#!/usr/bin/env python3
"""
持仓汇总推送: 计算持仓盈亏，推送到 WxPusher
运行时间: 工作日 16:30
"""
import os
import sys
import requests
import datetime

WXPUSHER_APP_TOKEN = "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc"
WXPUSHER_TOPIC_IDS = [43351]
WXPUSHER_URL = "https://wxpusher.zjiecode.com/api/send/message"
TUSHARE_TOKEN = "3664fe220cb675ae1661e7ad96c51e2592a0ef72c93d29da3d65b692"

POSITIONS = {
    "平安证券": [
        {"code": "603392", "name": "万泰生物", "shares": 81500, "cost": 75.47},
        {"code": "002647", "name": "ST仁东",   "shares": 300,   "cost": 6.70},
        {"code": "001212", "name": "中旗新材", "shares": 462235, "cost": 53.88},
        {"code": "002465", "name": "海格通信", "shares": 100,   "cost": 12.71},
        {"code": "002819", "name": "东方中科", "shares": 154100, "cost": 29.11},
        {"code": "002941", "name": "新疆交建", "shares": 100,   "cost": 11.13},
        {"code": "600416", "name": "湘电股份", "shares": 100,   "cost": 13.04},
    ],
    "兴证国际": [
        {"code": "600326", "name": "西藏天路", "shares": 77200,  "cost": 11.561},
        {"code": "600897", "name": "厦门空港", "shares": 200,   "cost": 18.010},
        {"code": "001212", "name": "中旗新材", "shares": 1612700, "cost": 52.180},
        {"code": "002174", "name": "游族网络", "shares": 800,   "cost": 12.400},
        {"code": "002465", "name": "海格通信", "shares": 200,   "cost": 15.153},
        {"code": "002819", "name": "东方中科", "shares": 989000, "cost": 28.296},
    ],
}


def fetch_prices():
    price_map = {}
    print(f"获取 {sum(len(v) for v in POSITIONS.values())} 只股票最新行情...")
    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()

        today = datetime.date.today()
        weekday = today.weekday()
        if weekday >= 5:
            trade_date = (today - datetime.timedelta(days=weekday - 4)).strftime('%Y%m%d')
        else:
            trade_date = today.strftime('%Y%m%d')

        all_codes = []
        for items in POSITIONS.values():
            for item in items:
                all_codes.append(item['code'])

        codes_str = ','.join(all_codes)
        print(f"  tushare 查询日期: {trade_date}")
        df = pro.daily(trade_date=trade_date)
        if df.empty:
            df = pro.daily(trade_date=(today - datetime.timedelta(days=1)).strftime('%Y%m%d'))
            print(f"  当日无数据，使用前一日: {(today - datetime.timedelta(days=1)).strftime('%Y-%m-%d')}")

        df_ts_code = df.copy()
        df_ts_code['simple_code'] = df_ts_code['ts_code'].str[:6]
        for items in POSITIONS.values():
            for item in items:
                code = item['code']
                match = df_ts_code[df_ts_code['simple_code'] == code]
                if not match.empty:
                    price = float(match.iloc[0]['close'])
                    price_map[code] = price
                    print(f"  {code} {item['name']}: {price}")
                else:
                    print(f"  ⚠️ {code} {item['name']}: 未找到行情数据")

        if not price_map:
            print("  尝试使用备用接口...")
            df_old = ts.get_today_all()
            for items in POSITIONS.values():
                for item in items:
                    code = item['code']
                    match = df_old[df_old['code'] == code]
                    if not match.empty:
                        price = float(match.iloc[0]['trade'])
                        price_map[code] = price
                        print(f"  {code} {item['name']}: {price}")
    except Exception as e:
        print(f"  ❌ 获取失败: {e}")
    return price_map


def build_content(price_map):
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    weekday = ["周一","周二","周三","周四","周五","周六","周日"][datetime.datetime.now().weekday()]
    all_cost = all_market = 0.0

    for account, items in POSITIONS.items():
        acct_cost = acct_market = 0.0
        for item in items:
            price = price_map.get(item['code'], item['cost'])
            cost_val = item['cost'] * item['shares']
            mkt_val = price * item['shares']
            pnl = mkt_val - cost_val
            pct = (pnl / cost_val * 100) if cost_val else 0
            acct_cost += cost_val
            acct_market += mkt_val
        all_cost += acct_cost
        all_market += acct_market

    total_pnl = all_market - all_cost
    total_pct = (total_pnl / all_cost * 100) if all_cost else 0
    sign = "+" if total_pnl >= 0 else ""
    arrow = "🔴" if total_pnl >= 0 else "🟢"

    lines = [f"**📊 持仓盈亏汇总 ({today} {weekday})**", ""]
    lines.append(f"**{arrow} 总盈亏: {sign}{total_pnl/10000:.0f}万元  ({sign}{total_pct:.2f}%)**")
    lines.append(f"总成本 {all_cost/10000:.0f}万 → 总市值 {all_market/10000:.0f}万")
    lines.append("")

    for account, items in POSITIONS.items():
        is_xingzheng = "兴证" in account
        if is_xingzheng:
            lines.append("---")

        sorted_items = []
        for item in items:
            price = price_map.get(item['code'], item['cost'])
            mkt_val = price * item['shares']
            sorted_items.append((price, item, mkt_val))
        sorted_items.sort(key=lambda x: x[2], reverse=True)

        lines.append(f"**<span style=\"color:red; font-size:20px;\">{account}</span>**")
        lines.append("")
        max_price_change = max(len(f"{item['cost']:.2f}\u2192{price_map.get(item['code'], item['cost']):.2f}") for price, item, mkt_val in sorted_items) if sorted_items else 15
        max_pnl = max(len(f"{'+' if price*item['shares']-item['cost']*item['shares'] >= 0 else ''}{price*item['shares']-item['cost']*item['shares']:,.0f}") for price, item, mkt_val in sorted_items) if sorted_items else 10
        for price, item, mkt_val in sorted_items:
            cost_val = item['cost'] * item['shares']
            pnl = mkt_val - cost_val
            pct = (pnl / cost_val * 100) if cost_val else 0
            sign_item = "+" if pnl >= 0 else ""
            lines.append(f"**{item['name']}**\u00a0\u00a0**|**\u00a0\u00a0{mkt_val:,.0f}")
            pnl_color = "red" if pnl >= 0 else "green"
            price_change = f"{item['cost']:.2f}\u2192{price:.2f}"
            pnl_str = f"{sign_item}{pnl:,.0f}"
            pct_str = f"{sign_item}{pct:.2f}%"
            lines.append(f"<font color=\"{pnl_color}\">{price_change}{'\u00a0'*(max_price_change-len(price_change))}\u00a0\u00a0**|**\u00a0\u00a0{pnl_str}{'\u00a0'*(max_pnl-len(pnl_str))}\u00a0\u00a0**|**\u00a0\u00a0{pct_str}</font>")
        lines.append("")

    summary = f"{arrow} 平安+兴证持仓 {sign}{total_pnl/10000:.0f}万元 ({sign}{total_pct:.2f}%)"
    return "\n".join(lines), summary


def send_wx(content, summary):
    try:
        session = requests.Session()
        session.trust_env = False
        resp = session.post(WXPUSHER_URL, json={
            "appToken": WXPUSHER_APP_TOKEN,
            "content": content,
            "summary": summary[:100],
            "contentType": 3,
            "topicIds": WXPUSHER_TOPIC_IDS
        }, timeout=10)
        result = resp.json()
        if result.get('code') == 1000:
            print(f"微信推送成功: {summary}")
        else:
            print(f"微信推送失败: {result.get('msg')}")
    except Exception as e:
        print(f"微信推送异常: {e}")


def main():
    now = datetime.datetime.now()
    print(f"持仓汇总推送 ({now.strftime('%Y-%m-%d %H:%M')})")
    print("=" * 60)
    price_map = fetch_prices()
    print()
    content, summary = build_content(price_map)
    print(content)
    print()
    send_wx(content, summary)
    print("=" * 60)
    print("完成")


if __name__ == "__main__":
    main()
