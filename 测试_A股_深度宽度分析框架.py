import requests
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import time
import os
import json

# ================= 配置区域 =================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_beijing_time():
    return datetime.now(BEIJING_TZ)

# ================= 数据获取与处理 =================
def fetch_data(retries=3, delay=2):
    url = 'https://sckd.dapanyuntu.com/api/api/industry_ma20_analysis_page?page=0'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
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
    # 保持原有的板块映射
    return {
        '科技成长': ['半导体', '电子元件', '光学光电子', '电子化学品', '计算机设备', '软件开发', '互联网服务', '通信设备', '通信服务', '消费电子'],
        '可选消费': ['酿酒行业', '家电行业', '珠宝首饰', '汽车整车', '汽车零部件', '汽车服务', '旅游酒店', '商业百货', '纺织服装', '文化传媒', '教育', '装修建材', '装修装饰', '家用轻工'],
        '必选消费医药': ['医药商业', '中药', '化学制药', '生物制品', '医疗器械', '医疗服务', '美容护理', '农牧饲渔', '食品饮料'],
        '能源资源': ['煤炭行业', '石油行业', '采掘行业', '钢铁行业', '有色金属', '贵金属', '小金属', '能源金属', '化学原料', '化学制品', '化纤行业', '非金属材料'],
        '高端制造': ['光伏设备', '风电设备', '电池', '电机', '电源设备', '电网设备', '专用设备', '通用设备', '航天航空', '交运设备', '船舶制造', '仪器仪表'],
        '传统制造': ['水泥建材', '塑料制品', '橡胶制品', '玻璃玻纤', '造纸印刷', '包装材料', '化肥行业', '农药兽药'],
        '大金融': ['银行', '证券', '保险', '多元金融'],
        '基建物流': ['铁路公路', '航运港口', '物流行业', '航空机场', '工程建设', '工程咨询服务', '工程机械', '专业服务'],
        '公用事业': ['公用事业', '电力行业', '燃气', '环保行业'],
        '房地产链': ['房地产开发', '房地产服务'],
        '贸易综合': ['贸易行业', '综合行业', '游戏']
    }

# ================= 深度数据清洗与衍生指标计算 =================
def compute_advanced_metrics(pivot, dates):
    """
    计算用于深度分析的衍生指标：
    1. 动量 (Momentum): 1日、3日、5日变化率
    2. 趋势反转 (Reversal): 底部拐点、顶部钝化
    3. 板块共振 (Sector Cohesion): 大板块内各细分行业的协同度
    """
    df = pivot.copy()
    
    # 基础动量指标
    df['1日变化'] = df[dates[-1]] - df[dates[-2]]
    df['3日变化'] = df[dates[-1]] - df[dates[-4]] if len(dates) >= 4 else df['1日变化']
    df['5日变化'] = df[dates[-1]] - df[dates[-6]] if len(dates) >= 6 else df['3日变化']
    
    # 均线系统 (平滑趋势)
    df['3日均值'] = df[dates[-3:]].mean(axis=1) if len(dates) >= 3 else df[dates[-1]]
    
    # 当前状态打分
    df['当前值'] = df[dates[-1]]
    
    # 定义状态标签
    def categorize_state(val, d1, d3):
        if val >= 80:
            return "极度过热" if d1 > 0 else "高位钝化/派发"
        elif val <= 20:
            return "极度冰点" if d1 < 0 else "底部反弹启动"
        elif 20 < val < 50:
            return "弱势修复" if d3 > 0 else "阴跌探底"
        else: # 50-80
            return "强势主升" if d3 > 0 else "高位震荡"
            
    df['状态标签'] = df.apply(lambda row: categorize_state(row['当前值'], row['1日变化'], row['3日变化']), axis=1)
    
    return df

def prepare_deep_context(pivot, dates):
    latest_date = dates[-1]
    advanced_df = compute_advanced_metrics(pivot, dates)
    sector_map = get_sector_map()
    
    # 1. 宏观市场数据
    current_vals = pivot[latest_date]
    avg_breadth = current_vals.mean()
    median_breadth = current_vals.median()
    
    # 计算市场动能 (全市场上涨的行业比例)
    market_momentum_1d = (advanced_df['1日变化'] > 0).mean() * 100
    
    # 2. 板块深度聚合分析 (Sector Level Analysis)
    sector_stats = []
    for sector_name, industries in sector_map.items():
        # 筛选出实际存在于数据中的行业
        valid_inds = [ind for ind in industries if ind in advanced_df.index]
        if not valid_inds: continue
        
        sec_data = advanced_df.loc[valid_inds]
        avg_val = sec_data['当前值'].mean()
        avg_3d_chg = sec_data['3日变化'].mean()
        
        # 计算内部共振度 (标准差越小，说明板块内部走势越一致)
        cohesion = sec_data['当前值'].std() 
        
        # 寻找板块内领头羊和拖后腿的
        leader = sec_data['当前值'].idxmax()
        laggard = sec_data['当前值'].idxmin()
        
        sector_stats.append({
            '板块': sector_name,
            '平均宽度': avg_val,
            '3日动量': avg_3d_chg,
            '内部离散度': cohesion,
            '领头行业': f"{leader}({sec_data.loc[leader, '当前值']:.1f})",
            '状态分布': sec_data['状态标签'].value_counts().to_dict()
        })
    
    sector_df = pd.DataFrame(sector_stats).sort_values(by='平均宽度', ascending=False)
    
    # 3. 极端异动筛选
    # 底部突发暴涨 (宽度<30，但3日变化>15)
    bottom_reversal = advanced_df[(advanced_df['当前值'] < 40) & (advanced_df['3日变化'] > 10)].index.tolist()
    # 高位大逃亡 (宽度>70，但3日变化<-15)
    top_crash = advanced_df[(advanced_df['当前值'] > 60) & (advanced_df['3日变化'] < -10)].index.tolist()
    
    # 4. 构建发送给 AI 的结构化上下文
    context = f"""
[核心数据基准]
数据日期: {latest_date}

[1. 宏观大盘环境 (Macro Environment)]
- 全市场平均宽度: {avg_breadth:.1f}% (反映整体赚钱效应)
- 宽度中位数: {median_breadth:.1f}% (反映普涨还是结构性行情)
- 市场短期动能(上涨行业占比): {market_momentum_1d:.1f}%

[2. 核心大板块聚合数据 (Sector Aggregation)]
(按平均宽度降序排列。离散度越低，代表板块内部协同度越高，主线特征越明显)
{sector_df.to_string(index=False)}

[3. 细分行业异动雷达 (Anomaly Detection)]
- 底部强力反转信号 (低位+短期大幅拉升): {', '.join(bottom_reversal) if bottom_reversal else '无明显信号'}
- 高位派发/破位信号 (高位+短期大幅杀跌): {', '.join(top_crash) if top_crash else '无明显信号'}

[4. 细分行业全景数据 (含状态标签)]
{advanced_df[['当前值', '1日变化', '3日变化', '状态标签']].sort_values(by='当前值', ascending=False).to_string()}
"""
    return context

# ================= 深度 AI 分析 Prompt 框架 =================
def test_ai_analysis(context):
    if not DEEPSEEK_API_KEY:
        return "未配置 DEEPSEEK_API_KEY，无法调用接口。请查看终端打印的 Context 数据。"

    # ！！！这是全新的深度分析 Prompt 框架 ！！！
    system_prompt = """你是一位顶尖的A股量化策略总监。你擅长通过『市场宽度(Market Breadth)』数据的横向比较、纵向动量以及板块共振度，来透视市场底层的资金博弈逻辑。

请基于提供的数据，输出一份极具深度的市场策略报告。

### 🧠 深度分析框架指南 (你的思考过程)：

**第一维：辨别指数面具下的真实生态 (宏观定调)**
- 比较平均数与中位数：差距大说明市场极其割裂（权重拉升掩护出货，或小票失血）。
- 结合短期动能（上涨行业占比）：判断今天是普反、普跌，还是存量资金的残酷互道互砍。
- 给出市场周期的定义：处于冰点期、混沌期、主升期、还是退潮期？

**第二维：透视板块共振与资金主线 (中观推演)**
- 重点关注【核心大板块聚合数据】中的『内部离散度』：
  - **高宽度 + 低离散度**：这是最强的主线，资金高度共识（如全板块高潮）。
  - **高宽度 + 高离散度**：板块内部出现分化，前排在高位震荡，后排掉队，这是主线见顶或切换的早期信号。
  - **低宽度 + 底部强力反转**：这是新周期/新主线正在孕育的信号。

**第三维：捕捉异动背离与交易节点 (微观异动)**
- 关注【异动雷达】和状态标签为『高位钝化/派发』、『底部反弹启动』的细分行业。
- 解释这些异动背后的可能逻辑（例如：是否是高低切？是否是避险资金涌入公用事业？）

### 📝 输出格式要求：

必须采用以下四个层级的 Markdown 结构，文字要锐利、一针见血，杜绝正确的废话。必须引用具体的数据来佐证你的观点。

# 深度量化宽度复盘 (Depth Breadth Analysis)

## 一、 市场真实生态度量 (Market Ecology)
*(直接给出对当前大盘所处周期的定性判断。解析平均数/中位数/动能背后的资金真相。)*

## 二、 主线生命周期推演 (Main Theme Lifecycle)
*(挑选1-2个最核心的板块，分析其内部共振度（离散度），判断它是处于爆发期、分歧期还是衰退期。点名领头羊。)*

## 三、 异动雷达与暗流涌动 (Anomalies & Undercurrents)
*(解读底部反转信号和高位派发信号，指出资金正在往哪个方向暗中切换。)*

## 四、 极简操作策略 (Actionable Strategy)
- **总体仓位建议**：(例如：3成防御 / 8成进攻)
- **主攻方向 (进攻矛)**：(具体到细分行业，说明是做突破还是做低吸)
- **防御/规避 (风险盾)**：(必须点名需要止盈或回避的板块)
"""

    user_prompt = f"这是基于市场宽度深度清洗后的数据矩阵，请进行高阶策略推演：\n\n{context}"

    payload = {
        "model": "deepseek-reasoner", # 建议深度分析使用 R1 (reasoner) 模型
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    try:
        print("\n正在调用 DeepSeek-R1 模型进行深度思考分析 (可能需要 1-2 分钟)...")
        response = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=120
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"AI 请求失败: {response.text}"
    except Exception as e:
        return f"AI 请求异常: {e}"

def main():
    print(">>> 启动深度分析测试框架 <<<")
    data = fetch_data()
    if not data:
        print("数据获取失败")
        return
        
    pivot, dates = process_data(data)
    context = prepare_deep_context(pivot, dates)
    
    print("\n" + "="*50)
    print("【深度清洗后的 Context 数据 (将喂给 AI)】")
    print("="*50)
    print(context)
    print("="*50 + "\n")
    
    report = test_ai_analysis(context)
    
    print("\n" + "="*50)
    print("【AI 深度分析报告输出】")
    print("="*50)
    print(report)

if __name__ == "__main__":
    main()
