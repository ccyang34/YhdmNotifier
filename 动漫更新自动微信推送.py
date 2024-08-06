import requests
from bs4 import BeautifulSoup
import datetime
import os

# 从环境变量中获取 wxpusher 配置
APP_TOKEN = os.environ.get('APP_TOKEN')
BASE_URL = "https://wxpusher.zjiecode.com/api"
# MY_UID = os.environ.get('MY_UID')  # 不再需要单独的用户 ID

def send_message(content, uids=None, topic_ids=None, summary=None, content_type=3, url=None, verify_pay_type=0):
    """发送微信消息"""
    data = {
        "appToken": APP_TOKEN,
        "content": content,
        "contentType": content_type,  # 使用 Markdown 格式
        "verifyPayType": verify_pay_type
    }
    if uids:
        data["uids"] = uids
    if topic_ids:
        data["topicIds"] = topic_ids
    if summary:
        data["summary"] = summary
    if url:
        data["url"] = url

    response = requests.post(f"{BASE_URL}/send/message", json=data)
    return response.json()

def get_anime_updates():
    """获取并筛选动漫更新信息"""
    # ... (代码逻辑不变)

if __name__ == "__main__":
    updates = get_anime_updates()
    if updates:
        message = f"<center><span style=\"color: red; font-size: 24px\">🔥 本周动漫更新 🔥</span></center>\n\n" + "".join(updates)
        
        # 发送给所有关注的用户，不需要指定 uids
        response = send_message(message)  
        print(response)
    else:
        print("今日无更新")
