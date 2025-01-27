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

# 历史记录文件路径 - 修改为使用 GitHub Actions 的工作目录
HISTORY_FILE = "/github/workspace/update_history.json"

# 从环境变量中获取 wxpusher 配置
APP_TOKEN = "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc"
BASE_URL = "https://wxpusher.zjiecode.com/api"
TARGET_TOPIC_ID = [32277]  # 目标主题的 topicId，是一个数组


def load_history():
    """加载历史记录"""
    now = datetime.datetime.now(BEIJING_TZ)
    # 每天凌晨0点5分自动清空历史记录
    if now.hour == 0 and now.minute == 5:
        return {"last_update": ""}
    
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"last_update": ""}


def save_history(content):
    """保存当前更新记录"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump({"last_update": content}, f, ensure_ascii=False)


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

    keywords = ["完美世界", "仙逆", "吞噬星空", "斗破苍穹", "武动乾坤", "斗罗大陆", "遮天", "武神主宰", "独步逍遥", "万界独尊", "剑来", "灵剑尊", "画江湖之天罡传", "斩神", "长生界"]
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

        # 筛选标题和更新日期（过去一周）
        if ((title in exact_titles) or any(keyword in title for keyword in keywords)) and update_date in valid_dates:
            episode = item.select_one('a.names > span.ep_name').text.strip()
            link = 'https://yhdm.one' + item.select_one('a.names')['href']

            # 获取周几
            update_date_obj = datetime.datetime.strptime(update_date, "%Y-%m-%d")
            weekday_zh = "周" + "一二三四五六日"[update_date_obj.weekday()]

            # 根据更新日期设置不同的格式
            if update_date == today:
                updates.append(
                    f"<font size=\"6\" color=\"red\"><a href=\"{link}\" style=\"color: red; text-decoration-color: red;\"><font color=\"red\">{title}</font></a></font>  <a href=\"alook://{link}\" style=\"font-size: 4;\">Alook打开</a>\n {episode} 🔥 更新日期：{update_date} {weekday_zh}\n\n")
            else:
                updates.append(
                    f"<font size=\"6\" color=\"orange\"><a href=\"{link}\" style=\"color: orange; text-decoration-color: orange;\"><font color=\"orange\">{title}</font></a></font>  <a href=\"alook://{link}\" style=\"font-size: 4;\">Alook打开</a>\n {episode} 🔥 更新日期：{update_date} {weekday_zh}\n\n")
    return updates


if __name__ == "__main__":
    # 获取动漫更新信息
    updates = get_anime_updates()
    # 获取今天的日期
    today_date = datetime.datetime.now(BEIJING_TZ).date().strftime("%Y-%m-%d")
    
    # 确认是否有今天的日期
    has_today_updates = any(f"更新日期：{today_date}" in update for update in updates)
    
    if has_today_updates:
        # 构建消息内容
        message = f"<center><span style='font-size: 24px;'><strong><span style='color: red;'>🔥 本周动漫更新 🔥</span></strong></span></center>\n\n" \
                  f"<center><span style=\"font-size: 14px\">(优选线路MD,JS,JY,WJ,WL,SN)</span></center>\n\n" \
                  + "".join(updates)

        # 加载历史记录
        history = load_history()
        
        # 如果内容与上次不同才发送
        if history["last_update"] != message:
            # 使用 topicId 群发消息
            response = send_message(message, topic_ids=TARGET_TOPIC_ID)
            # 保存当前更新记录
            save_history(message)
            print("检测到新更新，已发送消息")
        else:
            print("没有新更新，跳过发送")
