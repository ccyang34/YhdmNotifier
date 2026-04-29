import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import os
import pytz

# ================= 配置区域 =================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# 推送配置 (WxPusher)
WXPUSHER_APP_TOKEN = os.getenv("WXPUSHER_APP_TOKEN", "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc")
WXPUSHER_TOPIC_IDS = [42624] # 这里假设使用与其他脚本相同的 topic
WXPUSHER_URL = "https://wxpusher.zjiecode.com/api/send/message"

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_beijing_time():
    return datetime.datetime.now(BEIJING_TZ)

def fetch_10jqka_etf_data():
    """抓取同花顺ETF数据中心的全量数据"""
    base_url = "http://fund.10jqka.com.cn/datacenter/sy/kfs/etf/p/{}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    all_data = []
    
    print("开始抓取同花顺ETF数据...")
    for page in range(1, 30): # ETF约有20多页，假设最多30页
        url = base_url.format(page)
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'gbk'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            tbody = soup.find('tbody')
            if not tbody:
                break
                
            rows = tbody.find_all('tr')
            if not rows:
                break
                
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 12:
                    code = cols[2].text.strip()
                    name = cols[3].text.strip()
                    date = cols[5].text.strip()
                    w_ret = cols[6].text.strip()
                    m1_ret = cols[7].text.strip()
                    m3_ret = cols[8].text.strip()
                    m6_ret = cols[9].text.strip()
                    y1_ret = cols[10].text.strip()
                    total_ret = cols[11].text.strip()
                    nav = cols[12].text.strip()
                    
                    all_data.append({
                        "代码": code,
                        "名称": name,
                        "日期": date,
                        "周收益(%)": w_ret,
                        "近一月(%)": m1_ret,
                        "近三月(%)": m3_ret,
                        "近半年(%)": m6_ret,
                        "近一年(%)": y1_ret,
                        "总收益(%)": total_ret,
                        "净值": nav
                    })
            print(f"✅ 第 {page} 页抓取完成, 当前累计 {len(all_data)} 条记录")
            
            # 判断是否是最后一页
            page_info = soup.find('div', class_='page_info')
            if page_info:
                info_text = page_info.text.strip()
                if '/' in info_text:
                    curr, total = info_text.split('/')
                    if curr == total:
                        break
        except Exception as e:
            print(f"❌ 抓取第 {page} 页时发生错误: {e}")
            break
            
    df = pd.DataFrame(all_data)
    print(f"抓取完成，共获取 {len(df)} 只ETF数据。")
    return df

def call_deepseek_analysis(df):
    if not DEEPSEEK_API_KEY or "sk-" not in DEEPSEEK_API_KEY:
        return "⚠️ 未配置 DEEPSEEK_API_KEY，无法生成报告。"
        
    print("正在准备发送给 DeepSeek 的数据...")
    csv_data = df.to_csv(index=False)
    
    system_prompt = """你是一位资深的量化分析师和ETF研究专家。
你的任务是接收全量ETF收益率数据，并进行深度数据挖掘和分析，输出一份专业、清晰的市场分析报告。

【分析要求】
1. 整体市场温度：基于各周期（周、月、季、半年、年）的平均收益率、正收益占比等指标，评估市场整体情绪和赚钱效应。
2. 强势板块/主题识别：找出近期（近一月、近三月）收益率霸榜的ETF，归纳出当前市场的核心主线。
3. 弱势板块/主题识别：找出近期跌幅最大的ETF，提示风险。
4. 趋势动量反转分析：对比短期（周、月）和中长期（半年、年）收益率，寻找动量反转或持续的迹象。
5. 投资建议：基于以上数据分析，给出客观的资产配置建议（建议不超过3条）。

【输出格式】
请使用 Markdown 格式排版，包含合适的表情符号。
内容需严谨、数据驱动（引用具体数据支撑结论），避免空话。
"""

    user_prompt = f"以下是同花顺ETF数据中心获取的全市场ETF最新收益率数据（CSV格式，包含{len(df)}只ETF）：\n\n{csv_data}\n\n请根据以上全量数据，撰写一份深度的ETF市场分析报告。"

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 8000
    }

    try:
        print("正在请求 DeepSeek API (数据量较大，可能需要几分钟)...")
        response = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=300
        )
        if response.status_code == 200:
            print("✅ DeepSeek 分析完成")
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"❌ API 返回错误: {response.text}")
            return f"AI 请求失败 (HTTP {response.status_code}): {response.text}"
    except Exception as e:
        print(f"❌ API 请求异常: {e}")
        return f"AI 请求异常: {e}"

def send_push(title, content):
    print("\n" + "="*20 + f" PUSH: {title} " + "="*20)
    print("正在发送 WxPusher 推送...")
    
    if len(content) > 39000:
        content = content[:39000] + "\n\n...[内容过长，已被截断]..."

    payload = {
        "appToken": WXPUSHER_APP_TOKEN,
        "content": content,
        "summary": title,
        "contentType": 3,
        "topicIds": WXPUSHER_TOPIC_IDS,
        "verifyPay": False
    }
    
    try:
        response = requests.post(WXPUSHER_URL, json=payload, timeout=10)
        resp_json = response.json()
        if response.status_code == 200 and resp_json.get('code') == 1000:
            print(f"✅ WxPusher 推送成功: {resp_json.get('msg')}")
        else:
            print(f"❌ WxPusher 推送失败: {resp_json}")
    except Exception as e:
        print(f"❌ WxPusher 请求异常: {e}")

def main():
    beijing_time = get_beijing_time()
    print(f"[{beijing_time.strftime('%Y-%m-%d %H:%M:%S')}] 开始执行同花顺ETF全量数据抓取与分析任务...")
    
    df = fetch_10jqka_etf_data()
    if df.empty:
        print("❌ 未获取到任何数据，任务终止。")
        return
        
    report_content = call_deepseek_analysis(df)
    
    final_report = f"""> **分析时间**: {beijing_time.strftime('%Y-%m-%d %H:%M')} (北京时间)
> **数据来源**: 同花顺ETF数据中心 (共 {len(df)} 只ETF)
> **AI模型**: DeepSeek (基于全量数据挖掘)

---
{report_content}
"""

    push_title = f"📊 同花顺ETF全市场深度分析 ({beijing_time.strftime('%Y-%m-%d')})"
    send_push(push_title, final_report)

if __name__ == "__main__":
    main()
