import requests
import re
import json
import unicodedata
import os
import datetime
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
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
    print("  启动浏览器拦截数据...")
    otl_json = None
    
    def handle_response(response):
        nonlocal otl_json
        if "open/otl" in response.url:
            print("  [网络拦截] 截获到:", response.url, "状态码:", response.status)
            if response.status == 200:
                try:
                    text = response.text()
                    otl_json = json.loads(text)
                    print("  [网络拦截] 成功解析 JSON")
                except Exception as e:
                    print("  [网络拦截] 解析 API 响应时出错:", e)
                
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            page.on("response", handle_response)
            page.goto(url)
            
            # 等待接口响应
            for _ in range(30):
                if otl_json:
                    break
                page.wait_for_timeout(500)
            
            browser.close()
            
            if otl_json:
                return {'status': 'success', 'json_data': otl_json}
            else:
                return {'status': 'error', 'message': '未能截获到文档内容 API 响应 (open/otl)。'}
                
    except Exception as e:
        return {'status': 'error', 'error_type': 'general', 'message': str(e)}

def extract_text_from_data(raw_data):
    def extract_text_recursive(node):
        if isinstance(node, dict):
            text = ""
            if "text" in node and isinstance(node["text"], str):
                text += node["text"]
            for k, v in node.items():
                text += extract_text_recursive(v)
            return text
        elif isinstance(node, list):
            text = ""
            for item in node:
                text += extract_text_recursive(item)
            return text
        else:
            return ""

    if raw_data.get('json_data'):
        try:
            full_text = extract_text_recursive(raw_data['json_data'])
            print(f"\n【提取到的完整文本】\n{full_text[:500]}...\n【文本总长度】：{len(full_text)} 字符")
            return full_text
        except Exception as e:
            print(f"从 JSON 提取文本时出错: {e}")
    
    return ""

# ------------------------------
# 信息提取模块
# ------------------------------
def extract_anime_info(content):
    cleaned_content = re.sub(r'[\s\-]', '', content)
    anime_names = [
      "神墓", "玄界之门", "天相", "斗破苍穹", "牧神记", "凡人修仙传", "完美世界", 
        "仙逆", "遮天", "斗罗大陆", "吞噬星空", "诛仙", "武动乾坤", "武碎星河", "神墓", "剑来", "永生", "深空彼岸"
    ]
    updates = []
    
    for anime in anime_names:
        pattern = rf'({anime}[^动]*)(动漫(?:第[一二三四五六七八九十\d]+季)?(?:4k)?[^，,。.]*?(?:更新至\d+集|已更新\d+集|开播\d+集|连载至\d+集|共\d+集|全\d+集|暂时完结全\d+集|完结|连载中|已完结))'
        match = re.search(pattern, cleaned_content, re.IGNORECASE)
        
        if match:
            cleaned_name = match.group(1)
            raw_update_info = match.group(2)
            has_4k = '4k' in raw_update_info.lower()
            # 仅当包含4K时才记录
            if not has_4k:
                continue
            anime_unique_key = f"{cleaned_name}_有4K"
            
            baidu_link = ""
            after_pos = match.end()
            baidu_match = re.search(r'https://pan\.baidu\.com/.*?\?pwd=[a-zA-Z0-9]{4}', cleaned_content[after_pos:after_pos+300])
            if baidu_match:
                baidu_link = baidu_match.group(0)
            
            updates.append({
                "title": cleaned_name,
                "update_info": raw_update_info,
                "baidu_link": baidu_link,
                "has_4k": True,
                "unique_key": anime_unique_key
            })
    
    return updates

# ------------------------------
# 推送与历史记录模块
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
        return {"pushes": [], "anime_details": []}
    except Exception as e:
        print(f"历史记录加载失败: {str(e)}")
        return {"pushes": [], "anime_details": []}

def save_history(new_push, current_anime_details):
    try:
        current_history = load_history()
        current_history['pushes'].append(new_push)
        current_history['pushes'] = current_history['pushes'][-20:]
        current_history['anime_details'] = current_anime_details
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存历史记录失败: {str(e)}")
        raise

def format_message(new_updates, old_updates):
    """新动漫标题红色，旧动漫标题橙色，保持其他格式不变"""
    message = []

    # 先添加新内容（红色标题）
    for update in new_updates:
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
    
    # 再添加旧内容（橙色标题）
    for update in old_updates:
        message.append(
            f'<font size="5" color="orange">'  # 仅此处修改为橙色
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
    
    if not message:
        message.append("<p>本次未检测到任何动漫更新信息</p>")
    
    return "\n".join(message)

def send_wechat(content, summary=None):
    data = {
        "appToken": APP_TOKEN,
        "content": content,
        "contentType": 3,
        "topicIds": TARGET_TOPIC_ID
    }
    if summary:
        data["summary"] = summary
        
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
        print("⚠️ 提示：金山文档可能已开启强制登录验证。")
        print("   请在浏览器登录金山文档，获取 Cookie（尤其是 wps_sid 字段），")
        print("   并将其设置为 KDOCS_COOKIE 环境变量后再试。")
        print("   例如：export KDOCS_COOKIE=\"wps_sid=你的值; ...\"")
        print("=== 执行结束 ===")
        exit()
    print("✅ 文本提取完成")
    
    print("\n3. 正在提取动漫信息和百度链接...")
    current_anime_details = extract_anime_info(document_text)
    if not current_anime_details:
        print("❌ 未找到任何动漫更新信息")
        print("=== 执行结束 ===")
        exit()
    
    print("✅ 找到以下动漫更新:")
    for update in current_anime_details:
        k4_label = "（含4K）" if update["has_4k"] else "（无4K）"
        print(f"- {update['title']} {k4_label} | 原始更新信息：{update['update_info']}")
    
    # 历史比对与排序逻辑
    current_unique_keys = {update['unique_key'] for update in current_anime_details}
    history = load_history()
    history_unique_keys = {update['unique_key'] for update in history['anime_details']}
    
    # 筛选新增动漫（置顶，红色标题）和旧动漫（置底，橙色标题）
    new_updates = [
        update for update in current_anime_details 
        if update['unique_key'] not in history_unique_keys
    ]
    old_updates = [
        update for update in current_anime_details 
        if update['unique_key'] in history_unique_keys
    ]
    
    # 推送判断与执行
    if new_updates:
        new_desc = [f"{k.split('_')[0]} {k.split('_')[1]}" for k in (current_unique_keys - history_unique_keys)]
        print(f"\n4. 发现新增/4K状态更新: {', '.join(new_desc)}")
        print("5. 正在生成推送内容（新内容红色标题，旧内容橙色标题）...")
        message = format_message(new_updates, old_updates)
        
        # 提取新增动漫标题用于生成推送摘要
        new_titles = [update['title'] for update in new_updates]
        push_summary = f"🔥 动漫更新: {', '.join(new_titles)}"
        
        print("6. 正在发送微信推送...")
        if send_wechat(message, summary=push_summary):
            save_history(
                new_push={
                    "timestamp": get_beijing_time().isoformat(),
                    "anime_unique_keys": list(current_unique_keys)
                },
                current_anime_details=current_anime_details
            )
    else:
        print("⏭️ 无新增内容（4K状态无变化），不推送")
    
    print("=== 执行结束 ===")
    
