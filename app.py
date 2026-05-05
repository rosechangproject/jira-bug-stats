import random
import requests
import os
from flask import Flask, render_template, request, jsonify
import pandas as pd

app = Flask(__name__)

def get_team_from_excel():
    try:
        # 讀取成員名單
        df = pd.read_excel("jira_members.xlsx")
        df = df.sort_values(by='姓名')
        return df[['姓名', 'Jira ID (爬蟲用的)']].to_dict('records')
    except:
        return []

@app.route('/')
def index():
    members = get_team_from_excel()
    return render_template('index.html', members=members)

@app.route('/run_report', methods=['POST'])
def run_report():
    data = request.json
    selected_members = data.get('members', [])
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    # 優先從網頁輸入讀取，若無則從環境變數讀取
    token = data.get('token') or os.environ.get('JIRA_TOKEN')

    # 如果既沒有 Token 也不是演示模式，才報錯
    if not token and not os.environ.get('DEMO_MODE') == 'true':
        return jsonify({"error": "請貼上您的 Jira API Token 或確認環境變數已設定"}), 400

    results = []
    
    # 檢查是否開啟演示模式
    is_demo = os.environ.get('DEMO_MODE') == 'true'
    
    # 定義 Jira API 網址與標頭
    base_url = os.environ.get('JIRA_URL', 'https://pmo-jira.qyrc452.com')
    api_url = f"{base_url}/rest/api/2/search"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    for m in selected_members:
        if is_demo:
            # 💡 演示模式：隨機產生 3 到 15 之間的數字
            count = random.randint(3, 15)
        else:
            # 🚀 真實邏輯：連線公司 Jira 抓取數據
            jql = f'project IN ("QA", "KYOP", "RDC-QA", "API-HCIYL") AND issuetype = "Bug" AND reporter = "{m["id"]}" AND created >= "{start_date}" AND created <= "{end_date}"'
            params = {"jql": jql, "maxResults": 0}
            try:
                resp = requests.get(api_url, headers=headers, params=params, timeout=10)
                count = resp.json().get("total", 0) if resp.status_code == 200 else 0
            except Exception as e:
                print(f"Error fetching data for {m['name']}: {e}")
                count = 0
            
        results.append({"name": m['name'], "count": count})

    return jsonify(results)

if __name__ == '__main__':
    # Render 會自動分配 PORT，若在本機執行則預設 5000
    port = int(os.environ.get('PORT', 5000))
    # 必須設定 host='0.0.0.0'，雲端伺服器才能連結到程式
    app.run(host='0.0.0.0', port=port)