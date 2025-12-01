
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import requests
import os

# ================= 配置区域 =================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-063857d175bd48038684520e7b6ec934")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# 推送配置 (WxPusher)
WXPUSHER_APP_TOKEN = os.getenv("WXPUSHER_APP_TOKEN", "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc")
WXPUSHER_TOPIC_IDS = [42624]
WXPUSHER_URL = "https://wxpusher.zjiecode.com/api/send/message"

# 时区配置
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_beijing_time():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ)

# ================= 数据获取与处理 =================

def fetch_futures_data(symbol, days=180):
    """
    从 akshare 获取期货数据
    symbol: 'y0' (豆油主力) 或 'p0' (棕榈油主力)
    days: 获取天数，默认180天（约半年）
    """
    try:
        print(f"正在获取 {symbol} 的历史数据...")
        
        # 使用 akshare 获取期货主力连续数据
        # 大商所期货代码格式
        df = ak.futures_main_sina(symbol=symbol.upper())
        
        if df is None or df.empty:
            print(f"[Error] 未获取到 {symbol} 的数据")
            return None
        
        # 重命名列（akshare 返回的是中文列名）
        column_mapping = {
            '日期': 'date',
            '开盘价': 'open',
            '最高价': 'high',
            '最低价': 'low',
            '收盘价': 'close',
            '成交量': 'volume',
            '持仓量': 'hold',
            '动态结算价': 'settle'
        }
        df = df.rename(columns=column_mapping)
        
        # 确保日期列为 datetime 类型
        df['date'] = pd.to_datetime(df['date'])
        
        # 按日期排序
        df = df.sort_values('date')
        
        # 只保留最近 N 天的数据
        cutoff_date = (get_beijing_time() - timedelta(days=days)).replace(tzinfo=None)
        df = df[df['date'] >= cutoff_date]
        
        print(f"✅ 成功获取 {symbol} 数据，共 {len(df)} 条记录")
        print(f"   日期范围: {df['date'].min().strftime('%Y-%m-%d')} 至 {df['date'].max().strftime('%Y-%m-%d')}")
        
        return df
        
    except Exception as e:
        print(f"[Error] 获取 {symbol} 数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def calculate_technical_indicators(df):
    """
    计算技术指标
    """
    df = df.copy()
    
    # 移动平均线
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA10'] = df['close'].rolling(window=10).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['MA60'] = df['close'].rolling(window=60).mean()
    
    # 价格相对于均线的位置
    df['above_MA5'] = (df['close'] > df['MA5']).astype(int)
    df['above_MA10'] = (df['close'] > df['MA10']).astype(int)
    df['above_MA20'] = (df['close'] > df['MA20']).astype(int)
    df['above_MA60'] = (df['close'] > df['MA60']).astype(int)
    
    # 涨跌幅
    df['pct_change'] = df['close'].pct_change() * 100
    
    # 波动率 (20日标准差)
    df['volatility'] = df['pct_change'].rolling(window=20).std()
    
    # ATR (平均真实波幅)
    df['high_low'] = df['high'] - df['low']
    df['high_close'] = abs(df['high'] - df['close'].shift(1))
    df['low_close'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
    df['ATR'] = df['tr'].rolling(window=14).mean()
    
    # 成交量变化
    df['volume_ma5'] = df['volume'].rolling(window=5).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma5']
    
    return df

def prepare_context_for_ai(y0_df, p0_df):
    """
    为 AI 准备分析上下文
    """
    # 获取最新数据
    y0_latest = y0_df.iloc[-1]
    p0_latest = p0_df.iloc[-1]
    
    # 获取近期数据（最近60天）
    y0_recent = y0_df.tail(60)
    p0_recent = p0_df.tail(60)
    
    # 构建豆油完整数据CSV
    y0_data_lines = ["日期,开盘价,最高价,最低价,收盘价,成交量,持仓量,涨跌幅(%)"]
    for _, row in y0_recent.iterrows():
        date_str = row['date'].strftime('%Y-%m-%d')
        pct = row['pct_change'] if pd.notnull(row['pct_change']) else 0
        y0_data_lines.append(
            f"{date_str},{row['open']:.0f},{row['high']:.0f},{row['low']:.0f},"
            f"{row['close']:.0f},{row['volume']:.0f},{row['hold']:.0f},{pct:+.2f}"
        )
    y0_data_str = "\n".join(y0_data_lines)
    
    # 构建棕榈油完整数据CSV
    p0_data_lines = ["日期,开盘价,最高价,最低价,收盘价,成交量,持仓量,涨跌幅(%)"]
    for _, row in p0_recent.iterrows():
        date_str = row['date'].strftime('%Y-%m-%d')
        pct = row['pct_change'] if pd.notnull(row['pct_change']) else 0
        p0_data_lines.append(
            f"{date_str},{row['open']:.0f},{row['high']:.0f},{row['low']:.0f},"
            f"{row['close']:.0f},{row['volume']:.0f},{row['hold']:.0f},{pct:+.2f}"
        )
    p0_data_str = "\n".join(p0_data_lines)
    
    # 计算价差
    price_spread = y0_latest['close'] - p0_latest['close']
    spread_history = y0_recent['close'] - p0_recent['close']
    spread_mean = spread_history.mean()
    spread_std = spread_history.std()
    
    # 构建上下文
    context = f"""
    [分析基准]
    数据截止日期: {y0_latest['date'].strftime('%Y-%m-%d')}
    分析周期: 近60个交易日
    
    [豆油(y0)当前状态]
    - 最新价格: {y0_latest['close']:.0f} 元/吨
    - 日涨跌幅: {y0_latest['pct_change']:+.2f}%
    - MA5: {y0_latest['MA5']:.0f}, MA20: {y0_latest['MA20']:.0f}, MA60: {y0_latest['MA60']:.0f}
    - 价格位置: {'MA5之上' if y0_latest['above_MA5'] else 'MA5之下'}, {'MA20之上' if y0_latest['above_MA20'] else 'MA20之下'}
    - 20日波动率: {y0_latest['volatility']:.2f}%
    - 成交量比: {y0_latest['volume_ratio']:.2f}倍
    - 持仓量: {y0_latest['hold']:.0f}
    
    [棕榈油(p0)当前状态]
    - 最新价格: {p0_latest['close']:.0f} 元/吨
    - 日涨跌幅: {p0_latest['pct_change']:+.2f}%
    - MA5: {p0_latest['MA5']:.0f}, MA20: {p0_latest['MA20']:.0f}, MA60: {p0_latest['MA60']:.0f}
    - 价格位置: {'MA5之上' if p0_latest['above_MA5'] else 'MA5之下'}, {'MA20之上' if p0_latest['above_MA20'] else 'MA20之下'}
    - 20日波动率: {p0_latest['volatility']:.2f}%
    - 成交量比: {p0_latest['volume_ratio']:.2f}倍
    - 持仓量: {p0_latest['hold']:.0f}
    
    [价差分析]
    - 当前价差(豆油-棕榈油): {price_spread:+.0f} 元/吨
    - 60日均值: {spread_mean:+.0f} 元/吨
    - 60日标准差: {spread_std:.0f} 元/吨
    - 价差偏离度: {(price_spread - spread_mean) / spread_std:.2f} 个标准差
    
    [豆油(y0)近60日完整数据]
    {y0_data_str}
    
    [棕榈油(p0)近60日完整数据]
    {p0_data_str}
    """
    
    return context

# ================= AI 分析模块 =================

def call_deepseek_analysis(context):
    """调用 DeepSeek API 进行分析"""
    if not DEEPSEEK_API_KEY or "sk-" not in DEEPSEEK_API_KEY:
        print("[Warning] 未配置 DEEPSEEK_API_KEY，跳过 AI 分析。")
        return "未配置 API Key，无法生成 AI 报告。"

    system_prompt = """你是一位资深的期货分析师，专注于油脂油料品种分析。请基于提供的豆油(y0)和棕榈油(p0)的历史数据，撰写一份深度分析报告。

    **分析逻辑与要求：**

    1.  **趋势判断**:
        *   分析两个品种各自的趋势方向（上涨/下跌/震荡）。
        *   结合均线系统判断当前所处的技术位置（多头排列/空头排列）。
        *   识别关键支撑位和压力位。
        
    2.  **成交量分析（重要）**:
        *   **成交量是市场活跃度的直接体现**，反映资金的参与程度。
        *   分析成交量的变化趋势：放量还是缩量？
        *   **量价配合关系**：
            - 价涨量增 = 上涨动能充足，趋势健康
            - 价涨量缩 = 上涨乏力，可能是诱多
            - 价跌量增 = 恐慌性抛售，加速下跌
            - 价跌量缩 = 抛压减轻，可能止跌
        *   对比成交量比（当前成交量/5日均量），判断是否出现异常放量或缩量。
        
    3.  **持仓量分析（重要）**:
        *   **持仓量是期货市场的核心指标**，反映市场参与度和资金流向。
        *   分析持仓量的变化趋势：增仓还是减仓？
        *   **量价仓三者配合**：
            - 价涨+量增+仓增 = 多头强势建仓，趋势最强
            - 价涨+量增+仓减 = 空头止损离场，反弹性质
            - 价跌+量增+仓增 = 空头强势建仓，趋势最弱
            - 价跌+量增+仓减 = 多头止损离场，杀跌末期
        
    4.  **价差分析（核心）**:
        *   豆油和棕榈油存在替代关系，价差是重要的交易信号。
        *   分析当前价差是否偏离历史均值，是否存在套利机会。
        *   价差扩大/收窄的驱动因素是什么？
        
    5.  **交易建议**:
        *   给出具体的操作方向（做多/做空/观望）。
        *   如果存在套利机会，说明具体的套利策略（如：买豆油卖棕榈油）。
        *   明确止损位和目标位。

    **输出格式要求：**
    *   使用 Markdown 格式。
    *   **必须引用数据**: 在分析时必须引用具体的价格、成交量、持仓量等数值。
    *   语气专业、客观、有洞察力。
    *   字数控制在 600-800 字之间。

    **报告结构：**
    # 油脂期货深度分析
    ## 📊 品种走势分析
    ## 📈 量价仓配合解读
    ## 🔄 价差套利机会
    ## 💡 交易策略建议
    """

    user_prompt = f"这是最新的豆油和棕榈油期货数据，请开始分析：\n{context}"

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 2000
    }

    try:
        response = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=60
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"AI 请求失败: {response.text}"
    except Exception as e:
        return f"AI 请求异常: {e}"

# ================= 消息推送模块 =================

def send_push(title, content):
    """使用 WxPusher 推送消息"""
    print("\n" + "="*20 + f" PUSH: {title} " + "="*20)
    print("正在发送 WxPusher 推送...")
    print("="*50 + "\n")
    
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
            print(f"[Info] WxPusher 推送成功: {resp_json.get('msg')}")
        else:
            print(f"[Error] WxPusher 推送失败: {resp_json}")
    except Exception as e:
        print(f"[Error] WxPusher 请求异常: {e}")

# ================= 主程序 =================

def main():
    beijing_time = get_beijing_time()
    print(f"[{beijing_time.strftime('%H:%M:%S')}] 开始执行油脂期货分析任务...")
    
    # 1. 获取数据
    y0_df = fetch_futures_data('y0', days=180)
    p0_df = fetch_futures_data('p0', days=180)
    
    if y0_df is None or p0_df is None:
        print("[Error] 数据获取失败，任务终止。")
        return
    
    # 2. 计算技术指标
    print("正在计算技术指标...")
    y0_df = calculate_technical_indicators(y0_df)
    p0_df = calculate_technical_indicators(p0_df)
    
    # 3. 生成分析上下文
    context = prepare_context_for_ai(y0_df, p0_df)
    print("\n--- 生成的数据上下文 ---")
    print(context)
    
    # 4. 调用 AI 分析
    print(f"\n[{get_beijing_time().strftime('%H:%M:%S')}] 正在请求 DeepSeek 进行分析...")
    ai_report = call_deepseek_analysis(context)
    
    # 5. 组合最终报告
    beijing_time = get_beijing_time()
    report_header = f"""
> **推送时间**: {beijing_time.strftime('%Y-%m-%d %H:%M')} (北京时间) | 每个交易日收盘后推送
> 
> **品种说明**: 
> - **豆油(y0)**: 大商所豆油主力连续合约
> - **棕榈油(p0)**: 大商所棕榈油主力连续合约
> - 两者存在替代关系，价差分析是重要的交易参考

---
"""
    
    final_report = report_header + ai_report + f"""

---
*数据来源: AkShare | AI 分析: DeepSeek*
    """
    
    # 6. 保存与推送
    filename = f"futures_oil_report_{beijing_time.strftime('%Y%m%d')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(final_report)
    print(f"[Info] 报告已保存至 {filename}")
    
    # 推送
    push_title = f"油脂期货分析日报 ({beijing_time.strftime('%Y-%m-%d')})"
    send_push(push_title, final_report)

if __name__ == "__main__":
    main()
