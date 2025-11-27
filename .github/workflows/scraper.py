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

BOARDS = {
    "travel": "旅遊.csv",
    #"food": "美食.csv",
    #"job": "工作.csv",
    #"graduate_school": "研究所.csv",
    #"exam": "考試.csv"
}

def init_driver():
    """初始化驅動程式 - 優化記憶體使用"""
    opts = uc.ChromeOptions()
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--memory-pressure-off")
    opts.add_experimental_option("prefs", {"profile.default_content_setting_values.notifications": 2})
    
    try:
        driver = uc.Chrome(options=opts, version_main=142)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        print(f"驅動程式初始化失敗: {e}")
        return None

def collect_links(driver, board_url, max_scroll=200):
    """收集文章連結 - 優化效能版本"""
    print(f"開始收集 {board_url} 的文章連結...")
    
    try:
        driver.get(board_url)
        time.sleep(1)  # 初始載入等待
        
        links = set()
        last_count = 0
        no_new_count = 0
        
        for i in range(max_scroll):
            # 滾動頁面
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1, 1.5))  # 滾動間隔
            
            # 收集連結
            try:
                articles = WebDriverWait(driver, 5).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a[href*="/p/"]'))
                )
                
                for article in articles[-20:]:  # 只處理最近的文章避免重複
                    try:
                        href = article.get_attribute("href")
                        if href and "/p/" in href and href not in links:
                            links.add(href)
                    except:
                        continue
            except TimeoutException:
                print("  找不到文章元素，繼續滾動...")
                continue
            
            # 檢查進度
            current_count = len(links)
            if current_count == last_count:
                no_new_count += 1
                if no_new_count >= 20:  # 連續20次無新連結就停止
                    print(f"  已無新文章，停止滾動。共收集 {len(links)} 篇")
                    break
            else:
                no_new_count = 0
                last_count = current_count
            
            # 進度顯示
            if (i + 1) % 20 == 0:
                print(f"  已滾動 {i+1} 次，收集 {len(links)} 篇文章")
                
            # 記憶體釋放
            if (i + 1) % 50 == 0:
                driver.execute_script("window.stop();")
                time.sleep(1)
                
        return list(links)[:10000]  # 限制最大文章數避免記憶體不足
    
    except Exception as e:
        print(f"收集連結時發生錯誤: {e}")
        return []

def parse_article(driver, url):
    """解析單篇文章 - 增強穩定性和錯誤處理"""
    try:
        driver.get(url)
        time.sleep(random.uniform(1, 2))
        
        # 使用更穩定的等待方式
        title = "無標題"
        content = ""
        comments = ""
        
        try:
            title_elem = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            title = title_elem.text.strip()
        except:
            try:
                title_elem = driver.find_element(By.TAG_NAME, "h1")
                title = title_elem.text.strip()
            except:
                pass
        
        try:
            content_elem = driver.find_element(By.TAG_NAME, "article")
            content = content_elem.text.strip()
        except:
            pass
        
        try:
            comment_elems = driver.find_elements(By.CSS_SELECTOR, '[data-testid="comment"], .comment, .Post_comments_1_Nhv')
            comments = " || ".join([cmt.text.strip() for cmt in comment_elems[:10] if cmt.text.strip()])  # 限制評論數量
        except:
            pass
        
        return [title, content, comments, url]
        
    except Exception as e:
        print(f"解析文章失敗 {url}: {e}")
        return ["解析失敗", "", "", url]

def save_batch_data(board_name, batch_data, batch_num):
    """批次儲存資料並釋放記憶體"""
    if not batch_data:
        return
    
    csv_name = BOARDS[board_name]
    df = pd.DataFrame(batch_data, columns=["title", "content", "comments", "link"])
    
    # 檢查檔案是否存在來決定是否寫入標頭
    file_exists = os.path.exists(csv_name)
    
    try:
        df.to_csv(csv_name, mode='a', header=not file_exists, index=False, encoding='utf-8-sig')
        print(f"  批次 {batch_num} 已儲存 {len(batch_data)} 篇文章到 {csv_name}")
    except Exception as e:
        print(f"儲存失敗: {e}")
    
    # 釋放記憶體
    del df
    gc.collect()

def process_board(driver, board_name):
    """處理單個看板"""
    print(f"\n開始爬取 {board_name} 版...")
    
    csv_name = BOARDS[board_name]
    

    
    # 收集連結
    url = f"https://www.dcard.tw/f/{board_name}"
    links = collect_links(driver, url)
    
    if not links:
        print(f"❌ 無法收集到 {board_name} 的文章連結")
        return
    
    print(f"找到 {len(links)} 篇文章，開始解析...")
    
    # 批次處理文章
    batch_size = 10  # 減小批次大小以節省記憶體
    batch_data = []
    batch_num = 1
    
    for i, link in enumerate(links, 1):
        try:
            article_data = parse_article(driver, link)
            batch_data.append(article_data)
            
            print(f"  已解析 {i}/{len(links)}: {article_data[0][:30]}...")
            
            # 隨機延遲
            time.sleep(random.uniform(1, 3))
            
            # 批次儲存
            if len(batch_data) >= batch_size:
                save_batch_data(board_name, batch_data, batch_num)
                batch_data = []
                batch_num += 1
                
                # 休息一下避免被封
                time.sleep(2)
                
        except Exception as e:
            print(f"處理文章 {link} 時發生錯誤: {e}")
            continue
    
    # 儲存最後一批資料
    if batch_data:
        save_batch_data(board_name, batch_data, batch_num)
    
    print(f"✅ {board_name} 版完成，共處理 {len(links)} 篇文章")

def main():
    """主程式 - 優化記憶體管理"""
    driver = init_driver()
    if not driver:
        print("❌ 無法啟動瀏覽器，程式結束")
        return
    
    try:
        for board_name in BOARDS.keys():
            process_board(driver, board_name)
            
            # 每個看板完成後休息一下
            time.sleep(1)
            
        print("\n🎉 所有看板爬取完成！")
        
    except KeyboardInterrupt:
        print("\n⏹️ 使用者中斷程式")
    except Exception as e:
        print(f"❌ 程式執行錯誤: {e}")
    finally:
        if driver:
            driver.quit()
            print("🔚 瀏覽器已關閉")
        
        # 強制垃圾回收
        gc.collect()

if __name__ == "__main__":
    main()
