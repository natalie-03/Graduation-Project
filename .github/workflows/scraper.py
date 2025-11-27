from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd
import time
import random
import os

BOARDS = {
    "travel": "旅遊.csv",
}

def init_driver():
    """GitHub Actions 專用 Chrome Driver"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(20)
    return driver


def collect_links(driver, board_url, max_scroll=150):
    print(f"[INFO] Collecting links from {board_url}")

    driver.get(board_url)
    time.sleep(2)

    links = set()
    last_len = 0
    stable_cnt = 0

    for i in range(max_scroll):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1, 1.5))

        try:
            articles = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a[href*="/p/"]'))
            )
        except TimeoutException:
            continue

        for a in articles[-25:]:
            href = a.get_attribute("href")
            if href and "/p/" in href:
                links.add(href)

        if len(links) == last_len:
            stable_cnt += 1
            if stable_cnt >= 10:
                break
        else:
            stable_cnt = 0
            last_len = len(links)

        print(f"  scroll {i+1}, collected {len(links)} links")

    return list(links)


def parse_article(driver, url):
    try:
        driver.get(url)
        time.sleep(random.uniform(1, 1.8))

        try:
            title = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            ).text.strip()
        except:
            title = "無標題"

        try:
            content = driver.find_element(By.TAG_NAME, "article").text.strip()
        except:
            content = ""

        try:
            comments_elems = driver.find_elements(By.CSS_SELECTOR, '[data-testid="comment"]')
            comments = " || ".join([c.text for c in comments_elems[:10]])
        except:
            comments = ""

        return [title, content, comments, url]

    except Exception as e:
        print(f"解析錯誤: {url} → {e}")
        return ["解析失敗", "", "", url]


def save_data(board_name, data):
    df = pd.DataFrame(data, columns=["title", "content", "comments", "link"])
    df.to_csv(BOARDS[board_name], index=False, encoding="utf-8-sig")
    print(f"[SAVE] {board_name} 已儲存 {len(df)} 筆資料")


def process_board(driver, board_name):
    print(f"\n===== Start: {board_name} =====")

    url = f"https://www.dcard.tw/f/{board_name}"
    links = collect_links(driver, url)

    print(f"Found {len(links)} links, start parsing...")

    results = []
    for i, link in enumerate(links, 1):
        row = parse_article(driver, link)
        print(f"  {i}/{len(links)} {row[0][:20]}...")
        results.append(row)
        time.sleep(random.uniform(1, 2))

    save_data(board_name, results)


def main():
    driver = init_driver()

    for board in BOARDS.keys():
        process_board(driver, board)

    driver.quit()
    print("\n爬蟲完成！")


if __name__ == "__main__":
    main()
