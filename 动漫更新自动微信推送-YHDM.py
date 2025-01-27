try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
import datetime
import os
import json

# 设置北京时区
BEIJING_TZ = ZoneInfo("Asia/Shanghai")

# 历史记录文件路径（使用工作目录）
HISTORY_FILE = os.path.join(os.getcwd(), "update_history.json")

# 从环境变量中获取 wxpusher 配置
APP_TOKEN = "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc"
BASE_URL = "https://wxpusher.zjiecode.com/api"
TARGET_TOPIC_ID = [32277]  # 目标主题的 topicId


def load_history():
    """加载历史记录（带自动重置和异常处理）"""
    now = datetime.datetime.now(BEIJING_TZ)
    
    # 每日凌晨0点5分自动重置
    if now.hour == 0 and now.minute == 5:
        return {"last_update": ""}

    # 文件存在性检查和异常处理
    if not os.path.exists(HISTORY_FILE):
        return {"last_update": ""}
    
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"加载历史记录失败: {str(e)}，返回空记录")
        return {"last_update": ""}


def save_history(content):
    """保存当前更新记录（带异常处理）"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(
                {"last_update": content},
                f,
                ensure_ascii=False,
                indent=2
            )
            print("历史记录保存成功")
    except Exception as e:
        print(f"保存历史记录失败: {str(e)}")


def send_message(content, uids=None, topic_ids=None, summary=None, content_type=3, url=None, verify_pay_type=0):
    """发送微信消息"""
    data = {
        "appToken": APP_TOKEN,
        "content": content,
        "contentType": content_type,
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

    try:
        response = requests.post(f"{BASE_URL}/send/message", json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"消息发送失败: {str(e)}")
        return {"code": -1, "msg": str(e)}


def get_anime_updates():
    """获取并筛选动漫更新信息"""
    url = 'https://yhdm.one/latest/'
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {str(e)}")
        return []

    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    keywords = ["完美世界", "仙逆", "吞噬星空", "斗破苍穹", "武动乾坤", 
               "斗罗大陆", "遮天", "武神主宰", "独步逍遥", "万界独尊",
               "剑来", "灵剑尊", "画江湖之天罡传", "斩神", "长生界"]
    exact_titles = ["永生", "凡人修仙传", "诛仙", "眷思量"]

    now = datetime.datetime.now(BEIJING_TZ)
    today = now.date().strftime("%Y-%m-%d")
    valid_dates = [(now.date() - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    anime_items = soup.select('ul.latest-ul > li')
    updates = []

    for item in anime_items:
        title = item.select_one('a.names > span.name')
        if not title:
            continue
        title = title.text.strip()

        update_date = item.select_one('em')
        if not update_date:
            continue
        update_date = update_date.text.strip()

        # 双重过滤机制
        title_match = (title in exact_titles) or any(keyword in title for keyword in keywords)
        date_valid = update_date in valid_dates

        if title_match and date_valid:
            episode = item.select_one('a.names > span.ep_name')
            link = item.select_one('a.names')
            if not episode or not link:
                continue

            episode = episode.text.strip()
            link = 'https://yhdm.one' + link['href']

            try:
                update_date_obj = datetime.datetime.strptime(update_date, "%Y-%m-%d")
                weekday_zh = "周" + "一二三四五六日"[update_date_obj.weekday()]
            except ValueError:
                weekday_zh = ""

            # 格式化消息内容
            color = "red" if update_date == today else "orange"
            updates.append(
                f'<font size="6" color="{color}">'
                f'<a href="{link}" style="color: {color}; text-decoration-color: {color};">{title}</a>'
                f'</font>  '
                f'<a href="alook://{link}" style="font-size: 4;">Alook打开</a>\n'
                f'{episode} 🔥 更新日期：{update_date} {weekday_zh}\n\n'
            )

    return updates


if __name__ == "__main__":
    print("=== 开始执行动漫更新检查 ===")
    
    # 获取更新信息
    updates = get_anime_updates()
    today_date = datetime.datetime.now(BEIJING_TZ).date().strftime("%Y-%m-%d")
    
    # 检查当日更新
    has_today_updates = any(f"更新日期：{today_date}" in update for update in updates)
    
    if has_today_updates:
        print(f"检测到{today_date}的更新")
        
        # 构建消息内容
        message_header = (
            "<center><span style='font-size: 24px;'>"
            "<strong><span style='color: red;'>🔥 本周动漫更新 🔥</span></strong>"
            "</span></center>\n\n"
            "<center><span style='font-size: 14px'>(优选线路MD,JS,JY,WJ,WL,SN)</span></center>\n\n"
        )
        full_message = message_header + "".join(updates)

        # 历史记录对比
        history = load_history()
        if history["last_update"] != full_message:
            print("检测到新内容，准备发送消息...")
            response = send_message(full_message, topic_ids=TARGET_TOPIC_ID)
            
            if response.get("code") == 1000:
                save_history(full_message)
                print("消息发送成功，已更新历史记录")
            else:
                print(f"消息发送失败: {response.get('msg')}")
        else:
            print("内容未变化，跳过发送")
    else:
        print("今日无目标动漫更新")
    
    print("=== 执行完成 ===")
