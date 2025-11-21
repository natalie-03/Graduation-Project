import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import random
import os

# 設定要爬的看板
BOARDS = {
    "travel": "旅遊.csv",
    "food": "美食.csv",
    "job": "工作.csv",
    "graduate_school": "研究所.csv",
    "exam": "考試.csv"
}

TARGET_COUNT = 10000  # 目標爬取數量
OUTPUT_DIR = "csv"    # 設定輸出的資料夾名稱
BATCH_SIZE = 5        # 每幾篇存檔一次
MAX_LOAD_WAIT = 20    # 最大等待載入時間 (秒)

def get_driver():
    """設定適用於 GitHub Actions 的 Chrome"""
    options = uc.ChromeOptions()
    # 關鍵：啟用無頭模式 (Headless)
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # 增加穩定性參數 (新增)
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    
    # 模擬真實使用者
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 明確指定 Chrome 執行檔路徑 (適用於 GitHub Actions Ubuntu 環境)
    chrome_path = "/usr/bin/google-chrome"
    if os.path.exists(chrome_path):
        options.binary_location = chrome_path
        print(f"✅ 找到 Chrome Binary: {chrome_path}")
    
    print("正在啟動 Headless Chrome (純 Selenium 版)...")
    try:
        # 修正：明確指定 Chrome 主要版本為 120，提高穩定性
        driver = uc.Chrome(options=options, version_main=120) 
        return driver
    except Exception as e:
        print(f"❌ 嚴重錯誤：無法啟動 undetected-chromedriver。錯誤: {e}")
        return None


def crawl_board(driver, board, filename):
    if not driver: return 
    
    csv_path = os.path.join(OUTPUT_DIR, filename)
    
    print(f"🚀 開始爬取：{board} (儲存至 {csv_path})")
    url = f"https://www.dcard.tw/f/{board}?latest=true"
    
    try:
        driver.get(url)
        print(f"  正在嘗試載入頁面並等待 Cloudflare 檢查 ({MAX_LOAD_WAIT} 秒)...")
        
        # 強制等待文章列表元素出現，如果超時則被判定為 Cloudflare 阻擋
        WebDriverWait(driver, MAX_LOAD_WAIT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/p/"]'))
        )
        print("  ✅ 成功通過 Cloudflare 檢查並載入文章列表 (或超時)。")

    except Exception as e:
        # 檢查是否停留在 Cloudflare 頁面
        if "challenge" in driver.current_url.lower() or "dcard" not in driver.current_url.lower():
            print(f"  ❌ 錯誤：爬蟲被 Cloudflare 阻擋或超時！當前 URL: {driver.current_url}")
            print(f"  無法在 {MAX_LOAD_WAIT} 秒內通過檢查，停止爬取此看板。")
            return
        else:
            print(f"  ❌ 載入頁面時發生一般錯誤: {e}")
            return

    # --- 階段一：收集連結 ---
    data = []
    collected_urls = set()
    
    # 1. 讀取舊資料避免重複 (斷點續傳)
    if os.path.exists(csv_path):
        try:
            old_df = pd.read_csv(csv_path)
            if "link" in old_df.columns:
                collected_urls = set(old_df["link"].unique())
            
            # 將舊資料放入 data，以便後續 append
            data.extend(old_df[['title', 'link']].to_dict('records'))
            
            print(f"  已讀取現有資料 {len(collected_urls)} 筆")
        except:
            # 如果讀取失敗，就從頭開始
            pass

    print("  正在收集文章連結...")
    scroll_attempts = 0
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    # 收集連結迴圈 (最多滾動 100 次)
    while len(data) < TARGET_COUNT and scroll_attempts < 100:
        # 尋找所有文章連結元素
        elems = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/p/"]')
        
        newly_added = 0
        for elem in elems:
            try:
                link = elem.get_attribute('href')
                # 確保連結存在、未重複、且確實是文章連結
                if link and "/p/" in link and link not in collected_urls:
                    collected_urls.add(link)
                    # 只收集 link，title, content 稍後再爬取
                    data.append({"title": "待爬取", "link": link, "content": None, "comments": None}) 
                    newly_added += 1
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
            
    print(f"\n  連結收集完成，共 {len(data)} 篇。準備爬取內容。")

    # --- 階段二：進入內文爬取 (只處理新收集的連結) ---
    # 找出尚未爬取內容的文章 (content is None)
    new_data_to_crawl = [item for item in data if item.get('content') is None or item.get('content') == '待爬取']
    
    total_newly_crawled = 0
    
    for i, item in enumerate(new_data_to_crawl):
        if total_newly_crawled >= TARGET_COUNT: break
        
        try:
            driver.get(item['link'])
            time.sleep(random.uniform(2, 4)) # 隨機休息
            
            # 抓標題 (強制等待)
            try:
                h1 = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
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
            
            total_newly_crawled += 1
            print(f"  [{total_newly_crawled}/{len(new_data_to_crawl)}] {item['title'][:15]}...")

            # === 關鍵修改：即時存檔邏輯 (將新爬取的內容更新到 data 列表，然後重新寫入整個 CSV) ===
            if total_newly_crawled % BATCH_SIZE == 0:
                # 找到 item 在 data 中的索引並更新它
                save_csv(data, csv_path)
                
        except Exception as e:
            print(f"  ❌ 錯誤: {e}")
            continue

    # 存最後一批
    if new_data_to_crawl:
        save_csv(data, csv_path)

def save_csv(data_list, filepath):
    """將所有數據寫入 CSV 的函數 (覆蓋寫入，包含所有舊資料)"""
    df = pd.DataFrame(data_list)
    
    # 清理並保持欄位順序
    if not df.empty:
      df = df[['title', 'link', 'content', 'comments']].fillna('')
      
      try:
          # 直接覆蓋整個檔案，確保數據完整
          df.to_csv(filepath, index=False, encoding='utf-8-sig')
          print(f"  💾 已更新並儲存 {len(df)} 筆總資料到 {filepath}")
      except Exception as e:
          print(f"  ❌ 存檔失敗: {e}")


def main():
    # 1. 確保 csv 資料夾存在
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 已建立資料夾: {OUTPUT_DIR}")

    driver = get_driver()
    if not driver:
        print("無法取得瀏覽器驅動程式，程序退出。")
        return

    try:
        for board, filename in BOARDS.items():
            crawl_board(driver, board, filename)
            time.sleep(3) # 看板間稍微休息
    except Exception as e:
        print(f"發生全域錯誤: {e}")
    finally:
        if driver:
            print("關閉瀏覽器...")
            driver.quit()

if __name__ == "__main__":
    main()
