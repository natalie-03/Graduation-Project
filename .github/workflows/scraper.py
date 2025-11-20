import requests
from bs4 import BeautifulSoup
import time
import random

def fetch_articles():
    url = "https://www.dcard.tw/f/tech_job"  # 你要爬的看板
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print("❌ 連線失敗：", resp.status_code)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Dcard 已改版，多數內容由 JS 加載，HTML 看不到文章 → 這是你抓不到資料的主因！
    articles = soup.select("a[href^='/f/tech_job/p/']")

    links = ["https://www.dcard.tw" + a.get("href") for a in articles]

    print(f"✔️ 目前已收集 {len(links)} 篇文章連結")
    return links


def main():
    print("⏳ 開始爬取文章...")
    links = fetch_articles()

    if not links:
        print("⚠️ 沒抓到任何文章（可能是網站用 JavaScript 動態載入）")

    else:
        # 存檔
        with open("articles.txt", "w", encoding="utf-8") as f:
            for link in links:
                f.write(link + "\n")

        print("✔️ 已將文章連結保存到 articles.txt")

if __name__ == "__main__":
    main()
為啥github上抓捕不到文章
