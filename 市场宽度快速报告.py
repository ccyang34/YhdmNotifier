#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""市场宽度快速报告生成工具
直接获取数据并在控制台打印完整报告，包含行业趋势和ETF推荐"""

import requests
import json
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 推送配置
APP_TOKEN = "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc"
BASE_URL = "https://wxpusher.zjiecode.com/api"
TARGET_TOPIC_ID = [42540]

# 颜色常量定义
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'  # 绿色文本
    WARNING_TEXT = '\033[93m'  # 黄色文本警告
    FAIL = '\033[91m'  # 红色文本
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    # 特殊符号
    UP_ARROW = '📈'
    DOWN_ARROW = '📉'
    STAR = '⭐'
    INFO = 'ℹ️'
    WARNING_SYMBOL = '⚠️'

# 行业对应的ETF映射关系
industry_etf_map = {
    '船舶制造': ['512760', '中国船舶ETF'],
    '航天航空': ['516670', '军工ETF'],
    '燃气': ['159651', '燃气ETF'],
    '能源金属': ['516060', '稀土ETF'],
    '橡胶制品': ['159996', '家电ETF'],  # 橡胶制品相关ETF较少，可用化工ETF替代
    '教育': ['513360', '教育ETF'],
    '珠宝首饰': ['159646', '黄金ETF'],  # 珠宝首饰相关ETF较少，可用黄金ETF替代
    '软件开发': ['515330', '软件ETF'],
    '互联网服务': ['513050', '中概互联ETF'],
    '化纤行业': ['159885', '化纤ETF'],
    '装修建材': ['159745', '建材ETF'],
    '造纸印刷': ['159679', '造纸ETF'],
    '酿酒行业': ['512690', '酒ETF'],
    '采掘行业': ['159825', '煤炭ETF'],
    '钢铁行业': ['515210', '钢铁ETF'],
    '食品饮料': ['159843', '食品饮料ETF'],
    '半导体': ['512480', '半导体ETF'],
    '小金属': ['516020', '有色金属ETF'],  # 小金属相关ETF较少，可用有色金属ETF替代
    '贵金属': ['518880', '黄金ETF']
}

def get_and_parse_data():
    """获取并解析市场宽度数据"""
    print(f"{Colors.OKGREEN}{Colors.BOLD}🚀 市场宽度快速报告生成工具{Colors.ENDC}")
    print(f"{Colors.OKBLUE}正在获取最新的行业市场宽度数据...{Colors.ENDC}")
    print(f"{Colors.HEADER}=========================================")
    
    # API配置
    url = 'https://sckd.dapanyuntu.com/api/api/industry_ma20_analysis_page?page=0'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://sckd.dapanyuntu.com/'
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"{Colors.FAIL}❌ API请求失败，状态码: {response.status_code}{Colors.ENDC}")
            return None, None
            
        data = response.json()
        
        # 检查必要字段
        required_fields = ['dates', 'industries', 'data']
        for field in required_fields:
            if field not in data:
                print(f"{Colors.WARNING_SYMBOL} 数据中缺少必要字段: {field}{Colors.ENDC}")
                return None, None
                
        dates = data['dates']
        industries = data['industries']
        raw_data = data['data']
        
        print(f"{Colors.OKGREEN}✅ 成功获取数据：{Colors.ENDC}")
        print(f"  {Colors.INFO} - 日期范围: {dates[0]} 至 {dates[-1]} (共 {len(dates)} 天)")
        print(f"  {Colors.INFO} - 行业数量: {len(industries)} 个")
        print(f"  {Colors.INFO} - 数据点数量: {len(raw_data)}")
        
        # 解析数据点
        parsed_data = []
        for data_point in raw_data:
            date_idx, industry_idx, breadth_ratio = data_point
            date = dates[date_idx] if date_idx < len(dates) else "未知日期"
            industry = industries[industry_idx] if industry_idx < len(industries) else "未知行业"
            
            parsed_data.append({
                'date': date,
                'industry': industry,
                'above_ma20_ratio': breadth_ratio
            })
        
        # 创建数据框并转换为二维表格式
        df = pd.DataFrame(parsed_data)
        pivot_df = df.pivot(index='industry', columns='date', values='above_ma20_ratio')
        
        print(f"{Colors.OKGREEN}✅ 数据解析完成{Colors.ENDC}")
        return pivot_df, data
        
    except Exception as e:
        print(f"{Colors.FAIL}❌ 获取数据失败: {e}{Colors.ENDC}")
        return None, None

def send_wxpush_message(title, content):
    """使用WxPusher推送消息"""
    import requests
    import json
    
    url = f"{BASE_URL}/send/message"
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "appToken": APP_TOKEN,
        "content": content,
        "summary": title,
        "contentType": 1,  # 纯文本格式，支持普通换行符和HTML颜色标签
        "topicIds": TARGET_TOPIC_ID,
        "verifyPay": False
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        result = response.json()
        if result.get("success"):
            print(f"{Colors.OKGREEN}✅ 报告已成功推送到微信{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.FAIL}❌ 微信推送失败: {result.get('msg')}{Colors.ENDC}")
            return False
    except Exception as e:
        print(f"{Colors.FAIL}❌ 微信推送异常: {e}{Colors.ENDC}")
        return False

def analyze_market_breadth(pivot_df, raw_data):
    """分析市场宽度数据并生成报告"""
    if pivot_df is None or pivot_df.empty:
        print(f"{Colors.FAIL}❌ 没有可分析的数据{Colors.ENDC}")
        return
        
    date_columns = pivot_df.columns
    latest_date = date_columns[-1]
    
    print(f"\n{Colors.HEADER}=========================================")
    print(f"{Colors.HEADER}{Colors.BOLD}📊 市场宽度行业趋势分析报告{Colors.ENDC}")
    print(f"{Colors.OKBLUE}分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"数据时间范围: {date_columns[0]} 至 {latest_date}")
    print(f"包含行业数量: {len(pivot_df)}{Colors.ENDC}")
    print(f"{Colors.HEADER}=========================================")
    
    # 用于推送的文本内容
    push_content = f"# 市场宽度行业趋势分析报告\n\n"
    push_content += f"分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    push_content += f"数据时间范围: {date_columns[0]} 至 {latest_date}\n"
    push_content += f"包含行业数量: {len(pivot_df)}\n\n"
    
    # 计算指标
    latest_values = pivot_df[latest_date]
    
    # 计算5日和10日变化率
    five_day_change = {}  # 行业: 5日变化率
    ten_day_change = {}   # 行业: 10日变化率
    
    for industry in pivot_df.index:
        if len(date_columns) >= 5:
            five_day_change[industry] = ((pivot_df.loc[industry, latest_date] - pivot_df.loc[industry, date_columns[-5]]) / 
                                       pivot_df.loc[industry, date_columns[-5]] * 100) if pivot_df.loc[industry, date_columns[-5]] != 0 else 0
        else:
            five_day_change[industry] = 0
            
        if len(date_columns) >= 10:
            ten_day_change[industry] = ((pivot_df.loc[industry, latest_date] - pivot_df.loc[industry, date_columns[-10]]) / 
                                      pivot_df.loc[industry, date_columns[-10]] * 100) if pivot_df.loc[industry, date_columns[-10]] != 0 else 0
        else:
            ten_day_change[industry] = 0
    
    # 分类行业
    strong_trend = []  # 强趋势行业
    rising_trend = []  # 上升趋势行业
    falling_trend = []  # 下降趋势行业
    potential_value = []  # 低估值潜力行业
    
    for industry in pivot_df.index:
        latest = latest_values[industry]
        five_day = five_day_change[industry]
        ten_day = ten_day_change[industry]
        
        if latest > 70 and ten_day > 10:
            strong_trend.append((industry, latest, ten_day))
        if five_day > 10:
            rising_trend.append((industry, five_day))
        if five_day < -10:
            falling_trend.append((industry, five_day))
        if latest < 30 and ten_day > 0:
            potential_value.append((industry, latest, ten_day))
    
    # 按变化率排序
    strong_trend.sort(key=lambda x: x[2], reverse=True)
    rising_trend.sort(key=lambda x: x[1], reverse=True)
    falling_trend.sort(key=lambda x: x[1])
    potential_value.sort(key=lambda x: x[2], reverse=True)
    
    # 行业趋势分析
    print(f"\n{Colors.BOLD}1. 行业趋势分析{Colors.ENDC}")
    print(f"{Colors.HEADER}-" * 40)
    push_content += "1. 行业趋势分析\n"
    push_content += "-" * 40 + "\n"
    
    if strong_trend:
        print(f"\n{Colors.STAR} 强趋势行业 ({len(strong_trend)}个):")
        push_content += f"<b>⭐ 强趋势行业 ({len(strong_trend)}个):</b>\n"
        for industry, latest, ten_day in strong_trend[:10]:  # 显示前10个
            trend_color = Colors.FAIL if ten_day > 0 else Colors.OKGREEN
            trend_arrow = Colors.UP_ARROW if ten_day > 0 else Colors.DOWN_ARROW
            print(f"  {trend_arrow}  {industry}: 最新宽度 {latest:.2f}%, 10日变化 {trend_color}{ten_day:.2f}%{Colors.ENDC}")
            # 使用HTML font标签添加颜色
            color = "red" if ten_day > 0 else "green"
            push_content += f"  {trend_arrow}  {industry}: 最新宽度 {latest:.2f}%, 10日变化 <font color='{color}'>{ten_day:.2f}%</font>\n"
    else:
        print(f"\n{Colors.WARNING_TEXT} 强趋势行业: 无{Colors.ENDC}")
        push_content += "  强趋势行业: 无\n"
        
    if rising_trend:
        print(f"\n{Colors.UP_ARROW} 上升趋势行业 ({len(rising_trend)}个):")
        push_content += f"\n<b>📈 上升趋势行业 ({len(rising_trend)}个):</b>\n"
        for industry, five_day in rising_trend[:10]:  # 显示前10个
            print(f"  {Colors.UP_ARROW}  {industry}: 5日变化 {Colors.FAIL}{five_day:.2f}%{Colors.ENDC}")
            push_content += f"  📈  {industry}: 5日变化 <font color='red'>{five_day:.2f}%</font>\n"
    else:
        print(f"\n{Colors.WARNING_TEXT} 上升趋势行业: 无{Colors.ENDC}")
        push_content += "\n  上升趋势行业: 无\n"
        
    if falling_trend:
        print(f"\n{Colors.DOWN_ARROW} 下降趋势行业 ({len(falling_trend)}个):")
        push_content += f"\n<b>📉 下降趋势行业 ({len(falling_trend)}个):</b>\n"
        for industry, five_day in falling_trend[:10]:  # 显示前10个
            print(f"  {Colors.DOWN_ARROW}  {industry}: 5日变化 {Colors.OKGREEN}{five_day:.2f}%{Colors.ENDC}")
            push_content += f"  📉  {industry}: 5日变化 <font color='green'>{five_day:.2f}%</font>\n"
    else:
        print(f"\n{Colors.WARNING_TEXT} 下降趋势行业: 无{Colors.ENDC}")
        push_content += "\n  下降趋势行业: 无\n"
        
    if potential_value:
        print(f"\n{Colors.STAR} 低估值潜力行业 ({len(potential_value)}个):")
        push_content += f"\n<b>⭐ 低估值潜力行业 ({len(potential_value)}个):</b>\n"
        for industry, latest, ten_day in potential_value[:10]:  # 显示前10个
            print(f"  {Colors.STAR}  {industry}: 最新宽度 {Colors.WARNING_TEXT}{latest:.2f}%, 10日变化 {Colors.FAIL}{ten_day:.2f}%{Colors.ENDC}")
            push_content += f"  ⭐  {industry}: 最新宽度 <font color='orange'>{latest:.2f}%</font>, 10日变化 <font color='red'>{ten_day:.2f}%</font>\n"
    else:
        print(f"\n{Colors.WARNING_TEXT} 低估值潜力行业: 无{Colors.ENDC}")
        push_content += "\n  低估值潜力行业: 无\n"
    
    # 投资建议
    print(f"\n{Colors.BOLD}2. 投资建议{Colors.ENDC}")
    print(f"{Colors.HEADER}-" * 40)
    push_content += "\n2. 投资建议\n"
    push_content += "-" * 40 + ""
    
    # 短期策略
    print(f"\n{Colors.UP_ARROW} 短期策略 (1-5天):")
    push_content += f"\n<b>📈 短期策略 (1-5天):</b>\n"
    if rising_trend:
        top_rising = [industry for industry, _ in rising_trend[:3]]
        print(f"  {Colors.INFO} - 关注上升趋势明显的行业: {Colors.BOLD}{', '.join(top_rising)}{Colors.ENDC}")
        push_content += f"  ℹ️ - 关注上升趋势明显的行业: {', '.join(top_rising)}\n"
        
        # ETF推荐
        print(f"  {Colors.INFO} - ETF推荐:")
        push_content += f"  ℹ️ - ETF推荐:\n"
        for industry in top_rising:
            if industry in industry_etf_map:
                etf_code, etf_name = industry_etf_map[industry]
                print(f"    {Colors.STAR}  {industry}: {Colors.OKBLUE}{etf_name} ({etf_code}){Colors.ENDC}")
                push_content += f"    ⭐  {industry}: {etf_name} ({etf_code})\n"
            else:
                print(f"    {Colors.STAR}  {industry}: {Colors.WARNING_TEXT}暂无合适的ETF推荐{Colors.ENDC}")
                push_content += f"    ⭐  {industry}: 暂无合适的ETF推荐\n"
    else:
        print(f"  {Colors.WARNING_TEXT} - 目前没有明显的短期上升趋势行业{Colors.ENDC}")
        push_content += f"  ⚠️ - 目前没有明显的短期上升趋势行业\n"
    
    # 中期策略
    print(f"\n{Colors.UP_ARROW} 中期策略 (5-20天):")
    push_content += f"\n<b>📈 中期策略 (5-20天):</b>\n"
    if strong_trend:
        top_strong = [industry for industry, _, _ in strong_trend[:3]]
        print(f"  {Colors.INFO} - 持有强趋势行业: {Colors.BOLD}{', '.join(top_strong)}{Colors.ENDC}")
        push_content += f"  ℹ️ - 持有强趋势行业: {', '.join(top_strong)}\n"
        
        # ETF推荐
        print(f"  {Colors.INFO} - ETF推荐:")
        push_content += f"  ℹ️ - ETF推荐:\n"
        for industry in top_strong:
            if industry in industry_etf_map:
                etf_code, etf_name = industry_etf_map[industry]
                print(f"    {Colors.STAR}  {industry}: {Colors.OKBLUE}{etf_name} ({etf_code}){Colors.ENDC}")
                push_content += f"    ⭐  {industry}: {etf_name} ({etf_code})\n"
            else:
                print(f"    {Colors.STAR}  {industry}: {Colors.WARNING_TEXT}暂无合适的ETF推荐{Colors.ENDC}")
                push_content += f"    ⭐  {industry}: 暂无合适的ETF推荐\n"
    else:
        print(f"  {Colors.WARNING_TEXT} - 目前没有明显的中期强趋势行业{Colors.ENDC}")
        push_content += f"  ⚠️ - 目前没有明显的中期强趋势行业\n"
    
    # 低估值策略
    if potential_value:
        top_potential = [industry for industry, _, _ in potential_value[:3]]
        print(f"\n{Colors.STAR} 关注低估值潜力行业: {Colors.BOLD}{', '.join(top_potential)}{Colors.ENDC}")
        push_content += f"\n⭐ 关注低估值潜力行业: {', '.join(top_potential)}\n"
        
        # ETF推荐
        print(f"  {Colors.INFO} - ETF推荐:")
        push_content += f"  ℹ️ - ETF推荐:\n"
        for industry in top_potential:
            if industry in industry_etf_map:
                etf_code, etf_name = industry_etf_map[industry]
                print(f"    {Colors.STAR}  {industry}: {Colors.OKBLUE}{etf_name} ({etf_code}){Colors.ENDC}")
                push_content += f"    ⭐  {industry}: {etf_name} ({etf_code})\n"
            else:
                print(f"    {Colors.STAR}  {industry}: {Colors.WARNING_TEXT}暂无合适的ETF推荐{Colors.ENDC}")
                push_content += f"    ⭐  {industry}: 暂无合适的ETF推荐\n"
    
    # 风险提示
    print(f"\n{Colors.WARNING_TEXT}3. 风险提示{Colors.ENDC}")
    print(f"  {Colors.WARNING_TEXT} - 市场宽度指标仅反映短期趋势，需结合基本面分析{Colors.ENDC}")
    print(f"  {Colors.WARNING_TEXT} - 避免追高下降趋势明显的行业{Colors.ENDC}")
    print(f"  {Colors.WARNING_TEXT} - 建议分散投资，控制单一行业仓位{Colors.ENDC}")
    push_content += "\n<b>3. 风险提示</b>\n"
    push_content += "  - 市场宽度指标仅反映短期趋势，需结合基本面分析\n"
    push_content += "  - 避免追高下降趋势明显的行业\n"
    push_content += "  - 建议分散投资，控制单一行业仓位\n"
    
    print(f"\n{Colors.HEADER}=========================================")
    print(f"{Colors.OKGREEN}✅ 分析完成！{Colors.ENDC}")
    push_content += "\n=========================================\n"
    push_content += "✅ 分析完成！\n"
    
    # 推送报告
    print(f"\n{Colors.INFO} 正在推送分析报告...{Colors.ENDC}")
    send_wxpush_message("市场宽度行业趋势分析报告", push_content)

def main():
    """主函数"""
    print(f"{Colors.OKGREEN}{Colors.BOLD}🚀 市场宽度快速报告生成工具{Colors.ENDC}")
    print(f"{Colors.OKBLUE}正在获取最新的行业市场宽度数据...{Colors.ENDC}")
    
    # 获取和解析数据
    pivot_df, raw_data = get_and_parse_data()
    if pivot_df is None:
        print(f"{Colors.FAIL}❌ 报告生成失败{Colors.ENDC}")
        return
        
    # 分析数据并生成报告
    analyze_market_breadth(pivot_df, raw_data)

if __name__ == "__main__":
    main()