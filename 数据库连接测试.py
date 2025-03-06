import pyodbc
import base64
import requests

# 数据库连接信息
server = '47.121.207.201'
port = 1433
database = 'DB_K3SYNDB'
username = 'sa'
password = base64.b64decode('WG1zaHpoODg4IQ==').decode('utf-8')

# 推送配置
APP_TOKEN = "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc"
BASE_URL = "https://wxpusher.zjiecode.com/api"
TARGET_TOPIC_ID = [38231]

# 连接字符串
conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server},{port};DATABASE={database};UID={username};PWD={password}"

try:
    # 尝试连接
    conn = pyodbc.connect(conn_str, timeout=10)
    conn.close()
    print("数据库连接成功")
except Exception as e:
    error_message = f"数据库连接失败: {str(e)}"
    print(error_message)
    
    # 推送错误消息
    payload = {
        "appToken": APP_TOKEN,
        "topicIds": TARGET_TOPIC_ID,
        "content": error_message,
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
