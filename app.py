import requests
import os
from flask import Flask, render_template, request, jsonify
import pandas as pd

app = Flask(__name__)

def get_team_from_excel():
    try:
        # 讀取妳的成員名單
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
    token = data.get('token')

    # 建議修改
    token = data.get('token') or os.environ.get('JIRA_TOKEN')

    if not token:
        return jsonify({"error": "請貼上您的 Jira API Token 或確認環境變數已設定"}), 400

    results = []
    
    # 優先讀取環境變數，若沒設定則使用原本的網址作為預設值
    base_url = os.environ.get('JIRA_URL', 'https://pmo-jira.qyrc452.com')
    api_url = f"{base_url}/rest/api/2/search"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    for m in selected_members:
        # 💡 使用 JQL 查詢 Bug 數量
        jql = f'project IN ("QA", "KYOP", "RDC-QA", "API-HCIYL") AND issuetype = "Bug" AND reporter = "{m["id"]}" AND created >= "{start_date}" AND created <= "{end_date}"'
        
        params = {"jql": jql, "maxResults": 0} # 設為 0 速度最快
        
        try:
            resp = requests.get(api_url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                count = resp.json().get("total", 0)
            else:
                print(f"Error for {m['name']}: {resp.status_code}") # 可以在 Terminal 看到報錯
                count = 0
        except Exception as e:
            print(f"Fetch failed: {e}")
            count = 0
            
        results.append({"name": m['name'], "count": count})

    return jsonify(results)

if __name__ == '__main__':
    # Render 會自動分配 PORT，若在本機執行則預設 5000
    port = int(os.environ.get('PORT', 5000))
    # 必須設定 host='0.0.0.0'，雲端伺服器才能連結到妳的程式
    app.run(host='0.0.0.0', port=port)