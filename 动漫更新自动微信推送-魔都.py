import requests
from bs4 import BeautifulSoup
import datetime
import re
import os
import subprocess

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# 从环境变量中获取 wxpusher 配置
APP_TOKEN = os.environ.get('APP_TOKEN') or "YOUR_APP_TOKEN"  # 替换你的APP_TOKEN
BASE_URL = "https://wxpusher.zjiecode.com/api"
TARGET_TOPIC_IDS_STR = os.environ.get("WXPUSHER_TOPIC_IDS")
if TARGET_TOPIC_IDS_STR:
    TARGET_TOPIC_IDS = [int(x) for x in TARGET_TOPIC_IDS_STR.split(',')]
else:
    TARGET_TOPIC_IDS = [32393]  # 请替换为你的 Topic ID

# 替换你的UID
UID = os.environ.get("WXPUSHER_UID") or "YOUR_UID"  # 请替换为你的 UID

# 设置北京时间
BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def send_message(content, uids=None, topic_ids=None, summary=None, content_type=3, url=None, verify_pay_type=0):
    """发送微信消息"""
    data = {
        "appToken": APP_TOKEN,
        "content": content,
        "contentType": content_type,  # 使用 Markdown 格式
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

    response = requests.post(f"{BASE_URL}/send/message", json=data)
    return response.json()


def get_m3u8_link(detail_url, title):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        }
        response = requests.get(detail_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        match = re.search(r"更新至(\d+)集", title)
        if match:
            episode_num = match.group(1)
            links = []
            for a_tag in soup.find_all('a', class_='copy_text', target='_blank'):
                text = a_tag.get_text()
                if re.search(rf"第{episode_num}集", text):  # 使用正则表达式匹配集数
                    href = a_tag.get('href')
                    if href.startswith(('http://', 'https://')):
                        links.append(href)
                    elif href:  # 处理相对链接
                        links.append("https://www.moduzy.cc" + href)
            return links if links else None
        else:
            print(f"无法从标题 '{title}' 中提取集数")
            return None

    except requests.exceptions.RequestException as e:
        print(f"获取 {detail_url} 的链接失败: {e}")
        return None


def get_anime_updates():
    keywords = ["完美世界", "仙逆", "吞噬星空", "斗破苍穹", "斗罗大陆2", "遮天", "武神主宰", "诛仙", "独步逍遥", "万界独尊", "灵剑尊", "剑来", "赘婿", "星辰变", "武动乾坤"]
    exact_titles = ["永生之海噬仙灵", "凡人修仙传", "眷思量"]
    today = datetime.datetime.now(BEIJING_TZ).date()
    valid_dates = [(today - datetime.timedelta(days=i)) for i in range(7)]
    base_url = "https://www.moduzy.cc/list1/"
    updates = []

    for page in range(1, 6):
        url = f"{base_url}?page={page}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            table = soup.find('table')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) > 0:
                        title = cells[0].text.strip()
                        update_date = cells[2].text.strip()

                        if ((title in exact_titles) or any(keyword in title for keyword in keywords)) and update_date in [date.strftime('%Y-%m-%d') for date in valid_dates]:
                            original_link = row.find('a')['href']
                            detail_link = f"https://www.moduzy.cc{original_link}" if not original_link.startswith(
                                ('http://', 'https://')) else original_link
                            m3u8_links = get_m3u8_link(detail_link, title)

                            if m3u8_links:
                                update_date_obj = datetime.datetime.strptime(update_date, "%Y-%m-%d").replace(
                                    tzinfo=BEIJING_TZ)
                                weekday_zh = "周" + "一二三四五六日"[update_date_obj.weekday()]
                                match = re.search(r"更新至(\d+)集", title)

                                if match:
                                    title = title.replace(match.group(0), "")
                                    update_text = f"<span style='font-size: 30px;'><strong><span style='color: {'red' if update_date_obj.date() == today else 'orange'};'> {title} \n </span></strong></span><span style='font-size: 20px;'><strong><span style='color: {'red' if update_date_obj.date() == today else 'orange'};'> 第{match.group(1)}集 </span></strong></span>{'🔥' if update_date_obj.date() == today else ''} 🔥更新日期：{update_date_obj.strftime('%Y-%m-%d')} {weekday_zh}\n"
                                else:
                                    update_text = f"<span style='font-size: 30px;'><strong><span style='color: {'red' if update_date_obj.date() == today else 'orange'};'> {title} </span></strong></span>\n{'🔥🔥' if update_date_obj.date() == today else ''} 更新日期：{update_date_obj.strftime('%Y-%m-%d')} {weekday_zh}\n"

                                for link in m3u8_links:
                                    update_text += f"<a href='{link}' target='_blank'>魔都链接</a>            "
                                    update_text += f"<a href='alook://{link}' target='_blank'>Alook打开</a>            "
                                    update_text += "        "  # 设置间隔
                                update_text += f"<a href='{detail_link}' target='_blank'>详情页</a>\n\n"
                                updates.append(update_text)

            else:
                print(f"第{page}页未找到包含动漫信息的表格")

        except requests.exceptions.RequestException as e:
            print(f"获取第 {page} 页数据失败: {e}")

    return updates


def update_readme(content):
    """将内容更新到 README.md 文件"""
    try:
        with open("README.md", "w") as f:
            f.write(content)

        subprocess.run(["git", "add", "README.md"], check=True)
        subprocess.run(["git", "commit", "-m", "Update README"], check=True)
        subprocess.run(["git", "push"], check=True)

        print("README.md 更新成功！")

    except Exception as e:
        print(f"README.md 更新失败：{e}")


if __name__ == "__main__":
    updates = get_anime_updates()
    if updates:
        message = f"<center><span style='font-size: 24px;'><strong><span style='color: red;'>🔥 本周动漫更新 🔥</span></strong></span></center>\n\n\n" \
                  + "".join(updates)

        response = send_message(message, topic_ids=TARGET_TOPIC_IDS)
        print(response)

        update_readme(message)

    else:
        print("今日无更新")
