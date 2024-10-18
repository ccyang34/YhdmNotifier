try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# 设置北京时间
BEIJING_TZ = ZoneInfo("Asia/Shanghai")

import requests
from bs4 import BeautifulSoup
import datetime
import os
import json
from github import Github

# 从环境变量中获取 wxpusher 配置
APP_TOKEN = os.environ.get("APP_TOKEN")
BASE_URL = "https://wxpusher.zjiecode.com/api"
TARGET_TOPIC_ID = [int(x) for x in os.environ.get("TARGET_TOPIC_ID", "32277").split(",")]

SENT_MESSAGES_BRANCH = "sent-messages"  # 存储 sent_messages.json 的分支名

def load_sent_messages(repo):
    """从 sent-messages 分支加载已发送的消息记录"""
    try:
        contents = repo.get_contents("sent_messages.json", ref=SENT_MESSAGES_BRANCH)
        return json.loads(contents.decoded_content.decode("utf-8"))
    except github.GithubException as e:
        if e.status == 404:  # 如果文件不存在
            return {}
        else:
            raise  # 其他错误，重新抛出异常


def save_sent_messages(repo, sent_messages):
    """将已发送的消息记录保存到 sent-messages 分支"""
    try:
        contents = repo.get_contents("sent_messages.json", ref=SENT_MESSAGES_BRANCH)
        repo.update_file(
            contents.path,
            "Update sent messages",
            json.dumps(sent_messages, indent=4),
            contents.sha,  # 必须提供文件的 SHA 值才能更新
            branch=SENT_MESSAGES_BRANCH,
        )
    except github.GithubException as e:
        if e.status == 404:  # 文件不存在，则创建
            repo.create_file(
                "sent_messages.json", "Initial commit", json.dumps(sent_messages, indent=4), branch=SENT_MESSAGES_BRANCH
            )
        else:
            raise


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



def get_anime_updates(sent_messages):
    """获取并筛选动漫更新信息"""
    url = 'https://yhdm.one/latest/'
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    keywords = ["完美世界", "仙逆", "吞噬星空", "斗破苍穹", "斗罗大陆", "遮天", "武神主宰", "独步逍遥", "万界独尊", "剑来", "灵剑尊", "画江湖之天罡传", "斩神"]
    exact_titles = ["永生", "凡人修仙传", "诛仙", "眷思量"]  # 需要完全匹配的标题

    # 获取北京时间的当前日期和过去一周的日期列表
    now = datetime.datetime.now(BEIJING_TZ)
    today = now.date().strftime("%Y-%m-%d")
    valid_dates = [(now.date() - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    anime_items = soup.select('ul.latest-ul > li')
    updates = []

    for item in anime_items:
        title = item.select_one('a.names > span.name').text.strip()
        update_date = item.select_one('em').text.strip()
        episode = item.select_one('a.names > span.ep_name').text.strip()  # 在这里提取剧集信息
        link = 'https://yhdm.one' + item.select_one('a.names')['href']
        message_key = f"{title}-{episode}-{update_date}"

        if message_key not in sent_messages and ((title in exact_titles) or any(keyword in title for keyword in keywords)) and update_date in valid_dates:
            # 获取周几
            update_date_obj = datetime.datetime.strptime(update_date, "%Y-%m-%d")
            weekday_zh = "周" + "一二三四五六日"[update_date_obj.weekday()]

            # 根据更新日期设置不同的格式
            if update_date == today:
                updates.append(
                    f"<font size=\"6\" color=\"red\"><a href=\"{link}\" style=\"color: red; text-decoration-color: red;\"><font color=\"red\">{title}</font></a></font>  <a href=\"alook://{link}\" style=\"font-size: 4;\">Alook打开</a>\n {episode} 🔥 更新日期：{update_date} {weekday_zh}\n\n")
            else:
                updates.append(
                    f"<font size=\"6\" color=\"orange\"><a href=\"{link}\" style=\"color: orange; text-decoration-color: orange;\"><font color=\"orange\">{title}</font></a></font>  <a href=\"alook://{link}\" style=\"font-size: 4;\">Alook打开</a>\n {episode} 🔥 更新日期：{update_date} {weekday_zh}\n\n")  # 将剧集信息添加到消息中

    return updates


if __name__ == "__main__":

    g = Github(os.environ.get("GITHUB_TOKEN"))
    repo = g.get_repo(os.environ.get("GITHUB_REPOSITORY"))
    sent_messages = load_sent_messages(repo)

    updates = get_anime_updates(sent_messages)

    # 获取今天的日期
    today_date = datetime.datetime.now(BEIJING_TZ).date().strftime("%Y-%m-%d")

    has_today_updates = any(f"更新日期：{today_date}" in update for update in updates)

    if updates and has_today_updates:
        message = f"<center><span style='font-size: 24px;'><strong><span style='color: red;'>🔥 本周动漫更新 🔥</span></strong></span></center>\n\n" \
                  f"<center><span style=\"font-size: 14px\">(优选线路MD,JS,JY,WJ,WL,SN)</span></center>\n\n" \
                  + "".join(updates)

        response = send_message(message, topic_ids=TARGET_TOPIC_ID)
        print(response)


        for update in updates:
            title = update.split("</font>")[0].split(">")[-2]
            episode = update.split("🔥")[0].split("\n")[1].strip()
            update_date = update.split("更新日期：")[1].split("\n")[0].strip()
            message_key = f"{title}-{episode}-{update_date}"
            sent_messages[message_key] = True
        save_sent_messages(repo, sent_messages)

    else:
        print("今日无更新")
