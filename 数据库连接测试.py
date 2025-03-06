from sqlalchemy import create_engine
import requests
import base64

# 数据库连接信息
server = '47.121.207.201'
port = 1433
database = 'DB_K3SYNDB'
username = 'sa'
password = base64.b64decode('WG1zaHpoODg4IQ==').decode('utf-8')

# 添加连接超时和重试机制
try:
    # 使用pyodbc驱动连接SQL Server，添加连接超时参数
    engine = create_engine(
        f"mssql+pyodbc://{username}:{password}@{server}:{port}/{database}?driver=ODBC Driver 17 for SQL Server",
        connect_args={'timeout': 10}  # 设置10秒超时
    )
    connection = engine.connect()
    connection.close()
    print("数据库连接成功")
except Exception as e:
    print(f"数据库连接失败: {e}")
    
    # 推送消息到APP
    APP_TOKEN = "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc"
    BASE_URL = "https://wxpusher.zjiecode.com/api"
    TARGET_TOPIC_ID = [38231]
    
    error_message = f"数据库连接失败: {str(e)}"
    
    payload = {
        "appToken": APP_TOKEN,
        "topicIds": TARGET_TOPIC_ID,
        "content": error_message,
        "contentType": 1  # 1表示文本消息
    }
    
    try:
        # 添加请求超时参数
        push_response = requests.post(f"{BASE_URL}/send/message", json=payload, timeout=10)
        if push_response.status_code == 200:
            print(f"数据库连接失败消息已成功推送到APP: {error_message}")
        else:
            print(f"数据库连接失败消息推送失败: {push_response.text}")
    except requests.RequestException as req_err:
        print(f"推送消息失败: {req_err}")
