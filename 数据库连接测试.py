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

# 测试第一个服务器连接
def test_server_connection(server_info):
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server_info['server']},{server_info['port']};DATABASE={database};UID={username};PWD={password}"
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        conn.close()
        print(f"成功连接到服务器: {server_info['server']}:{server_info['port']}")
        return True
    except Exception as e:
        error_message = f"连接失败 {server_info['server']}:{server_info['port']}: {str(e)}"
        print(error_message)
        return False, error_message

# 分别测试两个服务器
server1_result = test_server_connection(servers[0])
server2_result = test_server_connection(servers[1])

# 处理连接结果
if server1_result is True or server2_result is True:
    print("至少有一个服务器连接成功")
else:
    # 收集错误信息
    error_messages = []
    if server1_result is not True:
        error_messages.append(server1_result[1])
    if server2_result is not True:
        error_messages.append(server2_result[1])
    
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
