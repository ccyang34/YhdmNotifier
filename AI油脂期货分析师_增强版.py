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
    从 akshare 获取期货数据（含实时行情拼接功能）
    symbols: 
    - 'y0' (豆油主力), 'm0' (豆粕主力), 'p0' (棕榈油主力)
    - 'B0' (大豆二号连续合约)
    days: 获取天数，默认180天（约半年）
    """
    try:
        print(f"正在获取 {symbol} 的历史数据...")
        
        # 使用 akshare 获取期货主力连续数据
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
        
        # 确保数据类型正确（添加空值检查）
        if 'volume' in df.columns:
            df['volume'] = df['volume'].fillna(0).astype(int)
        if 'hold' in df.columns:
            df['hold'] = df['hold'].fillna(0).astype(int)
        if 'open' in df.columns:
            df['open'] = df['open'].fillna(0.0).astype(float)
        if 'high' in df.columns:
            df['high'] = df['high'].fillna(0.0).astype(float)
        if 'low' in df.columns:
            df['low'] = df['low'].fillna(0.0).astype(float)
        if 'close' in df.columns:
            df['close'] = df['close'].fillna(0.0).astype(float)
        if 'settle' in df.columns:
            df['settle'] = df['settle'].fillna(0.0).astype(float)
        
        # 只保留最近 N 天的数据
        cutoff_date = (get_beijing_time() - timedelta(days=days)).replace(tzinfo=None)
        df = df[df['date'] >= cutoff_date]
        
        print(f"✅ 成功获取 {symbol} 历史数据，共 {len(df)} 条记录")
        print(f"   历史数据日期范围: {df['date'].min().strftime('%Y-%m-%d')} 至 {df['date'].max().strftime('%Y-%m-%d')}")
        
        # 📡 拼接实时行情数据
        print("📡 正在获取实时行情数据...")
        try:
            # 使用akshare的期货实时数据接口
            realtime_data = ak.futures_zh_spot(symbol=symbol.upper())
            
            if realtime_data is not None and not realtime_data.empty:
                print(f"✅ 成功获取 {symbol} 实时行情数据")
                
                # 解析实时数据
                realtime_row = realtime_data.iloc[0]
                
                # 获取今日日期
                today = pd.Timestamp.now().normalize()
                
                # 创建实时数据记录
                realtime_record = {
                    'date': today,
                    'open': float(realtime_row['open']),
                    'high': float(realtime_row['high']),
                    'low': float(realtime_row['low']),
                    'close': float(realtime_row['current_price']),
                    'volume': int(realtime_row['volume']) if pd.notnull(realtime_row['volume']) else 0,
                    'hold': int(realtime_row['hold']) if pd.notnull(realtime_row['hold']) else 0,
                    'settle': float(realtime_row['last_settle_price'])
                }
                
                # 将实时数据转换为DataFrame
                realtime_df = pd.DataFrame([realtime_record])
                
                # 检查是否需要更新历史数据中的最新记录
                if len(df) > 0:
                    last_date = df['date'].max()
                    
                    # 如果实时数据的日期与历史数据最后日期相同，更新最后一条记录
                    if last_date.date() == today.date():
                        print(f"🔄 更新今日数据 (最新价: {realtime_record['close']:.2f}, 涨跌幅: {((realtime_record['close'] - realtime_row['last_close']) / realtime_row['last_close'] * 100):.2f}%)")
                        # 更新最后一行数据，确保数据类型兼容
                        for key, value in realtime_record.items():
                            if key in df.columns:
                                # 确保数据类型兼容性
                                if key in ['volume', 'hold']:
                                    df.loc[df.index[-1], key] = int(value) if pd.notnull(value) else 0
                                elif key in ['open', 'high', 'low', 'close', 'settle']:
                                    df.loc[df.index[-1], key] = float(value) if pd.notnull(value) else 0.0
                                else:
                                    df.loc[df.index[-1], key] = value
                    else:
                        # 如果实时数据日期更新，追加新记录
                        print(f"➕ 添加新记录 (日期: {today.strftime('%Y-%m-%d')}, 最新价: {realtime_record['close']:.2f})")
                        df = pd.concat([df, realtime_df], ignore_index=True)
                
                print(f"📊 最终数据范围: {df['date'].min().strftime('%Y-%m-%d')} 至 {df['date'].max().strftime('%Y-%m-%d')}")
                print(f"最新价格: {df['close'].iloc[-1]:.2f} | 数据完整性: {df.dropna().shape[0]}/{df.shape[0]} 条记录")
            else:
                print("⚠️ 未获取到实时行情数据，仅使用历史数据")
        
        except Exception as e:
            print(f"⚠️ 获取实时行情失败: {e}")
            print("继续使用历史数据进行分析")
        
        return df
        
    except Exception as e:
        print(f"[Error] 获取 {symbol} 数据失败: {e}")
        print(f"[严重] {symbol} 数据获取失败，无法生成可靠的分析报告")
        print(f"[说明] 为保证分析准确性，程序拒绝使用模拟数据")
        return None

def fetch_us_data():
    """
    获取美豆数据（CBOT-黄豆合约 S）
    严格禁止使用模拟数据，所有数据必须来自真实数据源
    使用akshare库的新浪财经外盘期货历史行情数据接口
    """
    try:
        print("正在获取美豆数据...")
        
        # 尝试导入akshare
        try:
            import akshare as ak
        except ImportError:
            print("[Error] 缺少akshare依赖，请安装: pip install akshare")
            return None
        
        # 获取美豆数据：CBOT-黄豆合约 (S)
        # 使用akshare的新浪财经外盘期货历史行情数据接口
        symbol = "S"  # 美豆(CBOT)合约代码
        
        print(f"正在调用akshare接口获取美豆数据(symbol={symbol})...")
        us_data = ak.futures_foreign_hist(symbol=symbol)
        
        if us_data is not None and not us_data.empty:
            print(f"✅ 成功获取美豆历史数据，共 {len(us_data)} 条记录")
            
            # 数据预处理和格式化
            if 'date' in us_data.columns:
                us_data['date'] = pd.to_datetime(us_data['date'])
                us_data = us_data.sort_values('date').reset_index(drop=True)
                
                # 计算涨跌幅
                us_data['pct_change'] = us_data['close'].pct_change() * 100
                
                # 重命名列以保持与其他数据源的一致性
                column_mapping = {
                    'volume': 'volume',  # akshare返回的列名
                    'position': 'hold'   # 持仓量列名映射
                }
                us_data.rename(columns=column_mapping, inplace=True)
                
                # 确保所有必需列存在
                required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                if all(col in us_data.columns for col in required_columns):
                    print(f"美豆历史数据日期范围: {us_data['date'].min().strftime('%Y-%m-%d')} 至 {us_data['date'].max().strftime('%Y-%m-%d')}")
                    
                    # 删除多余的列（s列似乎是akshare的内部标识）
                    if 's' in us_data.columns:
                        us_data.drop('s', axis=1, inplace=True)
                    
                    # 确保数据类型正确
                    us_data['open'] = us_data['open'].astype(float)
                    us_data['high'] = us_data['high'].astype(float)
                    us_data['low'] = us_data['low'].astype(float)
                    us_data['close'] = us_data['close'].astype(float)
                    us_data['volume'] = us_data['volume'].astype(int)
                    
                    if 'hold' in us_data.columns:
                        us_data['hold'] = us_data['hold'].fillna(0).astype(int)
                    
                    # 拼接实时行情数据
                    print("📡 正在获取美豆实时行情数据...")
                    try:
                        realtime_data = ak.futures_foreign_commodity_realtime(symbol=symbol)
                        
                        if realtime_data is not None and not realtime_data.empty:
                            print(f"✅ 成功获取美豆实时行情数据")
                            
                            # 解析实时数据
                            realtime_row = realtime_data.iloc[0]
                            
                            # 获取今日日期
                            today = pd.Timestamp.now().normalize()
                            
                            # 创建实时数据记录
                            realtime_record = {
                                'date': today,
                                'open': float(realtime_row['开盘价']),
                                'high': float(realtime_row['最高价']),
                                'low': float(realtime_row['最低价']),
                                'close': float(realtime_row['最新价']),
                                'volume': int(float(realtime_row['持仓量'])) if realtime_row['持仓量'] != '-' else 0,
                                'hold': int(float(realtime_row['持仓量'])) if realtime_row['持仓量'] != '-' else 0,
                                'settlement': float(realtime_row['昨日结算价']),
                                'pct_change': float(realtime_row['涨跌幅'])
                            }
                            
                            # 将实时数据转换为DataFrame
                            realtime_df = pd.DataFrame([realtime_record])
                            
                            # 检查是否需要更新历史数据中的最新记录
                            if len(us_data) > 0:
                                last_date = us_data['date'].max()
                                
                                # 如果实时数据的日期与历史数据最后日期相同，更新最后一条记录
                                if last_date.date() == today.date():
                                    print(f"🔄 更新今日数据 (最新价: {realtime_record['close']:.2f})")
                                    # 更新最后一行数据，确保数据类型兼容
                                    for key, value in realtime_record.items():
                                        if key in us_data.columns:
                                            # 确保数据类型兼容性 - 先明确转换类型
                                            if key in ['volume', 'hold']:
                                                try:
                                                    us_data.at[us_data.index[-1], key] = int(value) if pd.notnull(value) else 0
                                                except (ValueError, TypeError):
                                                    us_data.at[us_data.index[-1], key] = 0
                                            elif key in ['open', 'high', 'low', 'close', 'settlement', 'pct_change']:
                                                try:
                                                    us_data.at[us_data.index[-1], key] = float(value) if pd.notnull(value) else 0.0
                                                except (ValueError, TypeError):
                                                    us_data.at[us_data.index[-1], key] = 0.0
                                            else:
                                                us_data.at[us_data.index[-1], key] = value
                                else:
                                    # 如果实时数据日期更新，追加新记录
                                    print(f"➕ 添加新记录 (日期: {today.strftime('%Y-%m-%d')}, 最新价: {realtime_record['close']:.2f})")
                                    us_data = pd.concat([us_data, realtime_df], ignore_index=True)
                            
                            print(f"📊 最终数据范围: {us_data['date'].min().strftime('%Y-%m-%d')} 至 {us_data['date'].max().strftime('%Y-%m-%d')}")
                        else:
                            print("⚠️ 未获取到实时行情数据，仅使用历史数据")
                    
                    except Exception as e:
                        print(f"⚠️ 获取实时行情失败: {e}")
                        print("继续使用历史数据进行分析")
                    
                    return us_data
                else:
                    print(f"[Error] 美豆数据格式不完整，缺少必要列")
                    print(f"可用列: {list(us_data.columns)}")
                    return None
            else:
                print("[Error] 美豆数据缺少日期列")
                return None
        else:
            print("[Error] 获取美豆数据失败，返回数据为空")
            return None
        
    except Exception as e:
        print(f"[Error] 获取美豆数据失败: {e}")
        print(f"[严重] 为保证分析准确性，程序拒绝使用模拟数据")
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

def calculate_crushing_profit(df_dict):
    """
    计算榨利
    基本公式：榨利 = (豆粕价格 + 豆油价格) / 压榨比例 - 大豆价格 - 压榨成本
    
    标准压榨比例：
    - 豆粕：78-80%
    - 豆油：18-20%
    """
    try:
        # 使用标准的压榨比例
        soybean_meal_ratio = 0.79  # 79%
        soybean_oil_ratio = 0.19   # 19%
        crushing_cost = 120        # 压榨成本，约120元/吨
        
        # 获取最新数据
        m0_latest = df_dict['m0'].iloc[-1]
        y0_latest = df_dict['y0'].iloc[-1]
        s_latest = df_dict['s'].iloc[-1]
        
        # 计算榨利
        profit_per_ton = (m0_latest['close'] * soybean_meal_ratio + 
                         y0_latest['close'] * soybean_oil_ratio - 
                         s_latest['close'] - crushing_cost)
        
        return profit_per_ton
        
    except Exception as e:
        print(f"[Error] 计算榨利失败: {e}")
        return None

def prepare_context_for_ai(df_dict):
    """
    为 AI 准备分析上下文，包含榨利分析
    """
    # 获取最新数据
    y0_latest = df_dict['y0'].iloc[-1]
    p0_latest = df_dict['p0'].iloc[-1]
    m0_latest = df_dict['m0'].iloc[-1]
    s_latest = df_dict['s'].iloc[-1]
    us_s_latest = df_dict['us_s'].iloc[-1] if 'us_s' in df_dict else None
    
    # 获取近期数据（最近60天）
    y0_recent = df_dict['y0'].tail(60)
    p0_recent = df_dict['p0'].tail(60)
    m0_recent = df_dict['m0'].tail(60)
    s_recent = df_dict['s'].tail(60)
    us_s_recent = df_dict['us_s'].tail(60) if 'us_s' in df_dict else None
    
    # 计算价差
    price_spread = y0_latest['close'] - p0_latest['close']
    spread_history = y0_recent['close'] - p0_recent['close']
    spread_mean = spread_history.mean()
    spread_std = spread_history.std()
    
    # 计算榨利
    soybean_meal_ratio = 0.79
    soybean_oil_ratio = 0.19
    crushing_cost = 120
    
    current_profit = (m0_latest['close'] * soybean_meal_ratio + 
                     y0_latest['close'] * soybean_oil_ratio - 
                     s_latest['close'] - crushing_cost)
    
    # 计算历史榨利趋势
    profit_history = []
    for i in range(60):
        try:
            m0_price = m0_recent.iloc[i]['close']
            y0_price = y0_recent.iloc[i]['close']
            s_price = s_recent.iloc[i]['close']
            profit = (m0_price * soybean_meal_ratio + y0_price * soybean_oil_ratio - s_price - crushing_cost)
            profit_history.append(profit)
        except:
            profit_history.append(current_profit)
    
    profit_mean = np.mean(profit_history)
    profit_std = np.std(profit_history)
    
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
    
    # 构建豆粕完整数据CSV
    m0_data_lines = ["日期,开盘价,最高价,最低价,收盘价,成交量,持仓量,涨跌幅(%)"]
    for _, row in m0_recent.iterrows():
        date_str = row['date'].strftime('%Y-%m-%d')
        pct = row['pct_change'] if pd.notnull(row['pct_change']) else 0
        m0_data_lines.append(
            f"{date_str},{row['open']:.0f},{row['high']:.0f},{row['low']:.0f},"
            f"{row['close']:.0f},{row['volume']:.0f},{row['hold']:.0f},{pct:+.2f}"
        )
    m0_data_str = "\n".join(m0_data_lines)
    
    # 构建大豆完整数据CSV
    s_data_lines = ["日期,开盘价,最高价,最低价,收盘价,成交量,持仓量,涨跌幅(%)"]
    for _, row in s_recent.iterrows():
        date_str = row['date'].strftime('%Y-%m-%d')
        pct = row['pct_change'] if pd.notnull(row['pct_change']) else 0
        s_data_lines.append(
            f"{date_str},{row['open']:.0f},{row['high']:.0f},{row['low']:.0f},"
            f"{row['close']:.0f},{row['volume']:.0f},{row['hold']:.0f},{pct:+.2f}"
        )
    s_data_str = "\n".join(s_data_lines)
    
    # 美豆数据（如果有）
    us_s_data_str = ""
    if us_s_recent is not None:
        us_s_data_lines = ["日期,开盘价,最高价,最低价,收盘价,成交量,持仓量,涨跌幅(%)"]
        for _, row in us_s_recent.iterrows():
            date_str = row['date'].strftime('%Y-%m-%d')
            pct = row['pct_change'] if pd.notnull(row['pct_change']) else 0
            us_s_data_lines.append(
                f"{date_str},{row['open']:.0f},{row['high']:.0f},{row['low']:.0f},"
                f"{row['close']:.0f},{row['volume']:.0f},{row['hold']:.0f},{pct:+.2f}"
            )
        us_s_data_str = "\n".join(us_s_data_lines)
    
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
    
    [豆粕(m0)当前状态]
    - 最新价格: {m0_latest['close']:.0f} 元/吨
    - 日涨跌幅: {m0_latest['pct_change']:+.2f}%
    - MA5: {m0_latest['MA5']:.0f}, MA20: {m0_latest['MA20']:.0f}, MA60: {m0_latest['MA60']:.0f}
    - 价格位置: {'MA5之上' if m0_latest['above_MA5'] else 'MA5之下'}, {'MA20之上' if m0_latest['above_MA20'] else 'MA20之下'}
    - 20日波动率: {m0_latest['volatility']:.2f}%
    - 成交量比: {m0_latest['volume_ratio']:.2f}倍
    - 持仓量: {m0_latest['hold']:.0f}
    
    [大豆(B0)当前状态]
    - 最新价格: {s_latest['close']:.0f} 元/吨
    - 日涨跌幅: {s_latest['pct_change']:+.2f}%
    - MA5: {s_latest['MA5']:.0f}, MA20: {s_latest['MA20']:.0f}, MA60: {s_latest['MA60']:.0f}
    - 价格位置: {'MA5之上' if s_latest['above_MA5'] else 'MA5之下'}, {'MA20之上' if s_latest['above_MA20'] else 'MA20之下'}
    - 20日波动率: {s_latest['volatility']:.2f}%
    - 成交量比: {s_latest['volume_ratio']:.2f}倍
    - 持仓量: {s_latest['hold']:.0f}
    
    {f"[美豆当前状态]\n- 最新价格: {us_s_latest['close']:.0f} 美元/吨\n- 日涨跌幅: {us_s_latest['pct_change']:+.2f}%\n- 成交量比: {us_s_latest['volume_ratio']:.2f}倍\n" if us_s_latest is not None else ""}
    
    [价差分析]
    - 当前价差(豆油-棕榈油): {price_spread:+.0f} 元/吨
    - 60日均值: {spread_mean:+.0f} 元/吨
    - 60日标准差: {spread_std:.0f} 元/吨
    - 价差偏离度: {(price_spread - spread_mean) / spread_std:.2f} 个标准差
    - 榨利状态: {'盈利' if current_profit > 0 else '亏损'}
    
    [豆油(y0)近60日完整数据]
    {y0_data_str}
    
    [棕榈油(p0)近60日完整数据]
    {p0_data_str}
    
    [豆粕(m0)近60日完整数据]
    {m0_data_str}
    
    [大豆(B0)近60日完整数据]
    {s_data_str}
    
    {f"[美豆近60日完整数据]{us_s_data_str}" if us_s_data_str else ""}

    """
    return context
# ================= AI 分析模块 =================

def call_deepseek_analysis(context):
    """调用 DeepSeek API 进行分析"""
    if not DEEPSEEK_API_KEY or "sk-" not in DEEPSEEK_API_KEY:
        print("[Warning] 未配置 DEEPSEEK_API_KEY，跳过 AI 分析。")
        return "未配置 API Key，无法生成 AI 报告。"

    system_prompt = """你是一位资深的期货分析师，专注于油脂油料品种和大豆压榨产业链分析。请基于提供的豆油(y0)、棕榈油(p0)、豆粕(m0)、大豆(B0)和美豆的历史数据，撰写一份深度分析报告。

    **分析逻辑与要求：**

    1.  **趋势判断**:
        *   分析四个品种各自的趋势方向（上涨/下跌/震荡）。
        *   结合均线系统判断当前所处的技术位置（多头排列/空头排列）。
        *   识别关键支撑位和压力位。
        
    2.  **榨利分析（核心）**:
        *   **榨利是压榨企业的盈利指标**，直接影响开工率和现货供应。
        *   计算公式：(豆粕价格×79% + 豆油价格×19% - 大豆价格 - 压榨成本)
        *   分析当前榨利水平：盈利/亏损，偏离历史均值的程度。
        *   榨利与现货供需关系：榨利高→开工率增加→豆粕豆油供应增加→价格下行
        *   榨利与外盘关系：美豆价格变化对榨利的影响。
        
    3.  **产业链联动分析**:
        *   大豆→豆粕、豆油的传导机制。
        *   豆油与棕榈油的替代关系和价差分析。
        *   外盘（美豆）与内盘的联动关系。
        
    4.  **成交量持仓量分析**:
        *   分析各品种的资金参与度。
        *   量价配合关系（放量上涨、缩量下跌等）。
        *   持仓量变化反映资金流向。
        
    5.  **交易策略建议**:
        *   给出各品种的操作方向建议(不要表格)
        *   榨利相关的套利策略（如买豆粕卖大豆等）。
        *   跨品种套利机会（豆油棕榈油、豆粕大豆等）。
        *   明确止损位和目标位。

    **输出格式要求：**
    *   使用 Markdown 格式。
    *   **必须引用数据**: 在分析时必须引用具体的价格、榨利、成交量、持仓量等数值。
    *   语气专业、客观、有洞察力。
    *   字数控制在 800-1000 字之间。

    **报告结构：**
    # 油脂期货深度分析（含榨利分析）
    ## 📊 品种走势分析
    ## 🏭 榨利分析与供需传导
    ## 📈 量价仓配合解读
    ## 🔄 产业链联动与套利机会
    ## 💡 交易策略建议
    """

    user_prompt = f"这是最新的油脂期货数据（包含豆油、棕榈油、豆粕、豆二号(B0)、美豆和榨利分析），请开始分析：\n{context}"

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 2500
    }

    try:
        # 将超时时间缩短为5分钟（300秒），重试次数保持3次
        max_retries = 3
        timeout_seconds = 300  # 5分钟超时
        
        for attempt in range(max_retries):
            try:
                print(f"[Info] 正在请求 DeepSeek AI 分析 (第{attempt + 1}次尝试, 超时时间: {timeout_seconds}秒)...")
                
                response = requests.post(
                    f"{DEEPSEEK_BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=timeout_seconds
                )
                
                if response.status_code == 200:
                    result = response.json()['choices'][0]['message']['content']
                    print(f"[Success] AI 分析完成!")
                    return result
                else:
                    error_msg = f"AI 请求失败 (HTTP {response.status_code}): {response.text}"
                    print(f"[Error] {error_msg}")
                    
                    if attempt < max_retries - 1:
                        print(f"[Info] 等待5秒后重试...")
                        import time
                        time.sleep(5)
                        continue
                    else:
                        return error_msg
                        
            except requests.exceptions.Timeout:
                timeout_error = f"AI 请求超时 (>{timeout_seconds}秒)"
                print(f"[Error] {timeout_error}")
                
                if attempt < max_retries - 1:
                    print(f"[Info] 等待10秒后重试...")
                    import time
                    time.sleep(10)
                    continue
                else:
                    return timeout_error
                    
            except requests.exceptions.ConnectionError as e:
                connection_error = f"AI 连接错误: {e}"
                print(f"[Error] {connection_error}")
                
                if attempt < max_retries - 1:
                    print(f"[Info] 等待15秒后重试...")
                    import time
                    time.sleep(15)
                    continue
                else:
                    return connection_error
                    
            except Exception as e:
                general_error = f"AI 请求异常: {e}"
                print(f"[Error] {general_error}")
                
                if attempt < max_retries - 1:
                    print(f"[Info] 等待5秒后重试...")
                    import time
                    time.sleep(5)
                    continue
                else:
                    return general_error
        
        return "AI 请求失败，已达到最大重试次数"
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
    print(f"[{beijing_time.strftime('%H:%M:%S')}] 开始执行油脂期货分析任务（含榨利分析）...")
    
    # 1. 获取数据
    print("=== 获取期货数据 ===")
    y0_df = fetch_futures_data('y0', days=180)  # 豆油
    p0_df = fetch_futures_data('p0', days=180)  # 棕榈油
    m0_df = fetch_futures_data('m0', days=180)  # 豆粕
    s_df = fetch_futures_data('B0', days=180)   # 大豆二号连续合约
    us_s_df = fetch_us_data()                    # 美豆（外部数据源）
    
    if any(df is None for df in [y0_df, p0_df, m0_df, s_df]):
        print("[Error] 核心数据获取失败，任务终止。")
        return
    
    # 2. 计算技术指标
    print("\n=== 计算技术指标 ===")
    y0_df = calculate_technical_indicators(y0_df)
    p0_df = calculate_technical_indicators(p0_df)
    m0_df = calculate_technical_indicators(m0_df)
    s_df = calculate_technical_indicators(s_df)
    
    if us_s_df is not None:
        us_s_df = calculate_technical_indicators(us_s_df)
    
    # 3. 整理数据字典
    df_dict = {
        'y0': y0_df,
        'p0': p0_df,
        'm0': m0_df,
        's': s_df,
    }
    if us_s_df is not None:
        df_dict['us_s'] = us_s_df
    
    # 4. 计算榨利
    current_profit = calculate_crushing_profit(df_dict)
    if current_profit is not None:
        print(f"\n=== 当前榨利: {current_profit:.0f} 元/吨 ===")
    
    # 5. 生成分析上下文
    context = prepare_context_for_ai(df_dict)
    print("\n--- 生成的数据上下文 ---")
    print(context)
    
    # 6. 调用 AI 分析
    print(f"\n[{get_beijing_time().strftime('%H:%M:%S')}] 正在请求 DeepSeek 进行分析...")
    ai_report = call_deepseek_analysis(context)
    
    # 7. 组合最终报告
    beijing_time = get_beijing_time()
    report_header = f"""
> **推送时间**: {beijing_time.strftime('%Y-%m-%d %H:%M')} (北京时间) | 每个交易日收盘后推送
> 
> **品种说明**: 
    > - **豆油(y0)**: 大商所豆油主力连续合约
    > - **棕榈油(p0)**: 大商所棕榈油主力连续合约
    > - **豆粕(m0)**: 大商所豆粕主力连续合约
    > - **大豆(B0)**: 大商所大豆二号连续合约
    > - **美豆(S)**: CBOT-黄豆合约
    > - **榨利分析**: (豆粕×79% + 豆油×19% - 大豆 - 120元/吨成本)
    > - 榨利水平直接影响压榨企业开工率和现货供应

---
"""
    
    final_report = report_header + ai_report + f"""

---
*数据来源: AkShare | AI 分析: DeepSeek*
    """
    
    # 8. 保存分析报告
    filename = f"futures_oil_report_enhanced_{beijing_time.strftime('%Y%m%d')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(final_report)
    print(f"[Info] 报告已保存至 {filename}")
    
    # 9. 推送分析报告
    push_title = f"油脂期货分析日报（含榨利）({beijing_time.strftime('%Y-%m-%d')})"
    send_push(push_title, final_report)

if __name__ == "__main__":
    main()
