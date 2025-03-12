import requests
from bs4 import BeautifulSoup
import json
import re
import os
import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# 配置参数
BEIJING_TZ = ZoneInfo("Asia/Shanghai")
HISTORY_FILE = os.path.join(os.getcwd(), "update_history_youtube.json")
APP_TOKEN = "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc"
BASE_URL = "https://wxpusher.zjiecode.com/api"
TARGET_TOPIC_ID = [32277]
YOUTUBE_URL = "https://www.youtube.com/@VitaAnimationGroups/videos"

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

def get_youtube_updates():
    url = YOUTUBE_URL
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9"  # 设置语言偏好为中文
}

    try:
        response = requests.get(url, headers=headers, timeout=10)  # 设置超时时间为 10 秒
        response.raise_for_status()  # 如果请求失败，抛出异常
        html_content = response.text

        # 创建 BeautifulSoup 对象
        soup = BeautifulSoup(html_content, 'html.parser')

        # 查找包含 JSON 数据的 script 标签
        script_tags = soup.find_all('script')
        valid_title_link_time_pairs = []  # 用于存储视频信息的数据
        for script_tag in script_tags:
            script_text = script_tag.string
            if script_text:
                # 使用正则表达式提取 JSON 数据
                pattern = r'ytInitialData\s*=\s*({.*?});'
                match = re.search(pattern, script_text)
                if match:
                    json_str = match.group(1)
                    try:
                        data = json.loads(json_str)

                        # 遍历数据结构来查找视频标题、播放链接和更新时间
                        rich_item_renderers = data.get('contents', {}).get('twoColumnBrowseResultsRenderer', {}).get('tabs', [])
                        for tab in rich_item_renderers:
                            tab_content = tab.get('tabRenderer', {}).get('content', {})
                            rich_grid_renderer = tab_content.get('richGridRenderer', {})
                            contents = rich_grid_renderer.get('contents', [])
                            for item in contents:
                                rich_item = item.get('richItemRenderer', {})
                                video_renderer = rich_item.get('content', {}).get('videoRenderer', {})
                                
                                # 提取视频标题
                                title_element = video_renderer.get('title', {}).get('runs', [{}])[0].get('text', '')
                                if title_element:
                                    original_title = title_element
                                    # 提取作品名称
                                    start_pos = original_title.find('【') + 1
                                    end_pos = original_title.find('】')
                                    name = original_title[start_pos:end_pos] if start_pos != 0 and end_pos != -1 else original_title

                                    # 如果标题包含4K（不区分大小写），则添加到name后面
                                    if "4k" in original_title.lower():
                                        name += " 4k"

                                    # 检查是否为预告片
                                    if "Preview" in original_title:
                                        name += "<font size='2' color='red'>（下集预告）</font>"

                                    # 提取集数信息
                                    pattern = r'(?:Episode|EP|第|Season\s+\d+\s+Episode|集数)\s*(\d+|[0-9]+(?:\s*-\s*[0-9]+)?)(?:集|Collection|#\d+|Full)?'
                                    episode_match = re.search(pattern, original_title)
                                    episode_info = episode_match.group(1) if episode_match else ''

                                    # 提取播放链接
                                    navigation_endpoint = video_renderer.get('navigationEndpoint', {})
                                    watch_endpoint = navigation_endpoint.get('watchEndpoint', {})
                                    video_id = watch_endpoint.get('videoId', '')
                                    if video_id:
                                        link = f"https://www.youtube.com/watch?v={video_id}"

                                        # 提取更新时间
                                        published_time_text = video_renderer.get('publishedTimeText', {}).get('simpleText', '')

                                        # 存储视频信息
                                        valid_title_link_time_pairs.append((name, episode_info, link, published_time_text))
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

        # 只保留最新的10条视频信息
        valid_title_link_time_pairs = valid_title_link_time_pairs[:10]

        return valid_title_link_time_pairs

    except requests.RequestException as e:
        print(f"请求失败: {e}")
        return []

def format_message(updates):
    """生成推送消息"""
    current_time = get_beijing_time()
    formatted_messages = []
    formatted_messages.append('<center><span style="font-size: 24px; color: red;">🔥 Youtube动漫更新 🔥</span></center>\n\n')
    for name, episode_info, link, update_time in updates:
        formatted_message = (
            f'<font size="5" color="red">'
            f'<a href="{link}" style="color: red; text-decoration-color: red;"><b>{name}</b></a>'
            f'</font>  '
            f'<a href="alook://{link}" style="font-size: 4;">Alook打开</a>\n'
            f'第{episode_info}集🔥更新时间: {update_time}\n\n'
        )
        formatted_messages.append(formatted_message)

    return "".join(formatted_messages)

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
    new_updates = get_youtube_updates()

    # 生成内容指纹（顺序无关）
    content_fingerprint = {f"{u[0]}||{u[1]}" for u in new_updates}

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
