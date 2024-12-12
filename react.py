from openai import OpenAI
import requests
import re
import json
# 初始化 OpenAI 客户端
client = OpenAI(api_key="XXXXXXXXXXXXXX")

file_path = 'api.txt'

# 讀取檔案內容
try:
    with open(file_path, 'r', encoding='utf-8') as file:
        api_text = file.read()
except Exception as e:
    print(f"發生錯誤：{e}")


# 初始化對話歷史
conversation_history = []

# 用戶輸入問題
user_question = input("請輸入問題: ")

# 添加用戶問題到對話歷史
conversation_history.append({"role": "user", "content": user_question})

# 定義 API 調用函數
API_ENDPOINTS = {
    "send_email": "http://127.0.0.1:7474/send_email",
    "get_emails": "http://127.0.0.1:7474/get_emails"
   # "get_wikitext":"http://127.0.0.1:7474/get_wikitext"
}

def call_api(api_name, parameter):
    """通用 API 調用邏輯"""
    if api_name not in API_ENDPOINTS:
        return f"未知的 API 名稱: {api_name}"
    
    # 選擇 API URL
    url = API_ENDPOINTS[api_name]
    
    # 根據 API 名稱生成不同的請求數據格式
    data = json.loads(parameter)
    # 發送請求
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        if 'error' in result:
            return f"API 錯誤信息: {result['error']}"
        return f"生成的 {api_name} 結果: {result}"
    else:
        return f"API 請求失敗，狀態碼: {response.status_code}, 錯誤信息: {response.text}"

# 進入回圈直到模型回答 "完成"
is_complete = False
while not is_complete:
    # 生成 Prompt
    prompt = f"""
你是一個智能系統助手，擅長通過邏輯推理和逐步行動來完成任務。根據以下的對話記錄，你需要：

1. 分析當前的上下文和用戶的需求。
2. 推理出下一步應該做什麼，並以清晰的文字說明推理過程。
3. 提出具體的行動指令，格式為：
   行動: <行動名稱>, <參數>
4. 如果行動執行後有回傳結果，請根據結果繼續推理和行動，直到完成任務。
注意事項：
- 目前可調用的行動有{api_text}除以上我列出的行動外不要使用任何其他行動。
- 如果問題中包含明確的主體和目標，優先提取主體並進行查詢。
舉例:'用戶：幫我查詢最近m120108030@tmu.edu.tw寄給我的郵件？
系統：
推理：查詢郵箱中m120108030@tmu.edu.tw寄出的郵件
行動：get_emails,specific_sender:m120108030@tmu.edu.tw
API 返回結果：["body": "12月請假文件簽核確認", "from": "m120108030@tmu.edu.tw",]
推理：從查詢結果中找到郵件資訊：
Subject: 12月請假文件簽核確認
From: =?UTF-8?B?5p6X56a55a6J?= <m120108030@tmu.edu.tw>
Body: 12月請假文件簽核確認
完成。'
- 行動指令需清晰且與上下文一致。
- 如果查詢到有内容即可完成任務並直接輸出，除了查詢結果之外，不要回復任何解釋或任何其他資訊。
- 如果任務已完成，請給出用戶提出問題的答案並回答「完成」。

以下是當前的對話記錄和系統回傳結果（如有）：

{conversation_history}

根據以上的上下文，請回答：
1. 下一步該做什麼？ 
2. 為什麼要這麼做？ 
3. 行動指令（如適用）。
"""

    
    # 向 OpenAI 發送請求
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=500,
        messages=[{"role": "system", "content": prompt}]
    )

    # 獲取推理內容
    reasoning = response.choices[0].message.content
    print("推理結果：", reasoning)

    # 添加推理內容到對話歷史
    conversation_history.append({"role": "assistant", "content": reasoning})

    # 檢測是否有行動指令
    if "行動:" in reasoning:
        # 解析行動指令，假設格式為 "行動:query, Edge Experience"
        try:
            action_part = reasoning.split("行動:")[1].strip()

            # 分割出 API 名稱和參數部分
            api_name, params = action_part.split(", ", 1)
            api_name = api_name.strip()

            # 使用正則表達式提取所有的 key:value 配對
            matches = re.findall(r"(\w+):\s*([^,]+)", params)

            # 格式化為合法的 JSON 字符串 (使用雙引號包裹鍵和值)
            parameter = '{' + ', '.join([f'"{key}":"{value.strip()}"' for key, value in matches]) + '}'

            # 調用 API 並獲取結果
            api_result = call_api(api_name, parameter)
            print("API 返回結果：", api_result)

            # 將 API 結果添加到對話歷史
            conversation_history.append({"role": "system", "content": api_result})
        except Exception as e:
            print("解析行動指令時發生錯誤:", e)
            conversation_history.append({"role": "system", "content": f"解析行動指令時發生錯誤: {e}"})
    else:
        print("沒有檢測到行動指令，繼續推理。")

    # 檢查是否完成
    if "完成" in reasoning:
        is_complete = True
        print("流程已完成，模型回答：", reasoning)
