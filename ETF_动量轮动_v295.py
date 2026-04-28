import os
import json
import pandas as pd
import numpy as np
import requests
import akshare as ak
import tushare as ts
from datetime import datetime, timedelta

# ==================== Tushare 配置 ====================
ts.set_token('3664fe220cb675ae1661e7ad96c51e2592a0ef72c93d29da3d65b692')
pro = ts.pro_api()

# ==================== 配置 ====================
# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v295_portfolio_ak.json")

# 微信推送配置 (WxPusher)
WXPUSHER_APP_TOKEN = "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc"
WXPUSHER_TOPIC_IDS = [43351]
WXPUSHER_URL = "https://wxpusher.zjiecode.com/api/send/message"

# 品种池 - v28(25只) + v29新增(3只) = 28只
POOL = {
    '宽基': ['510050.SH', '510300.SH', '510500.SH', '588000.SH', '159915.SZ'],
    '行业': ['512010.SH', '512660.SH', '512170.SH', '512200.SH', '512400.SH'],
    '主题': ['510880.SH', '510180.SH', '510330.SH', '159816.SZ', '515880.SH', '159770.SZ'],
    '跨境': ['513090.SH', '513130.SH', '513180.SH', '513330.SH', '159920.SZ', '159659.SZ'],
    '商品/债券': ['518880.SH', '159985.SZ', '162719.SZ', '511010.SH', '511260.SH'],
}

# 名字映射，方便展示
ETF_NAMES = {
    '510050.SH': '50ETF', '510300.SH': '300ETF', '510500.SH': '500ETF', '588000.SH': '科创50', '159915.SZ': '创业板',
    '512010.SH': '医药ETF', '512660.SH': '军工ETF', '512170.SH': '医疗ETF', '512200.SH': '房地产', '512400.SH': '有色金属',
    '510880.SH': '红利ETF', '510180.SH': '180ETF', '510330.SH': '300ETF华夏', '159816.SZ': '农业ETF', '515880.SH': '通信设备', '159770.SZ': '机器人',
    '513090.SH': '香港证券', '513130.SH': '恒生科技', '513180.SH': '恒生科技指数', '513330.SH': '恒生科技30', '159920.SZ': '恒生ETF', '159659.SZ': '纳指100',
    '518880.SH': '黄金ETF', '159985.SZ': '豆粕ETF', '162719.SZ': '石油基金', '511010.SH': '国债ETF', '511260.SH': '十年国债'
}

ALL_POOLS = [code for category in POOL.values() for code in category]

# 策略参数 (优化版: 中周期动量)
MOMENTUM_WEIGHTS = {10: 0.4, 30: 0.3, 60: 0.3}  # 中周期动量: 10日/30日/60日
TOP_N = 5  # 持有前5只
RSI_OVERBOUGHT_THRESHOLD = 75  # RSI超买阈值
RSI_PENALTY = 0.15  # 超买扣分比例

# ==================== 虚拟持仓管理 ====================
def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取虚拟持仓文件失败: {e}")
    return {"current_holdings": []}

def save_portfolio(portfolio):
    try:
        with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
            json.dump(portfolio, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"保存虚拟持仓文件失败: {e}")

# ==================== AI 分析模块 (DeepSeek) ====================
def call_deepseek_analysis(context):
    if not DEEPSEEK_API_KEY or "sk-" not in DEEPSEEK_API_KEY:
        print("[Warning] 未配置 DEEPSEEK_API_KEY，跳过 AI 分析。")
        return "未配置 API Key，无法生成 AI 解读。"

    system_prompt = """你是一位拥有20年经验的量化策略分析师。请基于提供的ETF二八轮动数据、最新调仓决策、近期涨跌幅，以及各标的过去200个交易日的历史收盘价数据，撰写一段简明扼要的AI策略解读。

    **分析逻辑与要求：**

    1. **当前局势点评**:
       - 结合当前各ETF的收益率表现及当前仓位，点评当前市场哪类资产（沪深300 vs 中证500）表现更强。
       - 分析各ETF近期（1日、3日、5日、10日）涨跌幅，判断其上涨是短期脉冲还是趋势延续。
    
    2. **中长期趋势分析 (基于200日数据)**:
       - 简要评估各核心标的在近200日长周期中的位置（如：处于历史高位震荡、长期均线之上突破、或是长期下跌后的底部反转）。
       - 结合中长期趋势与当前短期动量，判断轮动信号的可靠性。
    
    3. **调仓逻辑分析**:
       - 如果发生调仓，请解释为什么模型做出了这个决策（结合长短期动量衰减与新主线崛起，或跌破20日均线的防守需求）。
       - 如果空仓，说明跌破20日均线的避险逻辑。
       - 如果继续持有，说明持仓标的的动量健康度。
       
    4. **风险提示**:
       - 观察未持仓的ETF是否出现极端下跌或反转迹象。
       - 提醒当前持仓的潜在风险（如高位回调、跌破均线边缘等）。

    **输出格式要求：**
    * 使用 Markdown 格式。
    * 字数控制在 300-400 字左右，语言精炼，直击要害。
    * 语气专业、客观。不要使用模棱两可的废话。
    * 不需要输出大标题，直接输出解读内容。
    """

    user_prompt = f"这是最新的ETF二八轮动数据与决策，请开始解读：\n{context}"

    payload = {
        "model": "deepseek-chat",  # 文本任务使用普通模型即可
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 1000
    }

    try:
        response = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"AI 请求失败: {response.text}"
    except Exception as e:
        return f"AI 请求异常: {e}"

# ==================== 推送功能 ====================
def send_wx_msg(content: str, summary: str = "v29.5 策略调仓推送", contentType: int = 3):
    if not WXPUSHER_APP_TOKEN:
        print("未配置 WXPUSHER_APP_TOKEN")
        return
    try:
        payload = {
            "appToken": WXPUSHER_APP_TOKEN,
            "content": content,
            "summary": summary,
            "contentType": contentType,
            "topicIds": WXPUSHER_TOPIC_IDS
        }
        proxies = {"http": None, "https": None}
        response = requests.post(WXPUSHER_URL, json=payload, timeout=10, proxies=proxies)
        result = response.json()
        if result.get('code') == 1000:
            print(f"微信推送成功: {summary}")
        else:
            print(f"微信推送失败: {result.get('msg')}")
    except Exception as e:
        print(f"微信推送异常: {e}")

def get_etf_data(code, start_date, end_date):
    """
    优先使用 tushare 获取数据，若失败则降级使用 akshare 获取。
    返回标准化后的 DataFrame：包含 '日期', '收盘' 列，按日期升序排列。
    """
    # 尝试使用 tushare (优先)
    try:
        market = "SH" if str(code).startswith('5') else "SZ"
        ts_code = f"{code}.{market}"
        
        # 获取日线行情 (未复权)
        df_ts = pro.fund_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        
        if df_ts is None or df_ts.empty:
            print(f"[{code}] tushare 行情数据为空，尝试使用 akshare 备用数据源...")
        else:
            # 获取复权因子
            df_adj = pro.fund_adj(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df_adj is not None and not df_adj.empty:
                # 合并复权因子并计算前复权
                df_ts = pd.merge(df_ts, df_adj[['trade_date', 'adj_factor']], on='trade_date', how='left')
                df_ts['adj_factor'] = df_ts['adj_factor'].fillna(method='bfill').fillna(method='ffill')
                
                latest_factor = df_ts['adj_factor'].iloc[0]
                df_ts['close'] = df_ts['close'] * (df_ts['adj_factor'] / latest_factor)
                
            df_ts = df_ts.rename(columns={
                'trade_date': '日期',
                'close': '收盘'
            })
            
            df_ts['日期'] = pd.to_datetime(df_ts['日期']).dt.strftime('%Y-%m-%d')
            df_ts = df_ts.sort_values('日期').reset_index(drop=True)
            
            print(f"[{code}] tushare 数据获取并前复权处理成功")
            return df_ts
    except Exception as e:
        print(f"[{code}] tushare 获取失败: {e}，尝试使用 akshare 备用数据源...")

    # 尝试使用 akshare (备用)
    try:
        df = ak.fund_etf_hist_em(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        if df is not None and not df.empty:
            print(f"[{code}] akshare 数据获取成功")
            return df
    except Exception as e:
        print(f"[{code}] akshare 获取也失败: {e}")
        
    return None

# ==================== 市场状态与动量打分 ====================
def get_market_state(csi300_close):
    """判断当前市场状态 (基于最新的沪深300数据)"""
    if len(csi300_close) < 20:
        return 'normal'
    
    current_close = csi300_close.iloc[-1]
    close_5d_ago = csi300_close.iloc[-6] if len(csi300_close) >= 6 else csi300_close.iloc[0]
    weekly_return = (current_close / close_5d_ago - 1)
    
    recent_high = csi300_close.iloc[-20:].max()
    drawdown = (current_close / recent_high - 1) if recent_high > 0 else 0
    
    if drawdown < -0.10:
        return 'bottom'
    elif weekly_return < -0.03:
        return 'bear'
    elif drawdown < -0.05:
        return 'bear'
    else:
        return 'normal'

def fetch_data():
    """获取最新行情数据，优先使用 tushare，失败时使用 akshare 备用"""
    print("正在获取数据...")
    # 获取过去 300 天的数据，以确保扣除节假日后有足够的 200 个交易日数据供AI使用
    start_date = (datetime.now() - timedelta(days=300)).strftime("%Y%m%d")
    end_date = datetime.now().strftime("%Y%m%d")
    
    etf_data_list = []
    
    # 数据缓存，用于后续提取200日数据给AI
    global all_data_cache
    all_data_cache = {}
    
    # 查 ETF 数据
    for code in ALL_POOLS:
        success = False
        try:
            print(f"获取 {code} 数据...")
            # 增加获取天数以确保有足够的200天交易日数据
            df = pro.fund_daily(ts_code=code, start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                # 获取复权因子
                adj_df = pro.fund_adj(ts_code=code, start_date=start_date, end_date=end_date)
                if not adj_df.empty:
                    df = pd.merge(df, adj_df[['ts_code', 'trade_date', 'adj_factor']], on=['ts_code', 'trade_date'], how='left')
                    df['close'] = df['close'] * df['adj_factor']
                
                # 缓存原始复权数据供AI使用
                all_data_cache[code] = df.copy()
                
                df = df[['trade_date', 'close']].copy()
                df['ts_code'] = code
                df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
                etf_data_list.append(df)
                success = True
            else:
                print(f"警告: 未获取到 {code} tushare 数据，尝试使用 akshare 备用")
        except Exception as e:
            print(f"获取 {code} tushare 数据失败: {e}，尝试使用 akshare 备用")
            
        if not success:
            # akshare 需要去掉后缀，比如 '510050.SH' -> '510050'
            symbol = code.split('.')[0]
            try:
                df = ak.fund_etf_hist_em(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
                if df is not None and not df.empty:
                    # 缓存 akshare 原始数据
                    all_data_cache[code] = df.copy()
                    
                    df = df[['日期', '收盘']].copy()
                    df.columns = ['trade_date', 'close']
                    df['ts_code'] = code
                    # 将日期字符串转换为标准格式以便后续处理一致
                    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
                    etf_data_list.append(df)
                else:
                    print(f"警告: 未获取到 {code} akshare 数据")
            except Exception as e:
                print(f"获取 {code} akshare 数据失败: {e}")
            
    # 查沪深300数据 (510300) 用于市场状态判断
    csi300_df = pd.DataFrame()
    try:
        print("获取 沪深300 (510300) 数据...")
        df = pro.fund_daily(ts_code="510300.SH", start_date=start_date, end_date=end_date)
        if df is not None and not df.empty:
            adj_df = pro.fund_adj(ts_code="510300.SH", start_date=start_date, end_date=end_date)
            if not adj_df.empty:
                df = pd.merge(df, adj_df[['ts_code', 'trade_date', 'adj_factor']], on=['ts_code', 'trade_date'], how='left')
                df['close'] = df['close'] * df['adj_factor']
            
            csi300_df = df[['trade_date', 'close']].copy()
            csi300_df['trade_date'] = pd.to_datetime(csi300_df['trade_date']).dt.strftime('%Y-%m-%d')
            csi300_df = csi300_df.set_index('trade_date')
        else:
            print("警告: 未获取到 沪深300 tushare 数据，尝试使用 akshare 备用")
    except Exception as e:
        print(f"获取 沪深300 tushare 数据失败: {e}，尝试使用 akshare 备用")
        
    if csi300_df.empty:
        try:
            df = ak.fund_etf_hist_em(symbol='510300', period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
            if df is not None and not df.empty:
                csi300_df = df[['日期', '收盘']].copy()
                csi300_df.columns = ['trade_date', 'close']
                csi300_df['trade_date'] = pd.to_datetime(csi300_df['trade_date']).dt.strftime('%Y-%m-%d')
                csi300_df = csi300_df.set_index('trade_date')
            else:
                print("警告: 未获取到 沪深300 akshare 数据")
        except Exception as e:
            print(f"获取 沪深300 akshare 数据失败: {e}")

    if not etf_data_list:
        return pd.DataFrame(), pd.Series(dtype=float)
        
    all_etf_df = pd.concat(etf_data_list, ignore_index=True)
    price_matrix = all_etf_df.pivot(index='trade_date', columns='ts_code', values='close').sort_index()
    
    return price_matrix, csi300_df['close'] if not csi300_df.empty else pd.Series(dtype=float)

def main():
    print(f"开始执行任务: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    price_matrix, csi300_close = fetch_data()
    
    if len(price_matrix) < 60:
        print("数据不足 60 个交易日，无法计算动量，程序退出。")
        return
        
    latest_date = price_matrix.index[-1]
    print(f"最新数据日期: {latest_date}")
    
    market_state = get_market_state(csi300_close)
    print(f"当前市场状态: {market_state}")
    
    # 计算动量得分
    scores = {}
    returns_data = {}
    
    for code in ALL_POOLS:
        if code not in price_matrix.columns:
            continue
        prices = price_matrix[code].dropna()
        if len(prices) < 60:
            continue
            
        score = 0
        for w, weight in MOMENTUM_WEIGHTS.items():
            if len(prices) >= w:
                ret = (prices.iloc[-1] / prices.iloc[-w] - 1)
                score += ret * weight
                
        # RSI惩罚
        if len(prices) >= 15:
            deltas = prices.iloc[-15:].diff().dropna()
            gains = deltas[deltas > 0]
            losses = -deltas[deltas < 0]
            if len(losses) > 0 and losses.sum() > 0:
                rs = gains.sum() / losses.sum()
                rsi = 100 - (100 / (1 + rs))
                if rsi > RSI_OVERBOUGHT_THRESHOLD:
                    score *= (1 - RSI_PENALTY)
        
        scores[code] = score
        
        # 计算近期涨跌幅，用于展示
        def calc_ret(p, days):
            if len(p) > days:
                return (p.iloc[-1] / p.iloc[-(days+1)] - 1) * 100
            return 0.0
            
        returns_data[code] = {
            "1日": calc_ret(prices, 1),
            "5日": calc_ret(prices, 5),
            "10日": calc_ret(prices, 10),
            "20日": calc_ret(prices, 20)
        }
        
    if not scores:
        print("没有足够的标的得分数据。")
        return
        
    # 选出最新的 TOP N
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    target_holdings = [code for code, score in sorted_scores[:TOP_N]]
    
    # 获取旧持仓
    portfolio = load_portfolio()
    current_holdings = portfolio.get("current_holdings", [])
    
    # 比较持仓变化
    sell_list = [code for code in current_holdings if code not in target_holdings]
    buy_list = [code for code in target_holdings if code not in current_holdings]
    keep_list = [code for code in current_holdings if code in target_holdings]
    
    # 保存新持仓
    portfolio["current_holdings"] = target_holdings
    portfolio["last_update"] = str(latest_date)
    save_portfolio(portfolio)
    
    # ==================== 构建推送消息 ====================
    def highlight_etf(code):
        name = ETF_NAMES.get(code, code)
        return f'<a href="#" style="color: red; text-decoration: none; font-size: 1.2em;">{name}</a>'
        
    msg_lines = [
        "【v29.5 策略综合评分与监控】",
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} (数据截至: {latest_date})\n",
        f"📊 **市场状态**: `{market_state.upper()}`",
        "--- 💡 调仓建议 ---"
    ]
    
    if not sell_list and not buy_list:
        msg_lines.append("✅ 建议 **继续持有** 当前所有仓位，无需调仓。")
    else:
        if sell_list:
            sells_str = ", ".join([highlight_etf(c) for c in sell_list])
            msg_lines.append(f"📉 **建议卖出**: {sells_str}")
        if buy_list:
            buys_str = ", ".join([highlight_etf(c) for c in buy_list])
            msg_lines.append(f"📈 **建议买入**: {buys_str}")
            
    if keep_list:
        keeps_str = ", ".join([ETF_NAMES.get(c, c) for c in keep_list])
        msg_lines.append(f"🛡️ **继续持有**: {keeps_str}\n")
        
    msg_lines.append("--- 📊 综合动量评分排名 ---")
    for i, (code, score) in enumerate(sorted_scores):
        name = ETF_NAMES.get(code, code)
        msg_lines.append(f"🎯 {name}({code}): {score:.4f}")

    def format_return(val, is_1d=False):
        """格式化收益率，Markdown 模式下内嵌 HTML 标签"""
        color = "red" if val > 0 else "green" if val < 0 else ""
        
        val_str = f"{val:+.2f}%"
        style_list = ["text-decoration: none;"]
        if color:
            style_list.append(f"color: {color};")
            
        if is_1d:
            style_list.append("font-size: 1.2em;")
        elif abs(val) >= 5:
            # 大于5的，稍微加大一点字号（1.05em），不加粗
            style_list.append("font-size: 1.05em;")
            
        style = " ".join(style_list)
        return f'<a href="#" style="{style}">{val_str}</a>'

    msg_lines.append("\n--- 近期涨跌幅 ---")
    for code, _ in sorted_scores:
        name = ETF_NAMES.get(code, code)
        rets = returns_data.get(code, {})
        if rets:
            msg_lines.append(
                f"📈 {name}:\n"
                f"   1日: {format_return(rets['1日'], is_1d=True)}\n"
                f"   5日: {format_return(rets['5日'])} | 10日: {format_return(rets['10日'])} | 20日: {format_return(rets['20日'])}"
            )

    # 提取近200日数据供AI分析
    ai_context_data = {
        "轮动数据": "\n".join(msg_lines),
        "调仓建议": "卖出: " + ", ".join([ETF_NAMES.get(c, c) for c in sell_list]) + " | 买入: " + ", ".join([ETF_NAMES.get(c, c) for c in buy_list]),
        "近200日收盘价": {}
    }

    # 遍历缓存提取数据
    for code, _ in sorted_scores:
        name = ETF_NAMES.get(code, code)
        if code in all_data_cache:
            df = all_data_cache[code]
            if '收盘' in df.columns: # akshare 数据
                close_prices = df['收盘'].tail(200).tolist()
            else: # tushare 数据
                close_prices = df['close'].tail(200).tolist()
            # 缩减数据体积，每隔5天取一个点代表趋势
            sampled_prices = [round(p, 3) for i, p in enumerate(close_prices) if i % 5 == 0 or i == len(close_prices)-1]
            ai_context_data["近200日收盘价"][name] = sampled_prices

    # 调用 AI 分析
    print("\n正在请求 DeepSeek AI 解读...")
    ai_analysis = call_deepseek_analysis(str(ai_context_data))
    
    # 将 AI 分析附加到推送内容末尾
    msg_lines.append("\n--- 🤖 AI 策略解读 ---")
    msg_lines.append(ai_analysis)

    content = "\n".join(msg_lines)
    print("\n生成的推送内容如下:\n")
    print(content)
    
    # 发送推送
    send_wx_msg(content, contentType=3)

if __name__ == "__main__":
    main()
