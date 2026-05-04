import asyncio
from playwright.async_api import async_playwright

async def save_auth():
    async with async_playwright() as p:
        # 開啟瀏覽器（畫面會顯示出來，方便妳操作）
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # 1. 導航到妳們公司的 Jira 登入頁面 (請更換為正確網址)
        print("請在彈出的瀏覽器中完成 Jira 登入...")
        await page.goto("https://pmo-jira.qyrc452.com/secure/Dashboard.jspa")

        # 2. 腳本會在這裡暫停，直到妳手動登入成功並看到儀表板
        # 我們設定 60 秒的時間讓妳操作
        try:
            # 這裡可以根據登入成功後會出現的元素來判斷，或是單純等待妳操作完畢
            await page.wait_for_timeout(60000) 
        except Exception:
            pass

        # 3. 儲存登入狀態到 auth.json
        await context.storage_state(path="auth.json")
        print("✅ 登入狀態已成功儲存至 auth.json！")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(save_auth())