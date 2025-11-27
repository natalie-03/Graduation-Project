import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd
import random
import os
import gc
import time

BOARDS = {
    "travel": "旅遊.csv",
}

def init_driver():
    """初始化驅動程式 - 針對 GitHub Actions 強力抗偵測"""
    opts = uc.ChromeOptions()
    
    # === 關鍵設定 ===
    opts.add_argument("--headless=new") 
    opts.add_argument("--window-size=1920,1080")
    
    # 偽裝成一般使用者
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    
    try:
        driver = uc.Chrome(options=opts)
        driver.set_page_load_timeout(60) # 延長超時時間
        return driver
    except Exception as e:
        print(f"驅動程式初始化失敗: {e}")
        return None

def collect_links(driver, board_url, max_scroll=200):
    print(f"開始收集 {board_url} 的文章連結...")
    
    try:
        driver.get(board_url)
        
        # === 診斷步驟 (關鍵) ===
        print("等待頁面載入 (10秒)...")
        time.sleep(10) # 故意等久一點，讓 Cloudflare 驗證跑完
        
        page_title = driver.title
        print(f"🔍 目前網頁標題: {page_title}")
        
        # 檢查是否被擋
        if "Just a moment" in page_title or "Access denied" in page_title or "Attention Required" in page_title:
            print("⚠️ 警告: 被 Cloudflare 攔截！GitHub Actions IP 可能被封鎖。")
            print("嘗試印出頁面原始碼前 500 字元供除錯:")
            print(driver.page_source[:500])
            return []

        links = set()
        last_count = 0
        no_new_count = 0
        
        # 嘗試尋找主要內容容器，確保頁面真的載入了
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            print("等待 Body 元素超時")

        for i in range(max_scroll):
            # 滾動
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 3)) # 滾動慢一點
            
            # 收集連結 (使用更寬鬆的選擇器)
            found_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/p/"]')
            
            if not found_elements:
                # 再次確認是否還有內容
                print(f"  第 {i+1} 次滾動: 未發現連結，頁面原始碼長度: {len(driver.page_source)}")
            
            for article in found_elements[-30:]:
                try:
                    href = article.get_attribute("href")
                    if href and "/p/" in href and href not in links:
                        links.add(href)
                except:
                    continue
            
            # 檢查進度
            current_count = len(links)
            if current_count == last_count:
                no_new_count += 1
                if no_new_count >= 5: # 降低容忍次數，早點結束
                    print(f"  已無新文章，停止滾動。共收集 {len(links)} 篇")
                    break
            else:
                no_new_count = 0
                last_count = current_count
                print(f"  已滾動 {i+1} 次，目前收集 {len(links)} 篇文章")
            
            if (i + 1) % 50 == 0:
                driver.execute_script("window.stop();")
                time.sleep(1)
                
        return list(links)[:10000]
    
    except Exception as e:
        print(f"收集連結時發生錯誤: {e}")
        return []

def parse_article(driver, url):
    try:
        driver.get(url)
        time.sleep(random.uniform(2, 4))
        
        title = "無標題"
        content = ""
        comments = ""
        
        try:
            title = driver.find_element(By.TAG_NAME, "h1").text.strip()
        except:
            pass
        
        try:
            content = driver.find_element(By.TAG_NAME, "article").text.strip()
        except:
            pass
            
        try:
            comment_elems = driver.find_elements(By.CSS_SELECTOR, '.comment, [data-testid="comment"]')
            comments = " || ".join([c.text.strip() for c in comment_elems[:10] if c.text.strip()])
        except:
            pass
            
        return [title, content, comments, url]
    except:
        return ["解析失敗", "", "", url]

def save_batch_data(board_name, batch_data, batch_num):
    if not batch_data: return
    csv_name = BOARDS[board_name]
    df = pd.DataFrame(batch_data, columns=["title", "content", "comments", "link"])
    file_exists = os.path.exists(csv_name)
    try:
        df.to_csv(csv_name, mode='a', header=not file_exists, index=False, encoding='utf-8-sig')
        print(f"  批次 {batch_num} 已儲存 {len(batch_data)} 篇")
    except Exception as e:
        print(f"儲存失敗: {e}")
    del df
    gc.collect()

def process_board(driver, board_name):
    print(f"\n=== 開始爬取 {board_name} 版 ===")
    url = f"https://www.dcard.tw/f/{board_name}"
    links = collect_links(driver, url)
    
    if not links:
        print(f"❌ 無法收集到 {board_name} 的文章連結")
        return
    
    print(f"找到 {len(links)} 篇文章，開始解析...")
    batch_data = []
    batch_num = 1
    
    for i, link in enumerate(links, 1):
        data = parse_article(driver, link)
        batch_data.append(data)
        print(f"  已解析 {i}/{len(links)}: {data[0][:20]}")
        
        if len(batch_data) >= 10:
            save_batch_data(board_name, batch_data, batch_num)
            batch_data = []
            batch_num += 1
            time.sleep(2)
            
    if batch_data:
        save_batch_data(board_name, batch_data, batch_num)

def main():
    print("正在初始化 Chrome Driver...")
    driver = init_driver()
    if not driver: return
    
    try:
        for board_name in BOARDS.keys():
            process_board(driver, board_name)
            time.sleep(1)
        print("\n🎉 所有看板爬取完成！")
    except Exception as e:
        print(f"❌ 錯誤: {e}")
    finally:
        driver.quit()
        print("🔚 瀏覽器已關閉")

if __name__ == "__main__":
    main()
