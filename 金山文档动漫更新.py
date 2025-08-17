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
# 推送配置参数
# ------------------------------
BEIJING_TZ = ZoneInfo("Asia/Shanghai")
HISTORY_FILE = os.path.join(os.getcwd(), "update_history_jinshan.json")
APP_TOKEN = "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc"
BASE_URL = "https://wxpusher.zjiecode.com/api"
TARGET_TOPIC_ID = [32277]

# ------------------------------
# 数据获取模块
# ------------------------------
def fetch_raw_data(url):
    """获取网页原始数据（HTML和JSON）"""
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
        
        return {
            'html': html,
            'json_data': json_data,
            'status': 'success'
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'status': 'error',
            'error_type': 'request',
            'message': str(e)
        }
    except Exception as e:
        return {
            'status': 'error',
            'error_type': 'general',
            'message': str(e)
        }

def extract_text_from_data(raw_data):
    """从原始数据中提取文本内容（优先JSON，后备HTML）"""
    extracted_text = []
    
    # 优先从JSON数据提取
    if raw_data.get('json_data'):
        try:
            doc_data = raw_data['json_data'].get('doc', {})
            content_data = doc_data.get('content', {})
            
            if 'blocks' in content_data:
                blocks = content_data['blocks']
                for block in blocks:
                    if 'text' in block:
                        extracted_text.append(block['text'].strip())
                    elif 'paragraph' in block:
                        para = block['paragraph']
                        if 'content' in para:
                            for item in para['content']:
                                if 'text' in item:
                                    extracted_text.append(item['text'].strip())
        except Exception as e:
            print(f"从JSON提取文本时出错: {e}")
    
    # JSON提取失败时从HTML提取
    if not extracted_text and raw_data.get('html'):
        try:
            soup = BeautifulSoup(raw_data['html'], 'html.parser')
            
            # 移除脚本和样式标签
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            # 初步清理文本
            text = unicodedata.normalize("NFKC", text)
            text = re.sub(r'\s+', ' ', text)  # 将多个空白字符替换为单个空格
            text = re.sub(r'[\u200b\u200c\u200d\u2060\uFEFF]', '', text)  # 移除零宽字符
            text = re.sub(r'[\s\-]', '', text)  # 清除所有空格和连字符
            
            if text:
                extracted_text.append(text)
        except Exception as e:
            print(f"从HTML提取文本时出错: {e}")
    
    # 合并提取到的文本
    full_text = ' '.join(extracted_text)
    
    print(f"\n【提取到的完整文本】")
    print(full_text)
    print(f"【文本总长度】：{len(full_text)} 字符")
    
    return full_text

# ------------------------------
# 信息提取模块
# ------------------------------
def extract_anime_info(content):
    """从文本内容中提取动漫信息和百度网盘链接"""
    # 去除所有空格和-
    cleaned_content = re.sub(r'[\s\-]', '', content)
    
    # 指定动漫名称列表
    anime_names = [
        "斗破苍穹", "牧神记", "凡人修仙传", "完美世界", "仙逆", "遮天", "斗罗大陆", "吞噬星空", "武碎星河", "神墓"
    ]
    
    updates = []
    # 构建正则表达式，匹配动漫名称和紧跟的更新信息
    for anime in anime_names:
        # 匹配动漫名称和后面紧跟的更新信息（兼容季数、4k的顺序变化）
        pattern = rf'({anime}[^，,。.]*?)(动漫(?:第[\d一二三四五六七八九十]+季|4k)*?(?:更新至\d+集|暂时完结全\d+集))'
        match = re.search(pattern, cleaned_content)
        if match:
            cleaned_name = match.group(1)
            update_info = match.group(2)
            
            # 从当前位置向后查找第一个百度网盘链接
            after_pos = match.end()
            baidu_link = ""
            baidu_link_match = re.search(r'https://pan\.baidu\.com/.*?\?pwd=[a-zA-Z0-9]{4}', cleaned_content[after_pos:])
            if baidu_link_match:
                baidu_link = baidu_link_match.group(0)
            
            updates.append({
                "title": cleaned_name,
                "update_info": update_info,
                "baidu_link": baidu_link
            })
    
    return updates

# ------------------------------
# 推送与历史记录模块
# ------------------------------
def get_beijing_time():
    """获取当前北京时间"""
    return datetime.datetime.now(BEIJING_TZ)

def load_history():
    """原子化加载历史记录"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
                # 只保留最近20条记录
                history['pushes'] = history['pushes'][-20:]
                return history
        return {"pushes": []}
    except Exception as e:
        print(f"历史记录加载失败: {str(e)}")
        return {"pushes": []}

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

def format_message(updates):
    """生成推送消息"""
    current_time = get_beijing_time()
    message = []

    if not updates:
        message.append("<p>本次未检测到任何动漫更新信息</p>")
        return "\n".join(message)

    for update in updates:
        message.append(
            f'<font size="5" color="red">'
            f'{update["title"]}' 
            f'</font>'
            f' {update["update_info"]}'
        )
        if update["baidu_link"]:
            message.append(
                f'<a href="{update["baidu_link"]}" style="color: orange; text-decoration: underline;">{update["baidu_link"]}\n\n'
            )
        else:
            message.append("百度链接: 未找到\n\n")
    
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

# ------------------------------
# 主程序
# ------------------------------
if __name__ == "__main__":
    print("=== 执行开始 ===")
    # 目标金山文档URL
    doc_url = "https://www.kdocs.cn/l/cct2kiSZR43Z"
    
    print("1. 正在从网页获取原始数据...")
    raw_data = fetch_raw_data(doc_url)
    
    if raw_data['status'] == 'success':
        print("✅ 成功获取原始数据")
        
        print("\n2. 正在从原始数据中提取文本内容...")
        document_text = extract_text_from_data(raw_data)
        
        if document_text:
            print("✅ 文本提取完成")
            print("\n3. 正在提取动漫信息和百度链接...")
            anime_updates = extract_anime_info(document_text)
            
            if anime_updates:
                print("✅ 找到以下动漫更新:")
                for update in anime_updates:
                    print(f"- {update['title']} {update['update_info']}")
                
                # 提取当前记录中的动漫名称集合
                current_anime_names = {update['title'] for update in anime_updates}
                
                # 加载历史记录
                history = load_history()
                
                # 检查是否需要推送
                if not history['pushes']:  # 如果没有历史记录，直接推送
                    print("\n4. 无历史记录，准备推送...")
                    message = format_message(anime_updates)
                    print("5. 正在发送微信推送...")
                    if send_wechat(message):
                        # 记录推送信息，保存当前动漫名称集合
                        save_history({
                            "timestamp": get_beijing_time().isoformat(),
                            "anime_names": list(current_anime_names)
                        })
                else:
                    # 获取上一条记录中的动漫名称集合
                    last_anime_names = set(history['pushes'][-1]['anime_names'])
                    
                    # 找出当前记录比上一条多的动漫名称
                    new_anime_names = current_anime_names - last_anime_names
                    
                    if new_anime_names:  # 只有存在新的动漫名称时才推送
                        print(f"\n4. 发现新的动漫更新: {', '.join(new_anime_names)}")
                        print("5. 正在生成推送消息...")
                        message = format_message(anime_updates)
                        print("6. 正在发送微信推送...")
                        if send_wechat(message):
                            # 记录推送信息，保存当前动漫名称集合
                            save_history({
                                "timestamp": get_beijing_time().isoformat(),
                                "anime_names": list(current_anime_names)
                            })
                    else:
                        print("⏭️ 没有新增的动漫名称，与上一条记录对比后不推送")
            else:
                print("❌ 未找到任何动漫更新信息")
        else:
            print("❌ 未能从文档中提取到文本内容")
    else:
        print(f"❌ 获取数据失败: {raw_data['message']}")
    
    print("=== 执行结束 ===")
