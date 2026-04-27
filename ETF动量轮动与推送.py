import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
import requests
import json
import os

# ==================== 配置 ====================
# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# ETF池
ETF_POOL = {
    '510880': '红利ETF',
    '159915': '创业板ETF',
    '513100': '纳指ETF',
    '518880': '黄金ETF'
}

# 动量因子参数
BIAS_N = 25
SLOPE_N = 25
EFFICIENCY_N = 25
MOMENTUM_DAY = 25

# 权重配置
WEIGHT_BIAS = 0.2
WEIGHT_SLOPE = 0.3
WEIGHT_EFFICIENCY = 0.5

# 调仓阈值
REBALANCE_THRESHOLD = 1.5

# 虚拟持仓文件
PORTFOLIO_FILE = os.path.join(os.getcwd(), "virtual_portfolio.json")

# 微信推送配置 (WxPusher)

WXPUSHER_APP_TOKEN = "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc"
WXPUSHER_TOPIC_IDS = [43351]
WXPUSHER_URL = "https://wxpusher.zjiecode.com/api/send/message"

# ==================== 因子计算函数 ====================
def bias_momentum(series, window=BIAS_N):
    if len(series) < window: return np.nan
    ma = series.rolling(window=window, min_periods=1).mean()
    bias = series / ma
    if len(bias) < window or bias.iloc[-window] == 0: return np.nan
    bias_recent = bias.iloc[-window:]
    base = bias_recent.iloc[0]
    if base == 0: return np.nan
    y = (bias_recent / base).values.reshape(-1, 1)
    x = np.arange(window).reshape(-1, 1)
    lr = LinearRegression()
    lr.fit(x, y)
    return float(lr.coef_[0].item()) * 10000

def slope_momentum(series, window=SLOPE_N):
    if len(series) < window: return np.nan
    series_recent = series.iloc[-window:]
    base = series_recent.iloc[0]
    if base == 0: return np.nan
    y = (series_recent / base).values.reshape(-1, 1)
    x = np.arange(1, window + 1).reshape(-1, 1)
    lr = LinearRegression()
    lr.fit(x, y)
    return float(lr.coef_[0].item()) * 10000 * float(lr.score(x, y))

def efficiency_momentum(history, window=EFFICIENCY_N):
    """效率动量：净移动距离/总波动 * 动量"""
    if len(history) < window: return np.nan
    df_recent = history.iloc[-window:]
    pivot = (df_recent['开盘'] + df_recent['最高'] + df_recent['最低'] + df_recent['收盘']) / 4.0
    pivot = pivot.ffill()
    if pivot.iloc[0] <= 0 or pivot.iloc[-1] <= 0: return np.nan
    
    momentum = 100 * np.log(pivot.iloc[-1] / pivot.iloc[0])
    direction = abs(np.log(pivot.iloc[-1]) - np.log(pivot.iloc[0]))
    volatility = np.log(pivot).diff().abs().sum()
    
    efficiency_ratio = direction / volatility if volatility > 0 else 0
    return momentum * efficiency_ratio

# ==================== 虚拟持仓管理 ====================
def load_portfolio():
    try:
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"current_hold": None, "hold_price": 0.0, "nav": 1.0}
    except Exception as e:
        print(f"读取虚拟持仓文件失败: {e}")
        return {"current_hold": None, "hold_price": 0.0, "nav": 1.0}

def save_portfolio(portfolio):
    try:
        with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存虚拟持仓文件失败: {e}")
        raise

# ==================== AI 分析模块 (DeepSeek) ====================
def call_deepseek_analysis(context):
    if not DEEPSEEK_API_KEY or "sk-" not in DEEPSEEK_API_KEY:
        print("[Warning] 未配置 DEEPSEEK_API_KEY，跳过 AI 分析。")
        return "未配置 API Key，无法生成 AI 解读。"

    system_prompt = """你是一位拥有20年经验的量化策略分析师。请基于提供的ETF动量轮动数据、最新调仓决策以及近期涨跌幅，撰写一段简明扼要的AI策略解读。

    **分析逻辑与要求：**

    1. **当前局势点评**:
       - 结合当前排名第一的ETF及其综合评分，点评当前市场哪类资产表现最强。
       - 分析各ETF近期（1日、3日、5日、10日）涨跌幅，判断其上涨是短期脉冲还是趋势延续。
    
    2. **调仓逻辑分析**:
       - 如果发生调仓（卖出A，买入B），请解释为什么模型做出了这个决策（结合动量衰减与新主线崛起）。
       - 如果继续持有，说明持仓标的的动量健康度。
       
    3. **风险提示**:
       - 观察排名靠后的ETF是否出现极端下跌（可能蕴含反弹机会或持续崩盘风险）。
       - 提醒当前持仓的潜在风险（如高位回调、波动率放大的风险）。

    **输出格式要求：**
    * 使用 Markdown 格式。
    * 字数控制在 200-300 字左右，语言精炼，直击要害。
    * 语气专业、客观。不要使用模棱两可的废话。
    * 不需要输出大标题，直接输出解读内容。
    """

    user_prompt = f"这是最新的ETF动量轮动数据与决策，请开始解读：\n{context}"

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
def send_wx_msg(content: str, summary: str = "ETF综合评分与监控", contentType: int = 1):
    """发送微信推送
    contentType: 1表示文字，2表示HTML，3表示Markdown
    """
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

# ==================== 主流程 ====================
def main():
    print(f"开始执行任务: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取过去150天的数据以保证有足够的交易日
    start_date = (datetime.now() - timedelta(days=150)).strftime("%Y%m%d")
    end_date = datetime.now().strftime("%Y%m%d")
    
    factor_df = pd.DataFrame(index=ETF_POOL.keys(), columns=['bias', 'slope', 'efficiency'], dtype='float64')
    returns_data = {}
    
    for code, name in ETF_POOL.items():
        try:
            print(f"正在获取 {name} ({code}) 的数据...")
            # 使用 akshare 获取 ETF 日线前复权数据
            df = ak.fund_etf_hist_em(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
            if df is None or df.empty:
                print(f"未获取到 {code} 的数据")
                continue
                
            # 计算 1日, 3日, 5日, 10日 涨跌幅
            close_series = df['收盘']
            
            # 安全计算收益率
            def calc_return(series, days):
                if len(series) > days:
                    return (series.iloc[-1] / series.iloc[-(days+1)] - 1) * 100
                return 0.0
                
            ret_1d = calc_return(close_series, 1)
            ret_3d = calc_return(close_series, 3)
            ret_5d = calc_return(close_series, 5)
            ret_10d = calc_return(close_series, 10)
            
            latest_price = close_series.iloc[-1]
            
            returns_data[code] = {
                "latest_price": latest_price,
                "1日": ret_1d,
                "3日": ret_3d,
                "5日": ret_5d,
                "10日": ret_10d
            }
            
            # 截取历史数据计算动量（与原策略保持一致：84根K线）
            history_bars = max(BIAS_N, MOMENTUM_DAY, SLOPE_N, EFFICIENCY_N) + 60 - 1 # 84
            if len(df) > history_bars:
                history = df.iloc[-history_bars:]
            else:
                history = df
                
            if len(history) < 25:
                print(f"{name} ({code}) 数据不足25天，跳过因子计算")
                continue
                
            history_norm_close = history['收盘'] / history.iloc[0]['收盘']
            
            factor_df.at[code, 'bias'] = bias_momentum(history_norm_close)
            factor_df.at[code, 'slope'] = slope_momentum(history_norm_close)
            factor_df.at[code, 'efficiency'] = efficiency_momentum(history)
            
        except Exception as e:
            print(f"处理 {code} 时发生异常: {e}")
            
    # 清除空数据
    factor_df = factor_df.dropna()
    if factor_df.empty:
        print("没有足够的因子数据，程序退出。")
        return
        
    # Z-score 标准化
    for col in factor_df.columns:
        std = factor_df[col].std(ddof=0)
        if std == 0:
            factor_df[col] = 0
        else:
            factor_df[col] = (factor_df[col] - factor_df[col].mean()) / std
            
    # 计算综合得分
    combined_scores = (
        factor_df['bias'] * WEIGHT_BIAS +
        factor_df['slope'] * WEIGHT_SLOPE +
        factor_df['efficiency'] * WEIGHT_EFFICIENCY
    )
    
    sorted_scores = combined_scores.sort_values(ascending=False)
    
    # ==================== 调仓决策与模拟持仓 ====================
    portfolio = load_portfolio()
    current_hold = portfolio.get("current_hold")
    
    top_candidate = sorted_scores.index[0]
    top_score = sorted_scores.iloc[0]
    
    decision_msg = ""
    
    def highlight_etf(code):
        name = ETF_POOL.get(code, code)
        # 取消加粗，使用字号放大
        return f'<a href="#" style="color: red; text-decoration: none; font-size: 1.2em;">{name}</a>'
    
    if not current_hold:
        decision_msg = f"无持仓，建议买入 {highlight_etf(top_candidate)}"
        portfolio["current_hold"] = top_candidate
        portfolio["hold_price"] = returns_data[top_candidate]["latest_price"]
        save_portfolio(portfolio)
    else:
        current_score = combined_scores.get(current_hold, np.nan)
        
        # 记录一下如果是同个标的，或者符合调仓要求
        if current_hold == top_candidate:
            decision_msg = f"当前持仓 {highlight_etf(current_hold)} 仍为第一，建议继续持有"
            # 更新最新价格作为记录（可选）
            portfolio["hold_price"] = returns_data[current_hold]["latest_price"]
            save_portfolio(portfolio)
        else:
            if pd.isna(current_score) or top_score >= current_score * REBALANCE_THRESHOLD:
                decision_msg = f"触发调仓阈值，建议卖出 {highlight_etf(current_hold)}，买入 {highlight_etf(top_candidate)}"
                portfolio["current_hold"] = top_candidate
                portfolio["hold_price"] = returns_data[top_candidate]["latest_price"]
                save_portfolio(portfolio)
            else:
                decision_msg = f"未触发调仓阈值，建议继续持有 {highlight_etf(current_hold)}"
                portfolio["hold_price"] = returns_data[current_hold]["latest_price"]
                save_portfolio(portfolio)
    
    # ==================== 构建推送消息 ====================
    msg_lines = [
        "【ETF综合动量评分与调仓决策】", 
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        "--- 💡 调仓决策 ---",
        f"{decision_msg}\n",
        "--- 📊 综合动量评分排名 ---"
    ]
    
    context_data = {
        "decision": decision_msg,
        "scores": {},
        "returns": {}
    }
    
    for code, score in sorted_scores.items():
        name = ETF_POOL.get(code, "")
        msg_lines.append(f"🎯 {name}({code}): {score:.4f}")
        context_data["scores"][name] = round(score, 4)
        
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
    for code in ETF_POOL.keys():
        if code in returns_data:
            name = ETF_POOL.get(code, "")
            rets = returns_data[code]
            context_data["returns"][name] = {k: round(v, 2) for k, v in rets.items() if k != "latest_price"}
            msg_lines.append(
                f"📈 {name}:\n"
                f"   1日: {format_return(rets['1日'], is_1d=True)}\n"
                f"   3日: {format_return(rets['3日'])} | 5日: {format_return(rets['5日'])} | 10日: {format_return(rets['10日'])}"
            )
            
    # 获取 AI 解读
    print("正在请求 DeepSeek 进行策略解读...")
    ai_interpretation = call_deepseek_analysis(json.dumps(context_data, ensure_ascii=False, indent=2))
    
    msg_lines.append("\n--- 🤖 AI 策略解读 ---")
    msg_lines.append(ai_interpretation)
            
    # WxPusher 中 contentType = 3 为 Markdown，这样 HTML font 标签和 ** 才会生效
    content = "\n".join(msg_lines)
    print("\n生成的推送内容如下:\n")
    print(content)
    
    # 发送推送 (保留 Markdown 格式，因为前面的文本可能使用了 Markdown 排版)
    send_wx_msg(content, contentType=3)

if __name__ == "__main__":
    main()
