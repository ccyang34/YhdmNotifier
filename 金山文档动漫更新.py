import requests
import re
import json
import unicodedata
import os
import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# ------------------------------
# 推送配置参数（未修改）
# ------------------------------
BEIJING_TZ = ZoneInfo("Asia/Shanghai")
HISTORY_FILE = os.path.join(os.getcwd(), "update_history_jinshan.json")
APP_TOKEN = "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc"
BASE_URL = "https://wxpusher.zjiecode.com/api"
TARGET_TOPIC_ID = [32277]

# ------------------------------
# 数据获取模块（未修改）
# ------------------------------
def fetch_raw_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "Referer": "https://www.kdocs.cn/",
        "Connection": "keep-alive"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        html = response.text
        script_pattern = re.compile(r'window\.initialState\s*=\s*({.*?});', re.DOTALL)
        json_match = script_pattern.search(html)
        json_data = None
        
        if json_match:
            try:
                json_data = json.loads(json_match.group(1))
            except Exception as e:
                print(f"解析JSON数据时出错: {e}")
        
        return {'html': html, 'json_data': json_data, 'status': 'success'}
        
    except requests.exceptions.RequestException as e:
        return {'status': 'error', 'error_type': 'request', 'message': str(e)}
    except Exception as e:
        return {'status': 'error', 'error_type': 'general', 'message': str(e)}

def extract_text_from_data(raw_data):
    extracted_text = []
    
    if raw_data.get('json_data'):
        try:
            doc_data = raw_data['json_data'].get('doc', {})
            content_data = doc_data.get('content', {})
            if 'blocks' in content_data:
                for block in content_data['blocks']:
                    if 'text' in block:
                        extracted_text.append(block['text'].strip())
                    elif 'paragraph' in block and 'content' in block['paragraph']:
                        for item in block['paragraph']['content']:
                            if 'text' in item:
                                extracted_text.append(item['text'].strip())
        except Exception as e:
            print(f"从JSON提取文本时出错: {e}")
    
    if not extracted_text and raw_data.get('html'):
        try:
            soup = BeautifulSoup(raw_data['html'], 'html.parser')
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text()
            text = unicodedata.normalize("NFKC", text)
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'[\u200b\u200c\u200d\u2060\uFEFF]', '', text)
            text = re.sub(r'[\s\-]', '', text)
            if text:
                extracted_text.append(text)
        except Exception as e:
            print(f"从HTML提取文本时出错: {e}")
    
    full_text = ' '.join(extracted_text)
    print(f"\n【提取到的完整文本】\n{full_text}\n【文本总长度】：{len(full_text)} 字符")
    return full_text

# ------------------------------
# 信息提取模块（核心修改：适配“动漫4k”格式，保留原始update_info）
# ------------------------------
def extract_anime_info(content):
    cleaned_content = re.sub(r'[\s\-]', '', content)
    anime_names = [
        "斗破苍穹", "牧神记", "凡人修仙传", "完美世界", 
        "仙逆", "遮天", "斗罗大陆", "吞噬星空", "武碎星河", "神墓"
    ]
    updates = []
    
    # 关键：匹配“动漫4kxxx”或“动漫xxx”格式，保留原始更新信息文本
    for anime in anime_names:
        # 正则捕获：动漫名称 + 原始更新信息（含“动漫4k”或“动漫”）
        pattern = rf'({anime})(动漫(?:4k)?[^，,。.]*?(?:更新至\d+集|已更新\d+集|开播\d+集|连载至\d+集|共\d+集|全\d+集|暂时完结全\d+集|完结|连载中|已完结))'
        match = re.search(pattern, cleaned_content, re.IGNORECASE)  # 兼容4k/4K大小写
        
        if match:
            cleaned_name = match.group(1)  # 动漫名称（如：遮天）
            raw_update_info = match.group(2)  # 原始更新信息（如：动漫4k更新至123集 / 动漫更新至123集）
            
            # 判断是否含4K（不修改原始update_info）
            has_4k = '4k' in raw_update_info.lower()
            # 生成唯一标识（用于历史比对，不影响推送格式）
            anime_unique_key = f"{cleaned_name}_有4K" if has_4k else f"{cleaned_name}_无4K"
            
            # 提取百度链接（逻辑不变）
            baidu_link = ""
            after_pos = match.end()
            baidu_match = re.search(r'https://pan\.baidu\.com/.*?\?pwd=[a-zA-Z0-9]{4}', cleaned_content[after_pos:])
            if baidu_match:
                baidu_link = baidu_match.group(0)
            
            updates.append({
                "title": cleaned_name,
                "update_info": raw_update_info,  # 保留原始更新信息文本，不做任何修改
                "baidu_link": baidu_link,
                "has_4k": has_4k,  # 仅用于历史比对，不影响推送
                "unique_key": anime_unique_key  # 仅用于历史比对，不影响推送
            })
    
    return updates

# ------------------------------
# 推送与历史记录模块（仅修改format_message，完全保留原始推送格式）
# ------------------------------
def get_beijing_time():
    return datetime.datetime.now(BEIJING_TZ)

def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
                history['pushes'] = history['pushes'][-20:]
                return history
        return {"pushes": []}
    except Exception as e:
        print(f"历史记录加载失败: {str(e)}")
        return {"pushes": []}

def save_history(new_push):
    try:
        current_history = load_history()
        current_history['pushes'].append(new_push)
        current_history['pushes'] = current_history['pushes'][-20:]
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存历史记录失败: {str(e)}")
        raise

def format_message(updates):
    """完全保留原始推送格式，不新增任何额外标签（如4K标注）"""
    current_time = get_beijing_time()
    message = []

    if not updates:
        message.append("<p>本次未检测到任何动漫更新信息</p>")
        return "\n".join(message)

    # 原始格式：红色大字体标题 + 原始update_info + 橙色链接（无任何额外修改）
    for update in updates:
        message.append(
            f'<font size="5" color="red">'
            f'{update["title"]}' 
            f'</font>'
            f' {update["update_info"]}'  # 直接使用原始更新信息，无额外内容
        )
        if update["baidu_link"]:
            message.append(
                f'<a href="{update["baidu_link"]}" style="color: orange; text-decoration: underline;">{update["baidu_link"]}\n\n'
            )
        else:
            message.append("百度链接: 未找到\n\n")
    
    return "\n".join(message)

def send_wechat(content):
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

# ------------------------------
# 主程序（沿用唯一标识比对，确保“无4K→有4K”触发推送）
# ------------------------------
if __name__ == "__main__":
    print("=== 执行开始 ===")
    doc_url = "https://www.kdocs.cn/l/cct2kiSZR43Z"
    
    print("1. 正在从网页获取原始数据...")
    raw_data = fetch_raw_data(doc_url)
    if raw_data['status'] != 'success':
        print(f"❌ 获取数据失败: {raw_data['message']}")
        print("=== 执行结束 ===")
        exit()
    print("✅ 成功获取原始数据")
    
    print("\n2. 正在从原始数据中提取文本内容...")
    document_text = extract_text_from_data(raw_data)
    if not document_text:
        print("❌ 未能从文档中提取到文本内容")
        print("=== 执行结束 ===")
        exit()
    print("✅ 文本提取完成")
    
    print("\n3. 正在提取动漫信息和百度链接...")
    anime_updates = extract_anime_info(document_text)
    if not anime_updates:
        print("❌ 未找到任何动漫更新信息")
        print("=== 执行结束 ===")
        exit()
    
    print("✅ 找到以下动漫更新:")
    for update in anime_updates:
        k4_label = "（含4K）" if update["has_4k"] else "（无4K）"
        print(f"- {update['title']} {k4_label} | 原始更新信息：{update['update_info']}")
    
    # 历史比对（用unique_key，不影响推送格式）
    current_unique_keys = {update['unique_key'] for update in anime_updates}
    history = load_history()
    
    if not history['pushes']:
        print("\n4. 无历史记录，准备推送...")
        message = format_message(anime_updates)
        print("5. 正在发送微信推送...")
        if send_wechat(message):
            save_history({
                "timestamp": get_beijing_time().isoformat(),
                "anime_unique_keys": list(current_unique_keys)
            })
    else:
        last_unique_keys = set(history['pushes'][-1]['anime_unique_keys'])
        new_unique_keys = current_unique_keys - last_unique_keys
        
        if new_unique_keys:
            new_desc = [f"{k.split('_')[0]} {k.split('_')[1]}" for k in new_unique_keys]
            print(f"\n4. 发现新增/4K状态更新: {', '.join(new_desc)}")
            message = format_message(anime_updates)
            print("5. 正在发送微信推送...")
            if send_wechat(message):
                save_history({
                    "timestamp": get_beijing_time().isoformat(),
                    "anime_unique_keys": list(current_unique_keys)
                })
        else:
            print("⏭️ 无新增内容（4K状态无变化），不推送")
    
    print("=== 执行结束 ===")
