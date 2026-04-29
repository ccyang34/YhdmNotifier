
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import time
import os
import json

# ================= 配置区域 =================
# 请在环境变量中设置 DEEPSEEK_API_KEY，或直接在此处填入 (不推荐直接提交到代码库)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"  # DeepSeek 官方 API 地址

# 推送配置 (WxPusher)
WXPUSHER_APP_TOKEN = os.getenv("WXPUSHER_APP_TOKEN", "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc")
WXPUSHER_TOPIC_IDS = [42540]  # 目标主题 ID 列表
WXPUSHER_URL = "https://wxpusher.zjiecode.com/api/send/message"

# 时区配置
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_beijing_time():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ)

# ================= 数据获取与处理 (复用 v2 核心逻辑) =================

def fetch_data(retries=3, delay=2):
    url = 'https://sckd.dapanyuntu.com/api/api/industry_ma20_analysis_page?page=0'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://sckd.dapanyuntu.com/'
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"[Error] Fetching data: {e}, retrying...")
        time.sleep(delay)
    return None

def process_data(data):
    dates = data['dates']
    industries = data['industries']
    raw_data = data['data']
    parsed_data = []
    for point in raw_data:
        d_idx, i_idx, val = point
        if d_idx < len(dates) and i_idx < len(industries):
            parsed_data.append({'date': dates[d_idx], 'industry': industries[i_idx], 'value': val})
    df = pd.DataFrame(parsed_data)
    df = df.drop_duplicates(subset=['industry', 'date'])
    pivot = df.pivot(index='industry', columns='date', values='value')
    return pivot, dates

def get_sector_map():
    """
    行业板块分类映射表 (优化版)
    
    分类逻辑：
    - 科技成长：政策支持+高成长+高估值
    - 可选消费：经济向好时表现强势，受消费能力影响
    - 必选消费医药：防御属性+刚需，经济下行中相对抗跌
    - 能源资源：大宗商品+传统周期，受商品价格驱动
    - 高端制造：新能源+智能制造，受政策扶持+技术创新驱动
    - 传统制造：低端制造+建材，传统周期属性
    - 大金融：金融全板块
    - 基建物流：逆周期调节+政策对冲
    - 公用事业：防御+稳定分红
    - 房地产链：地产及后周期行业
    - 贸易综合：难以归类的综合性板块
    """
    return {
        # 1. 科技成长板块（政策支持+高成长+高估值）
        '科技成长': [
            # 半导体产业链
            '半导体', '电子元件', '光学光电子', '电子化学品',
            # 计算机与软件
            '计算机设备', '软件开发', '互联网服务',
            # 通信产业链
            '通信设备', '通信服务',
            # 新兴科技
            '消费电子'  # 保留在科技成长中，更符合产业属性
        ],
        
        # 2. 可选消费（经济向好时表现强势）
        '可选消费': [
            # 高端消费
            '酿酒行业', 
            # 耐用消费品
            '家电行业', '珠宝首饰',
            # 汽车产业链
            '汽车整车', '汽车零部件', '汽车服务',
            # 休闲服务
            '旅游酒店', '商业百货', '纺织服装', '文化传媒', '教育',
            # 家居相关（地产后周期）
            '装修建材', '装修装饰', '家用轻工'
        ],
        
        # 3. 必选消费+医药（防御属性+刚需）
        '必选消费医药': [
            # 医药全产业链
            '医药商业', '中药', '化学制药', '生物制品', '医疗器械', '医疗服务', '美容护理',
            # 农业
            '农牧饲渔',
            # 基础消费（与高端酒类区分）
            '食品饮料'  
        ],
        
        # 4. 能源资源（大宗商品+传统周期）
        '能源资源': [
            # 能源
            '煤炭行业', '石油行业', '采掘行业',
            # 金属
            '钢铁行业', '有色金属', '贵金属', '小金属', '能源金属',
            # 基础材料
            '化学原料', '化学制品', '化纤行业', '非金属材料'
        ],
        
        # 5. 高端制造（新能源+智能制造）
        '高端制造': [
            # 新能源产业链
            '光伏设备', '风电设备', '电池', '电机', '电源设备', '电网设备',
            # 高端装备
            '专用设备', '通用设备',
            # 航空航天
            '航天航空',
            # 交运装备
            '交运设备', '船舶制造',
            # 精密制造（科技属性强）
            '仪器仪表'
        ],
        
        # 6. 传统制造（低端制造+建材）
        '传统制造': [
            # 建材建筑
            '水泥建材', 
            # 传统制造
            '塑料制品', '橡胶制品', '玻璃玻纤', '造纸印刷', '包装材料',
            # 化工相关
            '化肥行业', '农药兽药'
        ],
        
        # 7. 大金融（金融全板块）
        '大金融': [
            '银行', '证券', '保险', '多元金融'
        ],
        
        # 8. 基建物流（逆周期+政策对冲）
        '基建物流': [
            # 交通运输
            '铁路公路', '航运港口', '物流行业', '航空机场',
            # 基建工程
            '工程建设', '工程咨询服务', '工程机械',
            # 专业服务
            '专业服务'
        ],
        
        # 9. 公用事业（防御+稳定分红）
        '公用事业': [
            '公用事业', '电力行业', '燃气', '环保行业'
        ],
        
        # 10. 房地产链（独立板块）
        '房地产链': [
            # 地产开发
            '房地产开发', '房地产服务'
        ],
        
        # 11. 贸易综合（难以归类的板块）
        '贸易综合': [
            '贸易行业', '综合行业',
            # 娱乐相关（难以归类）
            '游戏'  
        ]
    }

# ================= 本地预分析 (为 AI 准备数据) =================

def prepare_context_for_ai(pivot, dates):
    latest_date = dates[-1]
    
    # --- 1. 全市场分布统计 (Market Distribution) ---
    current_vals = pivot[latest_date]
    total_inds = len(current_vals)
    overheated = (current_vals > 80).sum()
    oversold = (current_vals < 20).sum()
    neutral = total_inds - overheated - oversold
    median_breadth = current_vals.median()
    avg_breadth = current_vals.mean()
    
    # --- 2. 构建完整历史数据矩阵 (Full History) ---
    # 使用所有可用日期，不进行截断
    full_dates = dates
    
    sector_map = get_sector_map()
    ind_to_sector = {}
    for sec, inds in sector_map.items():
        for ind in inds:
            ind_to_sector[ind] = sec
            
    # 构建 CSV 头: 行业,板块,日期1,日期2...
    history_csv_lines = [f"行业名称,所属板块,{','.join(full_dates)}"]
    
    # 按最新宽度降序排列
    sorted_inds = current_vals.sort_values(ascending=False).index
    
    for ind in sorted_inds:
        sector = ind_to_sector.get(ind, "其他")
        # 获取该行业在所有日期的值序列
        vals = pivot.loc[ind, full_dates]
        # 格式化数值，保留1位小数
        vals_str = ",".join([f"{v:.1f}" if pd.notnull(v) else "" for v in vals])
        history_csv_lines.append(f"{ind},{sector},{vals_str}")
    
    full_history_str = "\n".join(history_csv_lines)

    # --- 3. 构建发送给 AI 的结构化上下文 ---
    context = f"""
    [分析基准]
    数据截止日期: {latest_date}
    包含历史天数: {len(full_dates)} 天

    [市场全景统计]
    - 全市场平均宽度: {avg_breadth:.1f}%
    - 宽度中位数: {median_breadth:.1f}%
    - 极度过热(>80%)行业数: {overheated} / {total_inds}
    - 极度冰点(<20%)行业数: {oversold} / {total_inds}
    - 正常区间(20-80%)行业数: {neutral} / {total_inds}

    [全行业完整历史数据 (CSV矩阵)]
    {full_history_str}
    """
    return context

# ================= AI 分析模块 (DeepSeek) =================

def call_deepseek_analysis(context):
    if not DEEPSEEK_API_KEY or "sk-" not in DEEPSEEK_API_KEY:
        print("[Warning] 未配置 DEEPSEEK_API_KEY，跳过 AI 分析。")
        return "未配置 API Key，无法生成 AI 报告。"

    system_prompt = """你是一位拥有20年经验的A股首席策略分析师。请基于提供的全市场行业宽度数据（Market Breadth），撰写一份深度市场分析报告。

    **分析逻辑与要求：**

    1.  **全景定调 (The Big Picture)**:
        *   不要只看平均值。结合“过热/冰点”行业数量分布，判断市场情绪的极致程度。
        *   如果中位数远低于平均值，说明是少数权重股在撑场面（指数失真）；反之则是普涨。
        
    2.  **结构与主线 (Structure & Rotation)**:
        *   利用提供的全行业数据，识别当前最强的 1-2 个核心主线（Sector）。
        *   **深度挖掘**: 找出“强中之强”（领涨行业）和“弱中之强”（底部刚启动）。
        *   分析资金流向：哪些板块正在被资金抛弃（周变化大幅为负）？
        
    3.  **异动与背离 (Divergence)**:
        *   寻找“背离”现象：例如某些高位板块虽然宽度仍高，但周变化开始转负（高位派发迹象）。
        *   寻找“广度推力”：是否有大量行业在短时间内同时大幅上涨？

    4.  **实战策略 (Actionable Strategy)**:
        *   给出具体的仓位建议（0-10成）。
        *   **进攻方向**: 具体到细分行业。
        *   **防守/规避**: 点名需要回避的风险板块。

    **输出格式要求：**
    *   使用 Markdown 格式。
    *   **必须引用数据**: 在分析时，必须引用具体的宽度数值或变化率作为支撑（例如：“通信设备宽度高达85%，且周涨幅+10%...”）。
    *   语气专业、客观、有洞察力。不要使用模棱两可的废话。
    *   字数控制在 600-800 字之间，内容要详实。

    **报告结构：**
    # 深度市场宽度日报
    ## 📊 市场全景温度计
    ## 🔄 核心主线与资金流向
    ## ⚠️ 异动扫描与风险提示
    ## 💡 交易策略与建议
    """

    user_prompt = f"这是最新的全市场行业宽度数据，请开始分析：\n{context}"

    payload = {
        "model": "deepseek-v4-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.5, # 降低温度以增加分析的严谨性
        "max_tokens": 2000
    }

    try:
        response = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=60 # 增加超时时间，因为生成内容变长了
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"AI 请求失败: {response.text}"
    except Exception as e:
        return f"AI 请求异常: {e}"

# ================= 消息推送模块 =================

def send_push(title, content):
    """
    使用 WxPusher 推送消息
    """
    print("\n" + "="*20 + f" PUSH: {title} " + "="*20)
    # print(content) # 控制台不重复打印详细内容，避免刷屏
    print("正在发送 WxPusher 推送...")
    print("="*50 + "\n")
    
    payload = {
        "appToken": WXPUSHER_APP_TOKEN,
        "content": content,
        "summary": title, # 消息摘要，显示在列表页
        "contentType": 3, # 3 表示 Markdown
        "topicIds": WXPUSHER_TOPIC_IDS,
        "verifyPay": False
    }
    
    try:
        response = requests.post(WXPUSHER_URL, json=payload, timeout=10)
        resp_json = response.json()
        if response.status_code == 200 and resp_json.get('code') == 1000:
            print(f"[Info] WxPusher 推送成功: {resp_json.get('msg')}")
        else:
            print(f"[Error] WxPusher 推送失败: {resp_json}")
    except Exception as e:
        print(f"[Error] WxPusher 请求异常: {e}")

# ================= 主程序 =================

def main():
    beijing_time = get_beijing_time()
    print(f"[{beijing_time.strftime('%H:%M:%S')}] 开始执行市场分析任务...")
    
    # 1. 获取数据
    data = fetch_data()
    if not data:
        print("[Error] 数据获取失败，任务终止。")
        return

    # 2. 处理数据
    pivot, dates = process_data(data)
    
    # 检查最新数据日期是否为今天
    latest_date = dates[-1]
    today_date = beijing_time.strftime('%Y-%m-%d')
    if latest_date != today_date:
        print(f"[Warning] 数据最新日期 ({latest_date}) 不等于今天 ({today_date})，跳过数据分析和推送。")
        return
    
    # 3. 生成数据上下文
    context = prepare_context_for_ai(pivot, dates)
    print("--- 生成的数据上下文 ---")
    print(context)
    
    # 4. 调用 AI 分析
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 正在请求 DeepSeek 进行分析...")
    ai_report = call_deepseek_analysis(context)
    
    # 5. 组合最终报告
    beijing_time = get_beijing_time()
    report_header = f"""
> **推送时间**: {beijing_time.strftime('%Y-%m-%d %H:%M')} (北京时间) | 每个交易日下午 15:30 推送
> **最新数据日期**: {latest_date}
> **市场宽度定义**: 市场宽度（Market Breadth）是指当前处于 20 日均线（MA20）之上的股票占比。宽度越高，说明市场参与度越广，赚钱效应越强；反之则表明市场情绪低迷，仅少数个股活跃。
> - **< 20%**: 极度冰点，往往是底部区域
> - **20-80%**: 正常震荡区间
> - **> 80%**: 极度过热，往往是顶部区域

---
"""
    
    final_report = report_header + ai_report + f"""

---
*数据来源: 大盘云图 | AI 分析: DeepSeek*
    """
    
    # 6. 保存与推送
    # 保存
    filename = f"ai_market_report_{beijing_time.strftime('%Y%m%d')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(final_report)
    print(f"[Info] 报告已保存至 {filename}")
    
    # 推送
    push_title = f"📈 A股市场宽度日报 ({beijing_time.strftime('%Y-%m-%d')})"
    send_push(push_title, final_report)

if __name__ == "__main__":
    main()
