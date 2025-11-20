import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os
import re

# -----------------------------
BOARDS = {
    "travel": "旅遊.csv",
    "food": "美食.csv", 
    "job": "工作.csv",
    "graduate_school": "研究所.csv",
    "exam": "考試.csv"
}

OUTPUT_DIR = "csv"
TARGET_COUNT = 20  # 降低目標數量
# -----------------------------

def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }

def save_csv(new_rows, filepath):
    if not new_rows:
        print("⚠️ 無新資料可儲存")
        return
        
    df = pd.DataFrame(new_rows)
    header = not os.path.exists(filepath)
    df.to_csv(filepath, mode='a', header=header, index=False, encoding='utf-8-sig')
    print(f"💾 已儲存 {len(new_rows)} 筆資料到 {filepath}")

def crawl_board(board, filename):
    csv_path = os.path.join(OUTPUT_DIR, filename)
    print(f"🚀 開始爬取：{board}")
    
    # 使用 Dcard API 獲取文章列表
    api_url = f"https://www.dcard.tw/service/api/v2/forums/{board}/posts"
    params = {
        'limit': TARGET_COUNT,
        'popular': 'false'  # 最新文章
    }
    
    data = []
    collected_urls = set()

    # 讀取舊資料避免重複
    if os.path.exists(csv_path):
        try:
            old_df = pd.read_csv(csv_path)
            if "link" in old_df.columns:
                collected_urls = set(old_df["link"].dropna().unique())
            print(f"  已讀取現有資料 {len(collected_urls)} 筆")
        except Exception as e:
            print(f"  讀取舊資料失敗: {e}")

    try:
        print(f"  請求 API: {api_url}")
        response = requests.get(api_url, params=params, headers=get_headers(), timeout=30)
        response.raise_for_status()
        
        posts = response.json()
        print(f"  API 返回 {len(posts)} 篇文章")
        
        for post in posts:
            try:
                post_id = post['id']
                title = post['title']
                excerpt = post.get('excerpt', '')
                link = f"https://www.dcard.tw/f/{board}/p/{post_id}"
                
                if link in collected_urls:
                    continue
                    
                data.append({
                    "title": title,
                    "link": link,
                    "content": "",
                    "comments": "",
                    "excerpt": excerpt
                })
                collected_urls.add(link)
                
            except Exception as e:
                print(f"  處理文章資料時錯誤: {e}")
                continue
                
    except Exception as e:
        print(f"❌ API 請求失敗: {e}")
        # 如果 API 失敗，嘗試使用網頁爬取
        return crawl_board_fallback(board, filename)

    # 爬取文章詳細內容
    results = []
    for i, item in enumerate(data):
        try:
            print(f"  正在處理第 {i+1}/{len(data)} 篇文章: {item['title'][:30]}...")
            
            # 使用文章 API 獲取詳細內容
            post_id = item['link'].split('/p/')[-1]
            post_api_url = f"https://www.dcard.tw/service/api/v2/posts/{post_id}"
            
            response = requests.get(post_api_url, headers=get_headers(), timeout=30)
            if response.status_code == 200:
                post_detail = response.json()
                item['content'] = post_detail.get('content', '')
                
                # 獲取評論
                comments_api_url = f"https://www.dcard.tw/service/api/v2/posts/{post_id}/comments"
                comments_response = requests.get(comments_api_url, headers=get_headers(), timeout=30)
                
                comments = []
                if comments_response.status_code == 200:
                    comments_data = comments_response.json()
                    for comment in comments_data[:5]:  # 只取前5條評論
                        comment_content = comment.get('content', '')
                        if comment_content:
                            comments.append(comment_content)
                
                item['comments'] = " || ".join(comments) if comments else "無評論"
            else:
                # 如果 API 失敗，嘗試使用網頁爬取
                item = crawl_post_content(item)
            
            results.append(item)
            print(f"  ✅ 完成")
            
            # 隨機延遲避免被阻擋
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"  ❌ 處理文章內容時錯誤: {e}")
            continue

    if results:
        save_csv(results, csv_path)
        
    print(f"✅ {board} 看板爬取完成，共處理 {len(results)} 篇文章")
    return len(results)

def crawl_board_fallback(board, filename):
    """備用方法：使用網頁爬取如果 API 不可用"""
    csv_path = os.path.join(OUTPUT_DIR, filename)
    url = f"https://www.dcard.tw/f/{board}"
    print(f"  使用備用方法爬取: {url}")
    
    data = []
    collected_urls = set()

    # 讀取舊資料避免重複
    if os.path.exists(csv_path):
        try:
            old_df = pd.read_csv(csv_path)
            if "link" in old_df.columns:
                collected_urls = set(old_df["link"].dropna().unique())
        except Exception as e:
            print(f"  讀取舊資料失敗: {e}")

    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 尋找文章連結
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if f'/f/{board}/p/' in href:
                full_url = f"https://www.dcard.tw{href}" if href.startswith('/') else href
                if full_url not in collected_urls and full_url not in links:
                    links.append(full_url)
        
        print(f"  找到 {len(links)} 個文章連結")
        
        for link in links[:TARGET_COUNT]:
            data.append({
                "title": "待解析",
                "link": link,
                "content": "",
                "comments": ""
            })
            
    except Exception as e:
        print(f"❌ 備用方法也失敗: {e}")
        return 0

    # 爬取文章內容
    results = []
    for i, item in enumerate(data):
        try:
            print(f"  正在處理第 {i+1}/{len(data)} 篇文章...")
            item = crawl_post_content(item)
            results.append(item)
            print(f"  ✅ 完成")
            
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"  ❌ 處理文章內容時錯誤: {e}")
            continue

    if results:
        save_csv(results, csv_path)
        
    print(f"✅ {board} 看板爬取完成，共處理 {len(results)} 篇文章")
    return len(results)

def crawl_post_content(item):
    """爬取單篇文章內容"""
    try:
        response = requests.get(item['link'], headers=get_headers(), timeout=30)
        if response.status_code != 200:
            return item
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 獲取標題
        title_elem = soup.find('h1')
        if title_elem:
            item['title'] = title_elem.get_text(strip=True)
        
        # 獲取內容
        content_elem = soup.find('article') or soup.find('div', class_=re.compile('content|post'))
        if content_elem:
            item['content'] = content_elem.get_text(strip=True)
        
        # 獲取評論（簡單版本）
        comments = []
        comment_elems = soup.find_all('div', class_=re.compile('comment|reply'))
        for comment in comment_elems[:5]:
            comment_text = comment.get_text(strip=True)
            if comment_text and len(comment_text) > 5:
                comments.append(comment_text)
        
        item['comments'] = " || ".join(comments) if comments else "無評論"
        
    except Exception as e:
        print(f"    爬取文章內容錯誤: {e}")
    
    return item

def main():
    print("🎯 Dcard 爬蟲開始執行 (使用 API 方法)")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 已建立資料夾: {OUTPUT_DIR}")

    total_processed = 0
    for board, filename in BOARDS.items():
        print(f"\n{'='*50}")
        processed = crawl_board(board, filename)
        total_processed += processed
        print(f"{'='*50}\n")
        time.sleep(2)  # 看板間隔
        
    print(f"🎉 所有看板爬取完成！總共處理 {total_processed} 篇文章")

if __name__ == "__main__":
    main()
