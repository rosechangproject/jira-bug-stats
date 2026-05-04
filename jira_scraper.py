import re
import urllib.parse
import pandas as pd
import asyncio
from playwright.async_api import async_playwright
import json

# --- 1. 讀取 Excel 名單 ---
def get_team_from_excel(file_path):
    try:
        df = pd.read_excel(file_path)
        # ⚠️ 注意：欄位名稱必須與 Excel 完全一致 (檢查「蟲」字是否打對)
        team_dict = dict(zip(df['姓名'], df['Jira ID (爬蟲用的)']))
        print(f"✅ 成功載入 {len(team_dict)} 位成員名單")
        return team_dict
    except Exception as e:
        print(f"❌ 讀取 Excel 失敗: {e}")
        return {}

async def fetch_bug_count(page, member_name, member_id, start_date, end_date=None):
    # 1. 組合 JQL
    projects = ["QA", "KYOP", "RDC-QA", "API-HCIYL"]
    project_query = "(" + ", ".join([f'"{p}"' for p in projects]) + ")"
    jql = f'project IN {project_query} AND issuetype = "Bug" AND reporter = "{member_id}"'
    
    if "-" in str(start_date):
        jql += f' AND created >= "{start_date}"'
    else:
        jql += f' AND created >= {start_date}'
    if end_date:
        jql += f' AND created <= "{end_date}"'

    encoded_jql = urllib.parse.quote(jql)
    
    # ⚠️ 關鍵修正：地端版 Jira 建議使用 IssueNavigator 路徑
    # 請再次確認網域拼字是否完全正確
    base_url = "https://pmo-jira.qyrc452.com"
    search_url = f"{base_url}/secure/IssueNavigator.jspa?jql={encoded_jql}"
    
    print(f"📡 正在發送 {member_name} 的請求...")
    
    try:
        # 使用 wait_until="networkidle" 確保 AJAX 數據加載完成
        await page.goto(search_url, wait_until="networkidle", timeout=30000)
        
        # 偵錯：確認瀏覽器現在到底在哪裡
        if "login" in page.url.lower():
            print(f"❌ {member_name}: 掉到登入頁面了，請先跑 save_auth.py")
            return "Auth Error"

        # 2. 定義地端版可能的數量標籤 (results-count 或是包含 of 的 span)
        # 我們讓程式等 10 秒看數字出現沒
        count_locator = page.locator(".results-count, .showing, span:has-text('of')").first
        await count_locator.wait_for(state="visible", timeout=10000)
        
        raw_text = await count_locator.inner_text()
        
        # 3. 🛡️ 使用正規表示法只抓數字 (避開 "ile" 或 "file" 的問題)
        # re.findall(r'\d+', ...) 會把 "1 of 26" 變成 ["1", "26"]
        numbers = re.findall(r'\d+', raw_text.replace(',', ''))
        
        if len(numbers) >= 2:
            total_count = numbers[-1] # 拿最後一個數字
        elif len(numbers) == 1:
            total_count = numbers[0]
        else:
            total_count = "0"
            
        print(f"📊 {member_name}: {total_count} 筆")
        return total_count

    except Exception as e:
        # 最後手段：檢查頁面有沒有「沒有找到符合的」文字
        content = await page.content()
        if "No issues found" in content or "沒有找到" in content:
            print(f"📊 {member_name}: 0 筆 (確認無單)")
            return "0"
        else:
            print(f"ℹ️ {member_name}: 抓取失敗 (原因: {type(e).__name__})")
            return "0"

# --- 3. 執行主邏輯 ---
async def main():
    # A. 讀取名單
    team_members = get_team_from_excel("jira_members.xlsx")
    if not team_members: return

    async with async_playwright() as p:
        # B. 啟動瀏覽器 (共用同一個視窗)
        browser = await p.chromium.launch(headless=False) # 測試時建議設為 False 觀察執行情況
        context = await browser.new_context(storage_state="auth.json")
        page = await context.new_page()

        results = []
        
        # C. 跑名單迴圈
        # 妳可以改這兩個變數來調整日期
        TARGET_START = "2026-03-15"
        TARGET_END = "2026-05-01"

        for name, j_id in team_members.items():
            count = await fetch_bug_count(page, name, j_id, TARGET_START, TARGET_END)
            results.append({"姓名": name, "Bug數量": count})

        # D. 輸出成簡單的結果文件
        with open("daily_report.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        print("\n✨ 全部任務完成！結果已存入 daily_report.json")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())