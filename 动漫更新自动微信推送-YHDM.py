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

# 历史记录文件配置
HISTORY_FILE = os.path.join(os.getcwd(), "update_history.json")

# 微信推送配置
APP_TOKEN = "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc"
BASE_URL = "https://wxpusher.zjiecode.com/api"
TARGET_TOPIC_ID = [32277]

def load_history():
    """加载历史记录"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"last_update": ""}
    except Exception as e:
        print(f"加载历史记录失败: {str(e)}")
        return {"last_update": ""}

def save_history(content):
    """保存历史记录"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump({"last_update": content}, f, ensure_ascii=False, indent=2)
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
    if topic_ids:
        data["topicIds"] = topic_ids
    
    try:
        response = requests.post(f"{BASE_URL}/send/message", json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"消息发送失败: {str(e)}")
        return {"code": -1, "msg": str(e)}

def get_anime_updates():
    """获取动漫更新信息（增强容错）"""
    try:
        response = requests.get('https://yhdm.one/latest/', timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 筛选配置
    keywords = ["完美世界", "仙逆", "吞噬星空", "斗破苍穹", "武动乾坤", 
               "斗罗大陆", "遮天", "武神主宰", "独步逍遥", "万界独尊",
               "剑来", "灵剑尊", "画江湖之天罡传", "斩神", "长生界"]
    exact_titles = ["永生", "凡人修仙传", "诛仙", "眷思量"]
    
    # 时间计算
    now = datetime.datetime.now(BEIJING_TZ)
    today = now.strftime("%Y-%m-%d")
    valid_dates = [(now - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    
    updates = []
    for item in soup.select('ul.latest-ul > li'):
        try:
            title = item.select_one('a.names > span.name').text.strip()
            update_date = item.select_one('em').text.strip()
            
            if ((title in exact_titles) or any(kw in title for kw in keywords)) and update_date in valid_dates:
                episode = item.select_one('a.names > span.ep_name').text.strip()
                link = 'https://yhdm.one' + item.select_one('a.names')['href']
                
                # 格式化消息
                color = "red" if update_date == today else "orange"
                updates.append(
                    f'<font size="6" color="{color}">'
                    f'<a href="{link}" style="color: {color}; text-decoration-color: {color};">{title}</a>'
                    f'</font>  '
                    f'<a href="alook://{link}" style="font-size: 4;">Alook打开</a>\n'
                    f'{episode} 🔥 更新日期：{update_date}\n\n'
                )
        except Exception as e:
            print(f"解析条目失败: {str(e)}")
            continue
    
    return updates

if __name__ == "__main__":
    print("=== 执行开始 ===")
    
    # 获取并处理更新
    updates = get_anime_updates()
    today_str = datetime.datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    
    if any(today_str in update for update in updates):
        message = (
            "<center><span style='font-size: 24px; color: red;'>🔥 本周动漫更新 🔥</span></center>\n\n"
            "<center><span style='font-size: 14px'>(优选线路 MD/JS/JY/WJ/WL/SN)</span></center>\n\n"
            + "".join(updates)
        )
        
        # 历史记录比对
        history = load_history()
        if history.get("last_update") != message:
            result = send_message(message, topic_ids=TARGET_TOPIC_ID)
            if result.get("code") == 1000:
                save_history(message)
                print("✅ 消息发送成功并保存记录")
            else:
                print(f"❌ 发送失败: {result.get('msg')}")
        else:
            print("🔄 内容无变化，跳过发送")
    else:
        print("⏭️ 今日无目标更新")
    
    print("=== 执行结束 ===")
