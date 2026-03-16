import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import random
import os

# 設定要爬的看板 (檔名只寫名稱，路徑會由程式自動處理)
BOARDS = {
    "travel": "旅遊.csv",
    "food": "美食.csv",
    "job": "工作.csv",
    "graduate_school": "研究所.csv",
    "exam": "考試.csv"
}

TARGET_COUNT = 100  # 目標爬取數量
OUTPUT_DIR = "csv"    # 設定輸出的資料夾名稱
BATCH_SIZE = 5        # 每幾篇存檔一次

def get_driver():
    """設定適用於 GitHub Actions 的 Chrome"""
    options = uc.ChromeOptions()
    # 關鍵：啟用無頭模式 (Headless)
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # 模擬真實使用者
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    print("正在啟動 Headless Chrome...")
    driver = uc.Chrome(options=options, version_main=145)
    return driver

def crawl_board(driver, board, filename):
    # 組合完整的檔案路徑： csv/美食.csv
    csv_path = os.path.join(OUTPUT_DIR, filename)
    
    print(f"🚀 開始爬取：{board} (儲存至 {csv_path})")
    url = f"https://www.dcard.tw/f/{board}?latest=true"
    
    try:
        driver.get(url)
        time.sleep(5) # 等待頁面載入
    except Exception as e:
        print(f"無法載入頁面 {url}: {e}")
        return

    data = []
    collected_urls = set()
    
    # 1. 讀取舊資料避免重複 (斷點續傳)
    if os.path.exists(csv_path):
        try:
            old_df = pd.read_csv(csv_path)
            if "link" in old_df.columns:
                collected_urls = set(old_df["link"].unique())
            print(f"  已讀取現有資料 {len(collected_urls)} 筆")
        except:
            pass

    # --- 階段一：收集連結 ---
    print("  正在收集文章連結...")
    scroll_attempts = 0
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    # 收集連結迴圈
    while len(data) < TARGET_COUNT and scroll_attempts < 100:
        elems = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/p/"]')
        
        new_found = 0
        for elem in elems:
            try:
                link = elem.get_attribute('href')
                # 確保連結存在、未重複、且確實是文章連結
                if link and "/p/" in link and link not in collected_urls:
                    collected_urls.add(link)
                    data.append({"title": "待解析", "link": link}) # 標題稍後再抓比較準
                    new_found += 1
            except:
                continue
        
        print(f"\r  目前已收集 {len(data)} 篇新文章連結...", end="")
        
        # 滾動邏輯
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1.5, 3))
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            scroll_attempts += 1
        else:
            scroll_attempts = 0
            last_height = new_height
            
    print(f"\n  連結收集完成，準備爬取內容。")

    # --- 階段二：進入內文爬取 ---
    results = []
    for i, item in enumerate(data):
        # 雙重檢查目標數
        if i >= TARGET_COUNT: break
        
        try:
            driver.get(item['link'])
            time.sleep(random.uniform(2, 4)) # 隨機休息
            
            # 抓標題
            try:
                h1 = driver.find_element(By.TAG_NAME, "h1")
                item['title'] = h1.text
            except:
                item['title'] = "無標題"
            
            # 抓內文
            try:
                article = driver.find_element(By.TAG_NAME, "article")
                item['content'] = article.text
            except:
                item['content'] = "無法讀取內文"

            # 抓留言
            comments = []
            try:
                cmt_blocks = driver.find_elements(By.CSS_SELECTOR, '[data-testid="comment-content"]')
                for cb in cmt_blocks[:10]:
                    comments.append(cb.text.replace("\n", " "))
            except:
                pass
            item['comments'] = " || ".join(comments)
            
            results.append(item)
            print(f"  [{i+1}/{len(data)}] {item['title'][:15]}...")

            # === 關鍵修改：每 5 篇存一次 ===
            if len(results) >= BATCH_SIZE:
                save_csv(results, csv_path)
                results = [] # 清空暫存

        except Exception as e:
            print(f"  ❌ 錯誤: {e}")
            continue

    # 存最後一批
    if results:
        save_csv(results, csv_path)

def save_csv(new_rows, filepath):
    """儲存 CSV 的函數"""
    df = pd.DataFrame(new_rows)
    # 如果檔案不存在就寫入 Header，存在就 Append
    header = not os.path.exists(filepath)
    
    try:
        df.to_csv(filepath, mode='a', header=header, index=False, encoding='utf-8-sig')
        print(f"  💾 已儲存 {len(new_rows)} 筆資料到 {filepath}")
    except Exception as e:
        print(f"  ❌ 存檔失敗: {e}")

def main():
    # 1. 確保 csv 資料夾存在
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 已建立資料夾: {OUTPUT_DIR}")

    driver = get_driver()
    try:
        for board, filename in BOARDS.items():
            crawl_board(driver, board, filename)
            time.sleep(3) # 看板間稍微休息
    except Exception as e:
        print(f"發生全域錯誤: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
