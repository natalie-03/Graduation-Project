import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import pandas as pd
import time
import random
import os

# -----------------------------
BOARDS = {
    "travel": "旅遊.csv",
    "food": "美食.csv",
    "job": "工作.csv",
    "graduate_school": "研究所.csv",
    "exam": "考試.csv"
}

OUTPUT_DIR = "csv"
TARGET_COUNT = 100  # 每看板最大文章數，可調
BATCH_SIZE = 5      # 每幾篇存一次
# -----------------------------

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
    )
    print("正在啟動 Headless Chrome...")
    driver = uc.Chrome(options=options, version_main=None)
    return driver

def save_csv(new_rows, filepath):
    df = pd.DataFrame(new_rows)
    header = not os.path.exists(filepath)
    df.to_csv(filepath, mode='a', header=header, index=False, encoding='utf-8-sig')
    print(f"💾 已儲存 {len(new_rows)} 筆資料到 {filepath}")

def crawl_board(driver, board, filename):
    csv_path = os.path.join(OUTPUT_DIR, filename)
    url = f"https://www.dcard.tw/f/{board}?latest=true"
    print(f"🚀 開始爬取：{board} ({url})")

    data = []
    collected_urls = set()

    # 讀取舊資料避免重複
    if os.path.exists(csv_path):
        try:
            old_df = pd.read_csv(csv_path)
            if "link" in old_df.columns:
                collected_urls = set(old_df["link"].unique())
            print(f"  已讀取現有資料 {len(collected_urls)} 筆")
        except:
            pass

    try:
        driver.get(url)
        time.sleep(5)
    except Exception as e:
        print(f"無法載入頁面 {url}: {e}")
        return

    # 滾動收集文章連結
    scroll_attempts = 0
    last_height = driver.execute_script("return document.body.scrollHeight")
    while len(data) < TARGET_COUNT and scroll_attempts < 30:
        elems = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/p/"]')
        new_found = 0
        for elem in elems:
            try:
                link = elem.get_attribute('href')
                if link and link not in collected_urls:
                    collected_urls.add(link)
                    data.append({"title": "待解析", "link": link})
                    new_found += 1
            except:
                continue
        print(f"\r  已收集 {len(data)} 篇新文章連結...", end="")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1.5, 3))
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            scroll_attempts += 1
        else:
            last_height = new_height
            scroll_attempts = 0
    print(f"\n  連結收集完成，共 {len(data)} 篇文章")

    # 爬文章內文
    results = []
    for i, item in enumerate(data):
        if i >= TARGET_COUNT: break
        try:
            driver.get(item['link'])
            time.sleep(random.uniform(2, 4))
            try:
                h1 = driver.find_element(By.TAG_NAME, "h1")
                item['title'] = h1.text
            except:
                item['title'] = "無標題"
            try:
                article = driver.find_element(By.TAG_NAME, "article")
                item['content'] = article.text
            except:
                item['content'] = "無法讀取內文"
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
            if len(results) >= BATCH_SIZE:
                save_csv(results, csv_path)
                results = []
        except Exception as e:
            print(f"  ❌ 錯誤: {e}")
            continue

    if results:
        save_csv(results, csv_path)

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 已建立資料夾: {OUTPUT_DIR}")

    driver = get_driver()
    try:
        for board, filename in BOARDS.items():
            crawl_board(driver, board, filename)
            time.sleep(3)
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
