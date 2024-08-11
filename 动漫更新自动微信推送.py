import requests
from bs4 import BeautifulSoup
import datetime
import os

# 从环境变量中获取 wxpusher 配置
APP_TOKEN = os.environ.get('APP_TOKEN')
BASE_URL = "https://wxpusher.zjiecode.com/api"
TARGET_TOPIC_ID = [32277]  # 目标主题的 topicId，是一个数组

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
    url = 'https://yhdm.one/latest/'
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    keywords = ["完美世界", "仙逆", "吞噬星空", "斗破苍穹", "斗罗大陆", "遮天", "武神主宰", "独步逍遥", "万界独尊", "灵剑尊"]
    exact_titles = ["永生", "凡人修仙传", "诛仙", "眷思量"]  # 需要完全匹配的标题
    today = datetime.date.today().strftime("%Y-%m-%d")
    valid_dates = [(datetime.date.today() - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    anime_items = soup.select('ul.latest-ul > li')
    updates = []

    for item in anime_items:
        title = item.select_one('a.names > span.name').text.strip()
        update_date = item.select_one('em').text.strip()

        # 筛选标题和更新日期（过去一周）
        if ((title in exact_titles) or any(keyword in title for keyword in keywords)) and update_date in valid_dates:
            episode = item.select_one('a.names > span.ep_name').text.strip()
            link = 'https://yhdm.one' + item.select_one('a.names')['href']

            # 获取周几
            update_date_obj = datetime.datetime.strptime(update_date, "%Y-%m-%d")
            weekday_zh = "周" + "一二三四五六日"[update_date_obj.weekday()]

            # 根据更新日期设置不同的格式
            if update_date == today:
                updates.append(f"<font size=\"6\" color=\"red\"><a href=\"{link}\" style=\"color: red; text-decoration-color: red;\"><font color=\"red\">{title}</font></a></font>\n {episode} 更新日期：{update_date} {weekday_zh}\n\n")
            else:
                updates.append(f"<font size=\"6\" color=\"orange\"><a href=\"{link}\" style=\"color: orange; text-decoration-color: orange;\"><font color=\"orange\">{title}</font></a></font>\n {episode} 更新日期：{update_date} {weekday_zh}\n\n")
    return updates

if __name__ == "__main__":
    updates = get_anime_updates()
    if updates:
        message = f"<center><span style=\"color: red; font-size: 24px\"> 本周动漫更新 </span></center>\n\n" \
                  f"<center>**(优选线路GS,HN,WJ,WL,SN,JS,MD)**</center>\n\n" + "".join(updates)  # 添加线路说明

        # 使用 topicId 群发消息
        response = send_message(message, topic_ids=TARGET_TOPIC_ID)
        print(response)
    else:
        print("今日无更新")
