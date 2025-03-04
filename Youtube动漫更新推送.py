import requests
from bs4 import BeautifulSoup
import json
import re

url = "https://www.youtube.com/@VitaAnimationGroups/videos"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
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
                            title_info = video_renderer.get('title', {})
                            runs = title_info.get('runs', [])
                            if runs:
                                original_title = runs[0].get('text', '')
                                # 提取作品名称
                                start_pos = original_title.find('【') + 1
                                end_pos = original_title.find('】')
                                name = original_title[start_pos:end_pos] if start_pos != 0 and end_pos != -1 else original_title

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
                                    published_time_text = video_renderer.get('publishedTimeText', {})
                                    update_time = published_time_text.get('simpleText', '')

                                    # 存储视频信息
                                    valid_title_link_time_pairs.append((name, episode_info, link, update_time))
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue

    # 只保留最新的10条视频信息
    valid_title_link_time_pairs = valid_title_link_time_pairs[:10]

    # 格式化输出
    if valid_title_link_time_pairs:
        formatted_messages = []
        formatted_messages.append('<h1 style="text-align: center; color: red;">🔥Youtube动漫更新🔥</h1>')
        for name, episode_info, link, update_time in valid_title_link_time_pairs:
            formatted_message = (
                f'<font size="6" color="red">'
                f'<a href="{link}" style="color: red; text-decoration-color: red;"><b>{name}</b></a>'
                f'</font>  '
                f'<a href="alook://{link}" style="font-size: 4;">Alook打开</a>\n'
                f'<font size="4" color="white">第{episode_info}集🔥更新时间: {update_time}</font>\n'
            )
            formatted_messages.append(formatted_message)

        # 拼接成一条信息推送
        full_message = "".join(formatted_messages)

        # 推送消息到APP
        APP_TOKEN = "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc"
        BASE_URL = "https://wxpusher.zjiecode.com/api"
        TARGET_TOPIC_ID = [32277]

        payload = {
            "appToken": APP_TOKEN,
            "topicIds": TARGET_TOPIC_ID,
            "content": full_message,
            "contentType": 1  # 1表示文本消息
        }
        push_response = requests.post(f"{BASE_URL}/send/message", json=payload)
        if push_response.status_code == 200:
            result = push_response.json()
            if result.get("success"):
                print(f"消息已成功推送到APP: {full_message}")
            else:
                print(f"消息推送失败: {result.get('msg')}")
        else:
            print(f"消息推送请求失败，状态码: {push_response.status_code}, 响应文本: {push_response.text}")
    else:
        print("没有找到视频信息，不进行推送。")

except requests.RequestException as e:
    print(f"请求失败: {e}")
