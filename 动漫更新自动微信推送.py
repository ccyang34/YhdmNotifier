import requests
from bs4 import BeautifulSoup
import datetime
import os

# 从环境变量中获取 wxpusher 配置
APP_TOKEN = os.environ.get('APP_TOKEN')
BASE_URL = "https://wxpusher.zjiecode.com/api"
MY_UID = os.environ.get('MY_UID')

def send_message(content, uids=None, topic_ids=None, summary=None, content_type=3, url=None, verify_pay_type=0):
    """发送微信消息"""
    params = {
        "appToken": APP_TOKEN,
        "content": content,
        "contentType": content_type,  # 使用 Markdown 格式
        "verifyPayType": verify_pay_type
    }
    if uids:
        params["uids"] = uids
    if topic_ids:
        params["topicIds"] = topic_ids
    if summary:
        params["summary"] = summary
    if url:
        params["url"] = url

    response = requests.post(f"{BASE_URL}/send/message", params=params)
    return response.json()

def get_anime_updates():
    """获取并筛选动漫更新信息"""
    url = 'https://yhdm.one/latest/'
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    keywords = ["完美世界", "仙逆", "吞噬星空", "斗破苍穹", "斗罗大陆", "遮天", "武神主宰", "凡人修仙传", "诛仙"]
    today = datetime.date.today().strftime("%Y-%m-%d")

    anime_items = soup.select('ul.latest-ul > li:has(a.names)')
    anime_updates = []

    for item in anime_items:
        title = item.select_one('a.names > span.name').text.strip()
        update_date = item.select_one('em').text.strip()

        # 筛选标题和更新日期
        if (title == "永生" or any(keyword in title for keyword in keywords)) and update_date == today:
            episode = item.select_one('a.names > span.ep_name').text.strip()
            link = 'https://yhdm.one' + item.select_one('a.names')['href']
            anime_updates.append(f"<font size=\"6\" color=\"red\"><a href=\"{link}\"><font color=\"red\">{title}</font></a></font>\n{episode} 🔥\n更新日期：{update_date}\n---\n")  #  更 新日期另起一行
    return anime_updates

if __name__ == "__main__":
    anime_updates = get_anime_updates()
    if anime_updates:
        message = f"<center><font size=\"6\">🔥 今日动漫更新 🔥</font></center>\n\n" + "".join(anime_updates)
        response = send_message(message, uids=[MY_UID])
        print(response)
    else:
        print("今日无更新")
