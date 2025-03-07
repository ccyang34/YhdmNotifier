import os
import json
import requests
from bs4 import BeautifulSoup
import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# 配置参数
BEIJING_TZ = ZoneInfo("Asia/Shanghai")
HISTORY_FILE = os.path.join(os.getcwd(), "update_history.json")
APP_TOKEN = "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc"
BASE_URL = "https://wxpusher.zjiecode.com/api"
TARGET_TOPIC_ID = [32277]
YHDM_URL = "https://yhdm.one/latest/"

def get_beijing_time():
    """获取当前北京时间"""
    return datetime.datetime.now(BEIJING_TZ)

def load_history():
    """原子化加载历史记录"""
    current_time = get_beijing_time()
    current_weekday = current_time.weekday()  # 0 表示周一，6 表示周日
    three_days_ago = current_time - datetime.timedelta(days=3)

    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)

                # 检查是否是周日，若是则重置历史记录
                if current_weekday == 6:
                    print(f"检测到周日，重置历史记录")
                    return {"week_number": current_time.isocalendar()[1], "pushes": []}

                # 清除3天前的记录
                history['pushes'] = [push for push in history['pushes'] if
                                     datetime.datetime.fromisoformat(push['timestamp']) > three_days_ago]

                return history
        return {"week_number": current_time.isocalendar()[1], "pushes": []}
    except Exception as e:
        print(f"历史记录加载失败: {str(e)}")
        return {"week_number": current_time.isocalendar()[1], "pushes": []}

def save_history(new_push):
    """原子化保存历史记录"""
    try:
        # 重新加载最新记录
        current_history = load_history()

        # 合并新记录
        current_history['pushes'].append(new_push)
        current_history['pushes'] = current_history['pushes'][-20:]  # 保持20条限制

        # 原子化写入
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_history, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"保存历史记录失败: {str(e)}")
        raise  # 抛出异常终止工作流

def get_anime_updates():
    """获取樱花动漫更新信息"""
    try:
        response = requests.get(YHDM_URL, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    keywords = ["完美世界", "仙逆", "吞噬星空", "斗破苍穹", "武动乾坤",
                "斗罗大陆", "遮天", "武神主宰", "独步逍遥", "万界独尊",
                "剑来", "灵剑尊", "牧神记", "斩神", "长生界"]
    exact_titles = ["永生", "凡人修仙传", "诛仙", "眷思量"]

    updates = []
    for item in soup.select('ul.latest-ul > li'):
        try:
            title = item.select_one('a.names > span.name').text.strip()
            update_date = item.select_one('em').text.strip()

            if (title in exact_titles) or any(kw in title for kw in keywords):
                episode = item.select_one('a.names > span.ep_name').text.strip()
                link = 'https://yhdm.one' + item.select_one('a.names')['href']
                updates.append({
                    "title": title,
                    "episode": episode,
                    "link": link,
                    "date": update_date
                })
        except Exception as e:
            print(f"解析条目失败: {str(e)}")
    return updates

def format_message(updates):
    """生成推送消息"""
    current_time = get_beijing_time()
    message = [
        f"<center><span style='font-size: 24px; color: red;'>🔥 樱花动漫更新 🔥</span></center>",
        f"<center><span style='font-size: 14px; color: #666;'>检测时间：{current_time.strftime('%Y-%m-%d %H:%M:%S')}</span></center>",
        "<center><span style='font-size: 14px'>(优选线路 JS/JY/WJ/WL/MD/SN)</span></center>\n"
    ]

    for update in updates:
        update_date = datetime.datetime.strptime(update["date"], "%Y-%m-%d").date()
        color = "red" if update_date == current_time.date() else "orange"
        message.append(
            f'<font size="6" color="{color}">'
            f'<a href="{update["link"]}" style="color: {color}; text-decoration-color: {color};">{update["title"]}</a>'
            f'</font>  '
            f'<a href="alook://{update["link"]}" style="font-size: 4;">Alook打开</a>\n'
            f'{update["episode"]} 🔥 更新日期：{update["date"]}\n\n'
        )
    return "\n".join(message)

def send_wechat(content):
    """发送微信推送"""
    data = {
        "appToken": APP_TOKEN,
        "content": content,
        "contentType": 3,
        "topicIds": TARGET_TOPIC_ID
    }
    try:
        response = requests.post(f"{BASE_URL}/send/message", json=data, timeout=10)
        result = response.json()
        if result.get("code") == 1000:
            print("✅ 微信推送成功")
            return True
        print(f"❌ 推送失败: {result.get('msg')}")
        return False
    except Exception as e:
        print(f"推送异常: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== 执行开始 ===")
    history = load_history()
    new_updates = get_anime_updates()

    # 生成内容指纹（顺序无关）
    content_fingerprint = {f"{u['title']}||{u['episode']}" for u in new_updates}

    if content_fingerprint:
        # 获取最近一次推送指纹（无条件获取最后一次）
        last_push = history['pushes'][-1]['fingerprint'] if history['pushes'] else set()

        # 转换为集合进行比对
        last_fingerprint = set(last_push)

        if content_fingerprint == last_fingerprint:
            print("⏭️ 内容与最近推送一致，跳过发送")
        else:
            message = format_message(new_updates)
            if send_wechat(message):
                # 记录推送信息
                save_history({
                    "timestamp": get_beijing_time().isoformat(),
                    "fingerprint": list(content_fingerprint)
                })
    else:
        print("⏭️ 本次未检测到更新内容")

    print("=== 执行结束 ===")
