import requests
import pandas as pd
import time
import random
import os
from datetime import datetime

# --- 設定區 ---
BOARDS = {
    "travel": "旅遊.csv",
    "food": "美食.csv",
    "job": "工作.csv",
    "graduate_school": "研究所.csv",
    "exam": "考試.csv"
}

# 設定每個看板要爬幾篇
# API 速度很快，但建議單次不要超過 500，以免觸發 Rate Limit (429)
TARGET_PER_BOARD = 400 
OUTPUT_DIR = "csv"

# 偽裝成一般瀏覽器的標頭
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.dcard.tw/",
    "Accept": "application/json"
}

def get_posts(board, limit=30, before=None):
    """呼叫 Dcard API 取得文章列表"""
    # Dcard API 網址
    url = f"https://www.dcard.tw/service/api/v2/forums/{board}/posts?popular=false&limit={limit}"
    if before:
        url += f"&before={before}"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 429:
            print("⚠️ API 請求過於頻繁 (429)，休息 10 秒...")
            time.sleep(10)
            return []
        else:
            print(f"⚠️ API 錯誤 {resp.status_code}: {url}")
            return []
    except Exception as e:
        print(f"❌ 連線失敗: {e}")
        return []

def crawl_board_api(board, filename):
    csv_path = os.path.join(OUTPUT_DIR, filename)
    print(f"🚀 [API] 開始爬取看板：{board}")
    
    all_posts = []
    existing_ids = set()

    # 1. 讀取舊資料，避免重複 (根據文章 ID)
    if os.path.exists(csv_path):
        try:
            old_df = pd.read_csv(csv_path)
            if "id" in old_df.columns:
                existing_ids = set(old_df["id"].astype(str).unique())
            print(f"   📖 已讀取現有資料 {len(existing_ids)} 筆")
        except Exception as e:
            print(f"   ⚠️ 讀取舊檔失敗，將建立新檔: {e}")

    last_id = None
    collected_count = 0
    retry_count = 0

    while collected_count < TARGET_PER_BOARD:
        # 每次抓 30 筆
        batch = get_posts(board, limit=30, before=last_id)
        
        if not batch:
            retry_count += 1
            if retry_count > 3:
                print("   ⚠️ 連續失敗，停止爬取本看板")
                break
            time.sleep(2)
            continue
            
        new_items = []
        for post in batch:
            pid = str(post.get("id"))
            
            # 略過已存在或置頂公告
            if pid in existing_ids or post.get("pinned"):
                continue
                
            # 整理資料
            item = {
                "id": pid,
                "title": post.get("title"),
                "excerpt": post.get("excerpt", ""),
                "link": f"https://www.dcard.tw/f/{board}/p/{pid}",
                "likeCount": post.get("likeCount", 0),
                "commentCount": post.get("commentCount", 0),
                "createdAt": post.get("createdAt"),
                "updatedAt": post.get("updatedAt"),
                "gender": post.get("gender"),
                "school": post.get("school"),
                "topics": ",".join(post.get("topics", []))
            }
            new_items.append(item)
            existing_ids.add(pid)
            
            # 更新 last_id 用於翻頁
            last_id = post.get("id")

        if new_items:
            all_posts.extend(new_items)
            collected_count += len(new_items)
            print(f"   ✅ 取得 {len(new_items)} 筆新文章 (目前累積: {collected_count})")
            retry_count = 0 # 重置重試計數
        else:
            print("   ℹ️ 本頁無新文章 (可能都重複了)")
            if batch:
                last_id = batch[-1].get("id")

        # 隨機休息
        time.sleep(random.uniform(1, 2))

    # 存檔
    if all_posts:
        df = pd.DataFrame(all_posts)
        header = not os.path.exists(csv_path)
        df.to_csv(csv_path, mode='a', header=header, index=False, encoding='utf-8-sig')
        print(f"   💾 已儲存 {len(all_posts)} 筆資料至 {csv_path}")
    else:
        print("   💤 本次無新增資料")

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    for board, filename in BOARDS.items():
        crawl_board_api(board, filename)
        time.sleep(3)

if __name__ == "__main__":
    main()
