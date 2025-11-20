import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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
TARGET_COUNT = 30  # 進一步降低目標數量
BATCH_SIZE = 3
# -----------------------------

def get_driver():
    options = uc.ChromeOptions()
    
    # 嘗試不使用 headless 模式看看
    # options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # 使用更常見的 user agent
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--window-size=1920,1080")
    
    print("正在啟動 Chrome...")
    try:
        driver = uc.Chrome(
            options=options,
            version_main=None
        )
        # 移除 automation 標誌
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        return driver
    except Exception as e:
        print(f"啟動 Chrome 失敗: {e}")
        raise

def save_csv(new_rows, filepath):
    if not new_rows:
        print("⚠️ 無新資料可儲存")
        return
        
    df = pd.DataFrame(new_rows)
    header = not os.path.exists(filepath)
    df.to_csv(filepath, mode='a', header=header, index=False, encoding='utf-8-sig')
    print(f"💾 已儲存 {len(new_rows)} 筆資料到 {filepath}")

def crawl_board(driver, board, filename):
    csv_path = os.path.join(OUTPUT_DIR, filename)
    url = f"https://www.dcard.tw/f/{board}"
    print(f"🚀 開始爬取：{board} ({url})")

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
        print(f"  載入頁面...")
        driver.get(url)
        # 等待更長時間讓頁面加載
        time.sleep(5)
        
        # 檢查頁面標題確認載入成功
        print(f"  頁面標題: {driver.title}")
        
    except Exception as e:
        print(f"❌ 無法載入頁面 {url}: {e}")
        return

    # 嘗試多種方法尋找文章連結
    print("  尋找文章連結...")
    
    # 方法1: 嘗試不同的選擇器
    selectors = [
        'a[href*="/p/"]',
        'article a',
        '.sc-37c4a7e2 a',  # Dcard 的可能類名
        'h2 a',
        '[data-testid="title-anchor"]',
        'a[class*="Title"]',
        'a[class*="title"]',
        'a[class*="Post"]'
    ]
    
    all_links = []
    
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for elem in elements:
                try:
                    href = elem.get_attribute('href')
                    if href and '/p/' in href and href not in all_links:
                        all_links.append(href)
                        print(f"    找到連結: {href[:80]}...")
                except:
                    continue
            if all_links:
                print(f"  使用選擇器 '{selector}' 找到 {len(elements)} 個元素，{len(all_links)} 個唯一連結")
                break
        except Exception as e:
            print(f"  選擇器 '{selector}' 失敗: {e}")
    
    # 方法2: 如果上面沒找到，嘗試通過 XPath
    if not all_links:
        print("  嘗試 XPath 尋找...")
        xpaths = [
            "//a[contains(@href, '/p/')]",
            "//article//a",
            "//h2//a",
            "//a[contains(@class, 'title')]"
        ]
        
        for xpath in xpaths:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for elem in elements:
                    try:
                        href = elem.get_attribute('href')
                        if href and '/p/' in href and href not in all_links:
                            all_links.append(href)
                    except:
                        continue
                if all_links:
                    print(f"  使用 XPath '{xpath}' 找到 {len(all_links)} 個連結")
                    break
            except Exception as e:
                print(f"  XPath '{xpath}' 失敗: {e}")
    
    # 方法3: 獲取頁面所有連結然後過濾
    if not all_links:
        print("  獲取所有連結進行過濾...")
        try:
            all_anchors = driver.find_elements(By.TAG_NAME, "a")
            for anchor in all_anchors:
                try:
                    href = anchor.get_attribute('href')
                    if href and '/p/' in href and href not in all_links:
                        all_links.append(href)
                except:
                    continue
            print(f"  從所有連結中過濾出 {len(all_links)} 個文章連結")
        except Exception as e:
            print(f"  獲取所有連結失敗: {e}")
    
    # 如果還是沒有找到連結，保存頁面源碼用於調試
    if not all_links:
        print("❌ 無法找到任何文章連結")
        debug_file = f"debug_{board}.html"
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print(f"  已保存頁面源碼到 {debug_file} 用於調試")
        except:
            print("  無法保存調試文件")
        return
    
    # 過濾掉重複的連結
    new_links = [link for link in all_links if link not in collected_urls][:TARGET_COUNT]
    
    for link in new_links:
        data.append({
            "title": "待解析", 
            "link": link,
            "content": "",
            "comments": ""
        })
    
    print(f"  📊 找到 {len(new_links)} 篇新文章")

    # 爬取文章內文
    results = []
    for i, item in enumerate(data):
        try:
            print(f"  正在處理第 {i+1}/{len(data)} 篇文章...")
            
            driver.get(item['link'])
            time.sleep(random.uniform(2, 3))
            
            # 獲取標題
            title = "無標題"
            title_selectors = [
                "h1",
                "h2",
                ".sc-1963a7b-0 h1",
                "header h1",
                "title"
            ]
            
            for selector in title_selectors:
                try:
                    title_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    title_text = title_elem.text.strip()
                    if title_text:
                        title = title_text
                        break
                except:
                    continue
            
            item['title'] = title
            
            # 獲取內容
            content = "無法讀取內文"
            content_selectors = [
                "article",
                ".sc-7f6b7c1c-0",
                ".phqpq",
                "[data-testid='comment-content']",
                "div[class*='content']",
                "main"
            ]
            
            for selector in content_selectors:
                try:
                    content_elems = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in content_elems:
                        text = elem.text.strip()
                        if text and len(text) > 10:
                            content = text
                            break
                    if content != "無法讀取內文":
                        break
                except:
                    continue
            
            item['content'] = content
            
            # 獲取評論
            comments = []
            comment_selectors = [
                "[data-testid='comment']",
                "[class*='comment']",
                ".sc-1963a7b-0"
            ]
            
            for selector in comment_selectors:
                try:
                    comment_elems = driver.find_elements(By.CSS_SELECTOR, selector)
                    for comment in comment_elems[:5]:  # 只取前5條評論
                        try:
                            comment_text = comment.text.strip()
                            if comment_text and len(comment_text) > 5:
                                comments.append(comment_text.replace("\n", " "))
                        except:
                            continue
                    if comments:
                        break
                except:
                    continue
            
            item['comments'] = " || ".join(comments) if comments else "無評論"
            
            results.append(item)
            print(f"  ✅ 完成: {title[:30]}...")
            
            # 批次儲存
            if len(results) >= BATCH_SIZE:
                save_csv(results, csv_path)
                results = []
                
        except Exception as e:
            print(f"  ❌ 處理文章時發生錯誤: {e}")
            continue

    # 儲存剩餘資料
    if results:
        save_csv(results, csv_path)
        
    print(f"✅ {board} 看板爬取完成，共處理 {len(data)} 篇文章")

def main():
    print("🎯 Dcard 爬蟲開始執行")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 已建立資料夾: {OUTPUT_DIR}")

    driver = None
    try:
        driver = get_driver()
        
        # 先測試一個看板
        board, filename = list(BOARDS.items())[0]
        print(f"\n{'='*50}")
        crawl_board(driver, board, filename)
        print(f"{'='*50}\n")
            
    except Exception as e:
        print(f"❌ 程式執行失敗: {e}")
    finally:
        if driver:
            print("🔄 關閉瀏覽器...")
            driver.quit()
            
    print("🎉 爬取完成！")

if __name__ == "__main__":
    main()
