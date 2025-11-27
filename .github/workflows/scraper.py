import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import pandas as pd
import random
import os
import gc
import time

# 設定要爬取的看板
BOARDS = {
    "travel": "旅遊.csv",
    # "food": "美食.csv",
    # "job": "工作.csv",
}

def init_driver():
    """初始化驅動程式 - 針對 GitHub Actions 優化"""
    print("正在初始化 Chrome Driver...")
    opts = uc.ChromeOptions()
    
    # --- GitHub Actions 關鍵設定 ---
    opts.add_argument("--headless=new")  # 無頭模式 (伺服器端必備)
    opts.add_argument("--window-size=1920,1080")  # 設定視窗大小，避免元素因RWD被隱藏
    opts.add_argument("--no-sandbox")  # 避免權限問題
    opts.add_argument("--disable-dev-shm-usage")  # 避免記憶體不足崩潰
    opts.add_argument("--disable-gpu")
    
    # --- 防偵測與優化設定 ---
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--memory-pressure-off")
    opts.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.images": 2  # 禁止載入圖片以加速 (可選)
    })
    
    try:
        # 移除 version_main，讓 uc 自動偵測 GitHub Runner 上的 Chrome 版本
        driver = uc.Chrome(options=opts)
        driver.set_page_load_timeout(60) # 放寬超時限制
        return driver
    except Exception as e:
        print(f"❌ 驅動程式初始化失敗: {e}")
        return None

def collect_links(driver, board_url, max_scroll=200):
    """收集文章連結"""
    print(f"開始收集 {board_url} 的文章連結...")
    
    try:
        driver.get(board_url)
        time.sleep(3)  # 等待初始載入
        
        links = set()
        last_count = 0
        no_new_count = 0
        
        for i in range(max_scroll):
            # 滾動頁面
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1.5, 2.5))  # 稍微拉長間隔避免網路延遲
            
            # 收集連結
            try:
                # 尋找所有文章連結
                elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/p/"]')
                
                # 只檢查最後 30 個元素以提升效能
                for element in elements[-30:]:
                    try:
                        href = element.get_attribute("href")
                        if href and "/p/" in href and href not in links:
                            links.add(href)
                    except:
                        continue
                        
            except Exception as e:
                print(f"  搜尋元素時發生輕微錯誤 (可忽略): {e}")
                continue
            
            # 檢查進度
            current_count = len(links)
            if current_count == last_count:
                no_new_count += 1
                if no_new_count >= 15:  # 連續 15 次無新連結就停止
                    print(f"  已無新文章，停止滾動。共收集 {len(links)} 篇")
                    break
            else:
                no_new_count = 0
                last_count = current_count
            
            # 進度顯示
            if (i + 1) % 10 == 0:
                print(f"  已滾動 {i+1} 次，目前收集 {len(links)} 篇文章")
                
            # 記憶體釋放 (簡單版)
            if (i + 1) % 50 == 0:
                gc.collect()
                
        return list(links)[:500]  # 限制數量 (CI 環境建議不要一次跑太多)
    
    except Exception as e:
        print(f"收集連結時發生錯誤: {e}")
        return []

def parse_article(driver, url):
    """解析單篇文章"""
    try:
        driver.get(url)
        # CI 環境網路可能較慢，隨機等待長一點
        time.sleep(random.uniform(2, 4))
        
        title = "無標題"
        content = ""
        comments = ""
        
        # 解析標題
        try:
            title_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            title = title_elem.text.strip()
        except:
            pass
        
        # 解析內文
        try:
            content_elem = driver.find_element(By.TAG_NAME, "article")
            content = content_elem.text.strip()
        except:
            pass
        
        # 解析留言 (Dcard 結構常變，嘗試多種選取器)
        try:
            # 捲動一點點觸發留言載入
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)
            
            comment_elems = driver.find_elements(By.CSS_SELECTOR, '[data-testid="comment"], .comment')
            comments = " || ".join([cmt.text.replace('\n', ' ').strip() for cmt in comment_elems[:15] if cmt.text.strip()])
        except:
            pass
        
        return [title, content, comments, url]
        
    except Exception as e:
        print(f"解析文章失敗 {url}: {e}")
        return ["解析失敗", "", "", url]

def save_batch_data(board_name, batch_data, batch_num):
    """批次儲存資料"""
    if not batch_data:
        return
    
    csv_name = BOARDS[board_name]
    df = pd.DataFrame(batch_data, columns=["title", "content", "comments", "link"])
    
    file_exists = os.path.exists(csv_name)
    
    try:
        df.to_csv(csv_name, mode='a', header=not file_exists, index=False, encoding='utf-8-sig')
        print(f"  批次 {batch_num} 已儲存 {len(batch_data)} 篇文章到 {csv_name}")
    except Exception as e:
        print(f"儲存失敗: {e}")
    
    del df
    gc.collect()

def process_board(driver, board_name):
    """處理單個看板"""
    print(f"\n=== 開始爬取 {board_name} 版 ===")
    
    url = f"https://www.dcard.tw/f/{board_name}"
    links = collect_links(driver, url)
    
    if not links:
        print(f"❌ 無法收集到 {board_name} 的文章連結")
        return
    
    print(f"找到 {len(links)} 篇文章，開始解析...")
    
    batch_size = 5  # CI 環境批次改小，確保資料頻繁寫入
    batch_data = []
    batch_num = 1
    
    for i, link in enumerate(links, 1):
        try:
            article_data = parse_article(driver, link)
            batch_data.append(article_data)
            
            print(f"  [{i}/{len(links)}] 解析: {article_data[0][:20]}...")
            
            if len(batch_data) >= batch_size:
                save_batch_data(board_name, batch_data, batch_num)
                batch_data = []
                batch_num += 1
                time.sleep(2) # 休息一下
                
        except Exception as e:
            print(f"處理文章迴圈錯誤: {e}")
            continue
    
    if batch_data:
        save_batch_data(board_name, batch_data, batch_num)
    
    print(f"✅ {board_name} 版完成")

def main():
    driver = init_driver()
    if not driver:
        print("❌ 無法啟動瀏覽器，程式結束")
        # 讓 GitHub Action 失敗，這樣你會收到通知
        exit(1)
    
    try:
        for board_name in BOARDS.keys():
            process_board(driver, board_name)
            time.sleep(2)
            
        print("\n🎉 所有看板爬取完成！")
        
    except KeyboardInterrupt:
        print("\n⏹️ 使用者中斷程式")
    except Exception as e:
        print(f"❌ 主程式執行錯誤: {e}")
    finally:
        if driver:
            try:
                driver.quit()
                print("🔚 瀏覽器已關閉")
            except:
                pass
        gc.collect()

if __name__ == "__main__":
    main()
