import requests
import pandas as pd
import os
import time

# -----------------------------
# 設定看板與 CSV 檔名
BOARDS = {
    "travel": "旅遊.csv",
    "food": "美食.csv",
    "job": "工作.csv",
    "graduate_school": "研究所.csv",
    "exam": "考試.csv"
}

OUTPUT_DIR = "csv"
BATCH_SIZE = 20  # 每批存檔數量
# -----------------------------

def fetch_board(board, limit=100):
    url = f"https://www.dcard.tw/service/api/v2/forums/{board}/posts?limit={limit}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # 將文章轉成列表
        articles = []
        for post in data:
            articles.append({
                "id": post.get("id"),
                "title": post.get("title"),
                "excerpt": post.get("excerpt"),
                "link": f"https://www.dcard.tw/f/{board}/p/{post.get('id')}"
            })
        print(f"✔️ {board} 已抓取 {len(articles)} 篇文章")
        return articles
    except Exception as e:
        print(f"❌ {board} 抓取失敗: {e}")
        return []

def save_csv(board, articles):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    csv_path = os.path.join(OUTPUT_DIR, BOARDS[board])
    df = pd.DataFrame(articles)

    # 檢查檔案是否存在，存在就 append
    header = not os.path.exists(csv_path)
    df.to_csv(csv_path, mode='a', header=header, index=False, encoding='utf-8-sig')
    print(f"💾 已保存 {len(articles)} 筆到 {csv_path}")

def main():
    for board in BOARDS:
        all_articles = []
        # Dcard API 每次最多抓 100 篇，可分批抓更多
        total_limit = 200  # 每看板抓 200 篇文章，可調整
        for start in range(0, total_limit, 100):
            batch = fetch_board(board, limit=100)
            if not batch:
                break
            all_articles.extend(batch)
            time.sleep(1)  # 避免被封 IP

            # 批次存檔
            if len(all_articles) >= BATCH_SIZE:
                save_csv(board, all_articles)
                all_articles = []

        # 存最後一批
        if all_articles:
            save_csv(board, all_articles)

if __name__ == "__main__":
    main()
