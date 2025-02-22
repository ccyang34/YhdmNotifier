# 动漫更新自动微信推送-YHDM.py
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

def get_beijing_date():
    """获取当前北京日期"""
    return datetime.datetime.now(BEIJING_TZ).date()

def load_history():
    """加载并验证历史记录"""
    current_date = str(get_beijing_date())
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
                if history.get('date') != current_date:
                    print(f"检测到新日期 {current_date}，重置历史记录")
                    return {"date": current_date, "data": []}
                return history
        return {"date": current_date, "data": []}
    except Exception as e:
        print(f"历史记录加载失败: {str(e)}")
        return {"date": current_date, "data": []}

def save_history(history):
    """保存历史记录"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存历史记录失败: {str(e)}")

def check_duplicate(history, content_id):
    """精准内容查重"""
    return content_id in history["data"]

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
               "剑来", "灵剑尊", "画江湖之天罡传", "斩神", "长生界"]
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
    today = get_beijing_date()
    message = [
        f"<center><span style='font-size: 24px; color: red;'>🔥 本周动漫更新 🔥</span></center>",
        "<center><span style='font-size: 14px'>(优选线路 MD/JS/JY/WJ/WL/SN)</span></center>\n"
    ]
    
    for update in updates:
        update_date = datetime.datetime.strptime(update["date"], "%Y-%m-%d").date()
        color = "red" if update_date == today else "orange"
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
    
    # 过滤当日已推送内容
    unique_updates = []
    for update in new_updates:
        content_id = f"{update['title']}_{update['episode']}"
        if not check_duplicate(history, content_id):
            unique_updates.append(update)
            history["data"].append(content_id)
    
    if unique_updates:
        message = format_message(unique_updates)
        if send_wechat(message):
            save_history(history)
    else:
        print("⏭️ 今日无新内容需要推送")
    
    print("=== 执行结束 ===")

