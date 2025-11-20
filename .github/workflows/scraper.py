from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random

def fetch_articles_selenium():
    print("🚀 启动浏览器...")
    
    # 配置 Chrome 选项
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 无界面模式
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    try:
        # 初始化浏览器（确保 chromedriver 在 PATH 中）
        driver = webdriver.Chrome(options=chrome_options)
        
        print("📄 访问 Dcard 科技工作版...")
        driver.get("https://www.dcard.tw/f/tech_job")
        
        # 等待页面加载
        print("⏳ 等待页面加载...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "article"))
        )
        
        # 滚动页面以触发更多内容加载
        print("🔄 滚动页面加载更多内容...")
        for i in range(3):  # 滚动3次
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # 等待内容加载
        
        # 查找文章链接
        print("🔍 查找文章链接...")
        articles = driver.find_elements(By.CSS_SELECTOR, "a[href*='/f/tech_job/p/']")
        
        links = []
        for article in articles:
            href = article.get_attribute("href")
            if href and href not in links:
                links.append(href)
        
        print(f"✔️ 成功收集 {len(links)} 篇文章链接")
        return links
        
    except Exception as e:
        print(f"❌ 爬取过程中出现错误: {e}")
        return []
        
    finally:
        # 确保浏览器被关闭
        if 'driver' in locals():
            driver.quit()
            print("🔚 浏览器已关闭")

def main():
    print("⏳ 开始爬取 Dcard 科技工作版文章...")
    
    # 添加随机延迟，避免被检测
    time.sleep(random.uniform(1, 3))
    
    links = fetch_articles_selenium()

    if not links:
        print("⚠️ 没有抓到任何文章")
    else:
        # 保存到文件
        with open("articles.txt", "w", encoding="utf-8") as f:
            for link in links:
                f.write(link + "\n")

        print("✅ 文章链接已保存到 articles.txt")
        
        # 显示前5个链接作为示例
        print("\n📋 前5个文章链接:")
        for i, link in enumerate(links[:5], 1):
            print(f"{i}. {link}")

if __name__ == "__main__":
    main()
