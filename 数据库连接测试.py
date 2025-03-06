import pyodbc
import base64
import requests

# 数据库连接信息
servers = [
    {'server': '47.121.207.201', 'port': 1433},
    {'server': '53397pplz010.vicp.fun', 'port': 14472}
]
database = 'DB_K3SYNDB'
username = 'sa'
password = base64.b64decode('WG1zaHpoODg4IQ==').decode('utf-8')

# 推送配置
APP_TOKEN = "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc"
BASE_URL = "https://wxpusher.zjiecode.com/api"
TARGET_TOPIC_ID = [38231]

# 测试连接
connection_success = False
error_messages = []

for server_info in servers:
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server_info['server']},{server_info['port']};DATABASE={database};UID={username};PWD={password}"
    
    try:
        # 尝试连接
        conn = pyodbc.connect(conn_str, timeout=10)
        conn.close()
        print(f"成功连接到服务器: {server_info['server']}:{server_info['port']}")
        connection_success = True
        break
    except Exception as e:
        error_message = f"连接失败 {server_info['server']}:{server_info['port']}: {str(e)}"
        print(error_message)
        error_messages.append(error_message)

if not connection_success:
    # 推送所有错误消息
    combined_error = "\n".join(error_messages)
    payload = {
        "appToken": APP_TOKEN,
        "topicIds": TARGET_TOPIC_ID,
        "content": combined_error,
        "contentType": 1
    }
    
    try:
        push_response = requests.post(f"{BASE_URL}/send/message", json=payload, timeout=10)
        if push_response.status_code == 200:
            print("错误消息已成功推送到APP")
        else:
            print(f"消息推送失败: {push_response.text}")
    except requests.RequestException as req_err:
        print(f"推送消息失败: {req_err}")
