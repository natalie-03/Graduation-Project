import requests
from bs4 import BeautifulSoup
import time
import random
import json

def fetch_articles():
    # Dcard 官方 API：抓 tech_job 看板最新 30 篇
    url = "https://www.dcard.tw/service/api/v2/forums/tech_job/posts?limit=30"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        data = resp.json()  # 取得完整文章資料（含 id, title, excerpt 等）

        # 將文章 ID 轉成可點擊連結
        links = [f"https://www.dcard.tw/f/tech_job/p/{post['id']}" for post in data]

        print(f"✔️ 目前已收集 {len(links)} 篇文章連結")
        return links

    except Exception as e:
        print("❌ API 取得文章失敗：", e)
        return []


def main():
    print("⏳ 開始爬取文章...")
    links = fetch_articles()

    if not links:
        print("⚠️ 沒抓到任何文章")
    else:
        # 存成 txt（完全保留你原本的架構）
        with open("articles.txt", "w", encoding="utf-8") as f:
            for link in links:
                f.write(link + "\n")

        print("✔️ 已將文章連結保存到 articles.txt")


if __name__ == "__main__":
    main()
