import os
import csv
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import time
import json

# ================= 配置区域 =================
# 数据获取配置
DEFAULT_DAYS = 10  # 默认获取最近10天的数据
ENABLE_PUSH = True  # 是否启用消息推送

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"  # 标准基础URL
MODEL_NAME = "deepseek-v4-flash"

# 推送配置 (WxPusher)
WXPUSHER_APP_TOKEN = os.getenv("WXPUSHER_APP_TOKEN", "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc")
WXPUSHER_TOPIC_IDS = [42540]  # 目标主题 ID 列表
WXPUSHER_URL = "https://wxpusher.zjiecode.com/api/send/message"

# 时区配置
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_beijing_time():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ)

# ================= 数据获取核心函数模块 =================

def fetch_page(date_str, zdt_type, page_num):
    """
    Fetch a single page of ZDT data.
    """
    url = "https://gateway.jrj.com/quot-dc/zdt/v1/record"
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
        "Referer": "https://summary.jrj.com.cn/",
        "Origin": "https://summary.jrj.com.cn",
        "deviceinfo": '{"productId":"6000021","version":"1.0.0","device":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0","sysName":"Chrome","sysVersion":["chrome/142.0.0.0"]}',
        "productId": "6000021",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
    }

    payload = {
        "td": date_str,
        "zdtType": zdt_type,
        "pageNum": page_num,
        "pageSize": 20
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"获取第 {page_num} 页时出错: {e}")
        return None

def fetch_all_jrj_data(date_str=None, zdt_type="dt"):
    """
    Fetch all pages of ZDT data.
    """
    if not date_str:
        date_str = datetime.now().strftime("%Y%m%d")
        
    all_items = []
    page_num = 1
    
    print(f"[{date_str}] 正在获取 {zdt_type.upper()} 数据...")
    
    while True:
        data = fetch_page(date_str, zdt_type, page_num)
        if not data or 'data' not in data:
            break
            
        page_data = data['data']
        items = page_data.get('list', [])
        if not items:
            break

        all_items.extend(items)
        
        if not page_data.get('hasNextPage'):
            break
            
        page_num += 1
        time.sleep(0.2)  # Reduced delay for faster batch processing
        
    return all_items

def fetch_last_days(days=10, start_date_str=None):
    """
    Fetch data for the last N trading days.
    Returns all data as a dictionary instead of saving to files.
    """
    if not start_date_str:
        start_date_str = datetime.now().strftime("%Y%m%d")
        
    current_date = datetime.strptime(start_date_str, "%Y%m%d")
    days_collected = 0
    max_lookback = days * 3  # Avoid infinite loop if long holidays
    days_checked = 0
    
    print(f"正在获取从 {start_date_str} 开始过去 {days} 个交易日的数据...")
    
    # Store all data in memory
    all_data = {}
    
    while days_collected < days and days_checked < max_lookback:
        date_str = current_date.strftime("%Y%m%d")
        
        print(f"\n正在处理日期: {date_str}")
        
        # Fetch Limit Up (ZT) first as it's more likely to exist
        items_zt = fetch_all_jrj_data(date_str=date_str, zdt_type="zt")
        
        # Fetch Limit Down (DT)
        items_dt = fetch_all_jrj_data(date_str=date_str, zdt_type="dt")
        
        # If we got any data, count it as a valid day
        if items_zt or items_dt:
            all_data[f"{date_str}_zt"] = items_zt
            all_data[f"{date_str}_dt"] = items_dt
            
            days_collected += 1
            print(f"找到 {date_str} 的有效数据。({days_collected}/{days})")
        else:
            print(f"未找到 {date_str} 的数据（可能是节假日/周末）。")
            
        # Go back one day
        current_date -= timedelta(days=1)
        days_checked += 1
        
        # Be polite
        time.sleep(0.5)

    print(f"\n完成。共收集了 {days_collected} 天的数据。")
    return all_data

# ================= 数据获取与处理模块 =================

def read_csv_content(file_path):
    """读取CSV文件内容并返回为字符串。"""
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        return f.read()

def process_memory_data_to_csv(memory_data):
    """
    将内存中的数据直接转换为CSV格式字符串
    """
    import csv
    from io import StringIO
    
    # 创建内存CSV缓冲区
    output = StringIO()
    
    # 定义CSV字段，确保与analyze_market_structure函数期望的字段一致
    csv_fields = ['日期', '类型', '股票代码', '股票名称', '最新价', '涨跌幅', '振幅', '成交额', '换手率', '连板天数', '封单时间']
    
    # 写入CSV头部
    writer = csv.DictWriter(output, fieldnames=csv_fields)
    writer.writeheader()
    
    # 处理内存数据
    for key, items in memory_data.items():
        if items:  # 确保有数据
            date_str = key.split('_')[0]  # 提取日期
            zdt_type = '涨停' if 'zt' in key else '跌停'
            
            for item in items:
                # 构建CSV行数据，确保所有字段都存在
                row_data = {
                    '日期': date_str,
                    '类型': zdt_type,
                    '股票代码': item.get('code', ''),
                    '股票名称': item.get('name', ''),
                    '最新价': item.get('last_price', 0),
                    '涨跌幅': item.get('pct_chg', 0),
                    '振幅': item.get('amp', 0),
                    '成交额': item.get('amt', 0),
                    '换手率': item.get('turnover_rate', 0),
                    '连板天数': item.get('lianban_days', 0),
                    '封单时间': item.get('order_time', '')
                }
                writer.writerow(row_data)
    
    csv_content = output.getvalue()
    output.close()
    
    # 调试：打印前几行CSV内容
    csv_lines = csv_content.strip().split('\n')
    print(f"[Debug] CSV头部: {csv_lines[0] if csv_lines else 'None'}")
    if len(csv_lines) > 1:
        print(f"[Debug] CSV第一行数据: {csv_lines[1]}")
    
    return csv_content

def fetch_market_data(days=DEFAULT_DAYS):
    """
    获取市场数据
    数据全部通过网络获取，不保存到本地文件
    """
    print("=== 第一步：网络获取最新市场数据 ===")
    # 直接获取内存数据，不保存到文件
    memory_data = fetch_last_days(days=days)
    
    if not memory_data:
        print("网络获取数据失败。")
        return None, None

    print(f"\n=== 第二步：将内存数据转换为 CSV 格式 ===")
    # 直接处理内存数据为CSV格式
    csv_content = process_memory_data_to_csv(memory_data)
    
    if not csv_content:
        print("转换 CSV 格式失败。")
        return None, None

    print(f"\n=== 第三步：准备数据进行分析 ===")
    # 不需要读取文件，直接使用内存中的CSV内容
    csv_lines = csv_content.strip().split('\n')
    print(f"[Info] 成功转换 {len(csv_lines)-1} 条数据记录")
    
    return "memory_data.csv", csv_content

# ================= 数据预分析模块 =================

def analyze_market_structure(csv_content, days=DEFAULT_DAYS):
    """
    对涨停跌停数据进行结构化分析
    为AI分析准备更丰富的上下文数据
    """
    # 解析CSV数据
    lines = csv_content.strip().split('\n')
    if len(lines) < 2:
        return None
    
    headers = lines[0].split(',')
    data_lines = lines[1:]
    
    # 构建DataFrame
    data_rows = []
    for line in data_lines:
        if line.strip():
            data_rows.append(line.split(','))
    
    if not data_rows:
        return None
    
    df = pd.DataFrame(data_rows, columns=headers)
    
    # 数据类型转换
    numeric_columns = ['最新价', '涨跌幅', '振幅', '成交额', '换手率', '连板天数']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 按日期分组分析
    date_groups = df.groupby('日期')
    
    analysis_result = {
        'summary': {},
        'daily_stats': {},
        'sector_analysis': {},
        'risk_analysis': {},
        'trading_heat': {}
    }
    
    # 全局统计
    total_records = len(df)
    zt_count = len(df[df['类型'] == '涨停'])
    dt_count = len(df[df['类型'] == '跌停'])
    
    analysis_result['summary'] = {
        'total_records': total_records,
        'zt_count': zt_count,
        'dt_count': dt_count,
        'date_range': f"{df['日期'].min()} 至 {df['日期'].max()}" if not df['日期'].empty else "未知"
    }
    
    # 每日统计分析
    for date, group in date_groups:
        zt_daily = len(group[group['类型'] == '涨停'])
        dt_daily = len(group[group['类型'] == '跌停'])
        
        # 连板分析
        max_lianban = group['连板天数'].max() if '连板天数' in group.columns else 0
        lianban_distribution = group['连板天数'].value_counts().to_dict() if '连板天数' in group.columns else {}
        
        # 平均涨跌幅分析
        avg_zt_change = group[group['类型'] == '涨停']['涨跌幅'].mean() if len(group[group['类型'] == '涨停']) > 0 else 0
        avg_dt_change = group[group['类型'] == '跌停']['涨跌幅'].mean() if len(group[group['类型'] == '跌停']) > 0 else 0
        
        analysis_result['daily_stats'][date] = {
            'zt_count': zt_daily,
            'dt_count': dt_daily,
            'max_lianban': max_lianban,
            'lianban_distribution': lianban_distribution,
            'avg_zt_change': avg_zt_change,
            'avg_dt_change': avg_dt_change
        }
    
    # 板块分析（基于股票名称关键词）
    sector_keywords = {
        '军工': ['军工', '航天', '船舶', '航空', '中船', '江龙', '亚星', '长城', '北斗', '卫星', '导弹', '防务'],
        '科技': ['科技', '软件', '电子', '信息', '通信', '互联网', '芯片', '半导体', '人工智能', '算力', '数据', '云计算', '5G', '物联网', '信创'],
        '消费': ['食品', '饮料', '酒', '消费', '零售', '百货', '服装', '家电', '家居', '乳业', '调味品', '啤酒', '白酒', '黄酒'],
        '新能源': ['新能源', '锂电', '电池', '光伏', '风电', '储能', '氢能', '充电桩', '锂矿', '钴', '镍', '硅片', '逆变器', '绿电'],
        '医药': ['医药', '医疗', '生物', '制药', '健康', '疫苗', '创新药', 'CXO', '器械', '中药', '医美', '养老'],
        '金融': ['银行', '证券', '保险', '金融', '期货', '信托', '支付', '数字货币', '互金', '券商', 'AMC'],
        '地产': ['地产', '房产', '建筑', '建材', '装修', '物业', '家居', '水泥', '钢铁', '工程机械', '基建'],
        '汽车': ['汽车', '整车', '零部件', '新能源整车', '智能驾驶', '车联网', '热管理', '轻量化', '一体化压铸'],
        '周期': ['煤炭', '有色', '化工', '石油', '天然气', '稀土', '黄金', '铜', '铝', '铅锌', '钛', '氟化工', '磷化工', '化纤'],
        '农业': ['农业', '种植', '养殖', '饲料', '种子', '化肥', '农药', '渔业', '猪肉', '鸡肉', '糖业', '橡胶'],
        '电力': ['电力', '火电', '水电', '核电', '电网', '特高压', '电力改革', '虚拟电厂'],
        '环保': ['环保', '水务', '固废', '大气治理', '垃圾分类', '再生资源', '动力电池回收'],
        '传媒': ['传媒', '游戏', '影视', '出版', '广告', '直播', '短视频', '元宇宙', 'NFT'],
        '教育': ['教育', '培训', '职教', '高教', '在线教育'],
        '旅游': ['旅游', '酒店', '餐饮', '航空', '机场', '免税', '景区'],
        '物流': ['物流', '快递', '航运', '港口', '铁路', '公路', '供应链'],
        '公用': ['燃气', '供热', '环卫', '公交', '地铁']
    }
    
    for sector, keywords in sector_keywords.items():
        sector_stocks = df[df['股票名称'].str.contains('|'.join(keywords), na=False)]
        if len(sector_stocks) > 0:
            zt_in_sector = len(sector_stocks[sector_stocks['类型'] == '涨停'])
            dt_in_sector = len(sector_stocks[sector_stocks['类型'] == '跌停'])
            analysis_result['sector_analysis'][sector] = {
                'total': len(sector_stocks),
                'zt_count': zt_in_sector,
                'dt_count': dt_in_sector
            }
    
    # 风险分析
    high_risk_stocks = df[
        (df['连板天数'] >= 3) |  # 高位连板
        (df['类型'] == '跌停') & (df['涨跌幅'] < -0.09)  # 深度跌停
    ]
    
    analysis_result['risk_analysis'] = {
        'high_risk_count': len(high_risk_stocks),
        'high_risk_stocks': high_risk_stocks['股票名称'].tolist()[:10]  # 前10只
    }
    
    # 交易热度分析
    if '成交额' in df.columns:
        df['成交额'] = pd.to_numeric(df['成交额'], errors='coerce')
        high_volume_stocks = df.nlargest(20, '成交额')
        analysis_result['trading_heat'] = {
            'total_volume': df['成交额'].sum(),
            'high_volume_stocks': high_volume_stocks[['股票代码', '股票名称', '成交额', '类型']].to_dict('records')
        }
    
    return analysis_result

# ================= AI 分析模块 =================

def prepare_ai_context(csv_content, analysis_result):
    """
    为AI准备结构化的分析上下文
    """
    if not analysis_result:
        return "数据分析失败，无法生成报告。"
    
    summary = analysis_result['summary']
    daily_stats = analysis_result['daily_stats']
    sector_analysis = analysis_result['sector_analysis']
    risk_analysis = analysis_result['risk_analysis']
    
    # 计算CSV大小，控制是否直接嵌入
    csv_size = len(csv_content)
    
    # 构建结构化提示词
    context = f"""
[市场数据概览]
- 分析周期: {summary['date_range']}
- 总记录数: {summary['total_records']} 条
- 涨停股票: {summary['zt_count']} 只
- 跌停股票: {summary['dt_count']} 只

[每日市场温度计]"""
    
    # 添加每日数据
    for date, stats in daily_stats.items():
        context += f"""
- {date}: 涨停{stats['zt_count']}只, 跌停{stats['dt_count']}只, 最高连板{stats['max_lianban']}天"""
    
    # 添加板块分析
    if sector_analysis:
        context += f"""
[热门板块分析]"""
        for sector, data in sector_analysis.items():
            if data['total'] > 0:
                context += f"""
- {sector}: {data['zt_count']}涨停/{data['dt_count']}跌停"""
    
    # 添加风险提示
    if risk_analysis['high_risk_count'] > 0:
        context += f"""
[风险提示]
- 高风险股票: {risk_analysis['high_risk_count']}只
- 重点关注: {', '.join(risk_analysis['high_risk_stocks'][:5])}等"""
    
    # 始终直接嵌入完整CSV数据，便于检查
    context += f"""
[完整CSV数据]
{csv_content}
"""
    print(f"[Info] CSV数据大小: {csv_size} 字符，直接嵌入提示词 (共{summary['total_records']}条记录)")
    
    return context

def call_ai_analysis(csv_content, analysis_result):
    """
    调用DeepSeek进行市场分析
    """
    if not DEEPSEEK_API_KEY or "sk-" not in DEEPSEEK_API_KEY:
        print("[Warning] 未配置 DEEPSEEK_API_KEY，跳过 AI 分析。")
        return "未配置 API Key，无法生成 AI 报告。"

    # 准备AI上下文
    context = prepare_ai_context(csv_content, analysis_result)
    
    # 构建专业提示词
    prompt = f"""
你是一位专注于中国A股市场的资深金融分析师。
我将为你提供最新{len(analysis_result['daily_stats']) if analysis_result else 1}个交易日的涨停（Limit Up）和跌停（Limit Down）数据。

数据格式：CSV格式，包含表头（日期、类型、股票代码、股票名称、最新价、涨跌幅、振幅、成交额、换手率、连板天数、封单时间等）。

{context}

请根据提供的数据生成一份全面的市场分析报告，涵盖以下方面：
📈 **市场情绪趋势**：分析每日涨停与跌停股票数量的变化趋势。市场情绪是在回暖🔥还是降温❄️？
🔥 **短线炒作热度**：关注"连板天数"。是否有高位连板股（妖股/龙头）出现？目前市场的空间板高度是多少？
🎯 **热门板块**：根据股票名称（结合你对A股板块的了解），识别当前活跃的题材或概念（如人工智能、房地产、消费等）。
⚠️ **风险提示**：如果跌停数量增加或高位股出现亏钱效应（核按钮），请给出风险警示。
📊 **总结与展望**：对当前市场阶段进行简要总结。
💡 **投资建议**：基于上述分析，给出针对短线选手和稳健型投资者的具体投资建议（例如：仓位管理、方向选择、回避板块等）。

请直接输出中文报告。
"""

    # 打印完整提示词用于检查，CSV数据过多时只显示部分
    lines = csv_content.strip().split('\n')
    print("-" * 20 + " 提示词内容开始(显示CSV样例) " + "-" * 20)
    if len(lines) <= 20:
        # 数据量少时显示完整内容
        print(prompt)
    else:
        # 数据量大时只显示CSV前后部分样例
        # 构建显示版本的prompt
        head = '\n'.join(lines[:11])  # 表头+前10行数据
        tail = '\n'.join(lines[-10:])  # 后10行数据
        
        # 创建省略版本的CSV内容
        omit_csv = head + '\n...(中间省略 {} 行)...\n'.format(len(lines) - 20) + tail
        
        # 替换prompt中的完整CSV为省略版本
        display_prompt = prompt.replace(csv_content, omit_csv)
        print(display_prompt)
    print("-" * 20 + " 提示词内容结束 " + "-" * 20)

    print("\n=== 向 DeepSeek API 发送请求 ===")
    
    # 使用requests直接调用DeepSeek API
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "你是一位乐于助人的金融分析师。"},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }

    try:
        response = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                report = result['choices'][0]['message']['content']
                return report
            else:
                print(f"DeepSeek API 返回格式异常: {result}")
                return "DeepSeek API 返回格式异常"
        else:
            print(f"DeepSeek API 请求失败: {response.status_code} - {response.text}")
            return f"DeepSeek API 请求失败: {response.status_code}"
            
    except Exception as e:
        print(f"调用 DeepSeek API 出错: {e}")
        return f"AI 分析失败: {e}"

# ================= 消息推送模块 =================

def send_push(title, content):
    """
    使用 WxPusher 推送消息
    """
    print("\n" + "="*20 + f" PUSH: {title} " + "="*20)
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

def main(days=DEFAULT_DAYS, enable_push=ENABLE_PUSH):
    """
    主分析流程
    借鉴AI市场宽度分析师的主程序结构
    """
    beijing_time = get_beijing_time()
    print(f"[{beijing_time.strftime('%H:%M:%S')}] 开始执行涨停跌停市场分析任务...")
    
    # 1. 获取数据
    csv_file, csv_content = fetch_market_data(days=days)
    if not csv_file or not csv_content:
        print("[Error] 数据获取失败，任务终止。")
        return

    # 2. 数据预分析
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 正在进行数据预分析...")
    analysis_result = analyze_market_structure(csv_content, days=days)
    if not analysis_result:
        print("[Error] 数据预分析失败，任务终止。")
        return

    # 3. AI分析
    print(f"[{get_beijing_time().strftime('%H:%M:%S')}] 正在请求 DeepSeek 进行深度分析...")
    ai_report = call_ai_analysis(csv_content, analysis_result)

    # 4. 生成最终报告
    beijing_time = get_beijing_time()
    report_header = f"""
> **推送时间**: {beijing_time.strftime('%Y-%m-%d %H:%M')} (北京时间)
> **分析周期**: {analysis_result['summary']['date_range']}
> **数据来源**: 涨跌停股票明细
> **分析方法**: AI深度分析 + 结构化数据解析

---
"""
    
    final_report = report_header + ai_report + f"""

---
*数据来源: 涨停跌停统计 | AI 分析: DeepSeek*
    """
    
    # 5. 保存报告
    filename = f"zt_dt_analysis_report_{beijing_time.strftime('%Y%m%d')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(final_report)
    print(f"[Info] 报告已保存至 {filename}")
    
    # 6. 控制台输出报告
    print("\n" + "="*50)
    print("涨停跌停市场分析报告")
    print("="*50 + "\n")
    print(ai_report)
    
    # 7. 推送消息（可选）
    if enable_push:
        push_title = f"A股涨跌停分析 ({beijing_time.strftime('%Y-%m-%d')})"
        send_push(push_title, final_report)

# 程序直接运行主函数
main(days=DEFAULT_DAYS, enable_push=ENABLE_PUSH)
