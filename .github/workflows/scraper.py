from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)
    return driver


def get_links_from_board(board="food"):
    url = f"https://www.dcard.tw/f/{board}"
    driver = setup_driver()

    print(f"🔗 打開：{url}")
    driver.get(url)
    time.sleep(5)

    # ⬇️ Debug：印出前 1200 字
    print("\n=== 🔍 DEBUG: Page Source Preview ===")
    print(driver.page_source[:1200])
    print("===================================\n")

    # 偵測有無 Cloudflare 檔
    if "請稍候" in driver.page_source or "Just a moment" in driver.page_source:
        print("❌ 被 Cloudflare 檔住了！")
        driver.quit()
        return []

    # 開始捲動載入貼文
    print("📜 開始捲動以載入文章...")
    for _ in range(8):
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
        time.sleep(2)

    # 抓貼文連結
    print("🔎 解析貼文連結...")
    posts = driver.find_elements(By.CSS_SELECTOR, "a[href*='/f/']")
    links = [p.get_attribute("href") for p in posts if "/p/" in p.get_attribute("href")]

    print(f"📌 共抓到 {len(links)} 篇文章")
    driver.quit()
    return list(set(links))


if __name__ == "__main__":
    links = get_links_from_board("food")
    print(links)
