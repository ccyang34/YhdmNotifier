import requests
from bs4 import BeautifulSoup
import json
import re

url = "https://www.youtube.com/@VitaAnimationGroups/videos"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # 如果请求失败，抛出异常
    html_content = response.text

    # 创建 BeautifulSoup 对象
    soup = BeautifulSoup(html_content, 'html.parser')

    # 这里假设包含视频信息的 JSON 数据在 script 标签中，你需要根据实际情况调整查找方式
    # 比如查找包含特定关键字的 script 标签
    script_tags = soup.find_all('script')
    title_link_time_pairs = []
    for script_tag in script_tags:
        script_text = script_tag.string
        if script_text:
            try:
                # 尝试找到 JSON 数据部分
                start_index = script_text.find('{')
                end_index = script_text.rfind('}') + 1
                if start_index != -1 and end_index != -1:
                    json_str = script_text[start_index:end_index]
                    # 解析 JSON 数据
                    data = json.loads(json_str)

                    # 遍历数据结构来查找视频标题、播放链接和更新时间
                    # 这里需要根据实际的 JSON 结构调整路径
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
                                pattern = r'(?:Episode|EP|第|Season\s+\d+\s+Episode|集数)\s*(\d+|[0-9]+\s*-\s*[0-9]+|[0-9]+\s*-\s*[0-9]+\s*Collection|Collection\s+of\s+Episodes\s+\d+-\d+)\s*(?:集|Collection|#\d+|Full)?'
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

                                    title_link_time_pairs.append((name, episode_info, link, update_time))
            except (json.JSONDecodeError, IndexError, KeyError):
                continue

    # 格式化输出
    formatted_messages = []
    formatted_messages.append('<h1 style="text-align: center; color: red;">🔥Youtube动漫更新🔥</h1>')
    for name, episode_info, link, update_time in title_link_time_pairs:
        formatted_message = (
            f'<font size="6" color="red">'
            f'<a href="{link}" style="color: red; text-decoration-color: red;"><b>{name}</b></a>'
            f'</font>  '
            f'<a href="alook://{link}" style="font-size: 4;">Alook打开</a>\n'
            f'<font size="4" color="white">第{episode_info}集🔥更新时间: {update_time}</font>\n'
        )
        # 检查更新时间是否符合规则
        if re.search(r'<font size="4" color="white">.*?(分鐘前|小時前).*?</font>', formatted_message):
            formatted_messages.append(formatted_message)

    # 检查是否有符合条件的消息
    if len(formatted_messages) > 1:  # 除了标题外还有其他消息
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
            print(f"消息已成功推送到APP: {full_message}")
        else:
            print(f"消息推送失败: {push_response.text}")
    else:
        print("没有符合更新时间条件的结果，不进行推送。")

except requests.RequestException as e:
    print(f"请求失败: {e}")
