#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI行业资金流向AI分析师
整合新浪财经行业数据获取、智能分析和AI深度解读功能
结合多时间维度资金流向分析

Author: AI Assistant
Date: 2024-12-02
"""

# =============================================================================
# 导入模块
# =============================================================================

# 标准库导入
import os
import time
import warnings
import json
from datetime import datetime
from io import StringIO

# 第三方库导入
import requests
import pandas as pd
import numpy as np
import pytz


# =============================================================================
# 配置常量
# =============================================================================

# ---------------- DeepSeek API 配置 ----------------
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-v4-flash"

# ---------------- 推送配置 (WxPusher) ----------------
WXPUSHER_APP_TOKEN = os.getenv("WXPUSHER_APP_TOKEN", "AT_UHus2F8p0yjnG6XvGEDzdCp5GkwvLdkc")
WXPUSHER_TOPIC_IDS = [42353]  # 目标主题 ID 列表42540备用
WXPUSHER_URL = "https://wxpusher.zjiecode.com/api/send/message"

# ---------------- 时区配置 ----------------
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# =============================================================================
# 工具函数
# =============================================================================

def get_beijing_time():
    """
    获取北京时间
    
    Returns:
        datetime: 北京时间对象
    """
    return datetime.now(BEIJING_TZ)

# =============================================================================
# 数据获取模块
# =============================================================================

class DataFetcher:
    """
    数据获取类 - 专注于证监会行业资金流向数据获取
    """
    
    def __init__(self):
        """初始化数据获取器"""
        self.base_url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/MoneyFlow.ssl_bkzjlxt"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': 'https://vip.stock.finance.sina.com.cn/moneyflow/',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        # 创建session以避免代理问题
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.trust_env = False
    
    def fetch_industry_flow_data(self, page=1, num=20, sort='cate_id', asc=1, fenlei=2):
        """
        获取证监会行业资金流向数据
        
        Args:
            page: 页码，默认1
            num: 每页数量，默认20
            sort: 排序字段，默认cate_id（行业代码）
            asc: 排序方向，0降序，1升序，默认1
            fenlei: 分类，2表示获取行业资金流向数据
            
        Returns:
            dict: 返回的行业JSON数据，失败返回None
        """
        url = self.base_url
        params = {
            'page': page,
            'num': num,
            'sort': sort,
            'asc': asc,
            'fenlei': fenlei
        }
        
        try:
            print(f"正在获取第{page}页证监会行业资金流向数据...")
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            response.encoding = 'gbk'  # 新浪财经使用GBK编码
            
            # 解析JSON数据
            content = response.text.strip()
            if content.startswith('[') and content.endswith(']'):
                data = json.loads(content)
            else:
                # 处理可能的JSONP格式
                start = content.find('(') + 1
                end = content.rfind(')')
                if start > 0 and end > start:
                    data = json.loads(content[start:end])
                else:
                    data = json.loads(content)
            
            print(f"第{page}页获取成功，共{len(data)}条数据")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"获取第{page}页数据出错: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            print(f"解析第{page}页JSON数据出错: {str(e)}")
            return None
        except Exception as e:
            print(f"第{page}页数据处理出错: {str(e)}")
            return None
    
    def parse_industry_flow_data(self, raw_data):
        """
        解析证监会行业资金流向数据
        
        Args:
            raw_data: 原始行业JSON数据
            
        Returns:
            list: 解析后的行业数据列表
        """
        if not raw_data:
            return []
        
        parsed_data = []
        for item in raw_data:
            try:
                # 解析行业数据字段，适配多时间维度
                parsed_item = {
                    '行业代码': item.get('category', ''),
                    '行业名称': item.get('name', ''),
                    '3日净流入': float(item.get('netamount_3', 0)),
                    '3日净流入占比': float(item.get('ratioamount_3', 0)),
                    '3日平均涨跌幅': float(item.get('avg_changeratio_3', 0)),
                    '3日流入流出比': float(item.get('r0x_ratio_3', 0)),
                    '5日净流入': float(item.get('netamount_5', 0)),
                    '5日净流入占比': float(item.get('ratioamount_5', 0)),
                    '5日平均涨跌幅': float(item.get('avg_changeratio_5', 0)),
                    '5日流入流出比': float(item.get('r0x_ratio_5', 0)),
                    '10日净流入': float(item.get('netamount_10', 0)),
                    '10日净流入占比': float(item.get('ratioamount_10', 0)),
                    '10日平均涨跌幅': float(item.get('avg_changeratio_10', 0)),
                    '10日流入流出比': float(item.get('r0x_ratio_10', 0)),
                    '数据更新时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                parsed_data.append(parsed_item)
                
            except (ValueError, TypeError) as e:
                print(f"解析数据项时出错: {str(e)}, 数据: {item}")
                continue
        
        return parsed_data
    
    def collect_batch_data(self, total_pages=8, page_size=20):
        """
        批量获取多页证监会行业资金流向数据
        
        Args:
            total_pages: 总页数，默认8页（完整数据）
            page_size: 每页大小，默认20条
            
        Returns:
            list: 合并后的所有行业数据
        """
        all_data = []
        
        print(f"=== 开始批量获取证监会行业资金流向数据 ===")
        print(f"目标: 获取{total_pages}页行业数据，每页{page_size}条")
        
        for page in range(1, total_pages + 1):
            print(f"\n--- 获取第{page}页数据 ---")
            
            # 获取原始数据
            raw_data = self.fetch_industry_flow_data(page=page, num=page_size)
            if raw_data:
                # 解析数据
                parsed_data = self.parse_industry_flow_data(raw_data)
                if parsed_data:
                    all_data.extend(parsed_data)
                    print(f"第{page}页解析成功，获得{len(parsed_data)}条数据")
                else:
                    print(f"第{page}页数据解析失败")
            else:
                print(f"第{page}页数据获取失败")
            
            # 添加间隔，避免请求过于频繁
            if page < total_pages:
                print("等待1秒...")
                time.sleep(1)
        
        print(f"\n=== 批量获取完成 ===")
        print(f"总计获得 {len(all_data)} 条数据")
        
        return all_data

# =============================================================================
# 数据分析模块
# =============================================================================

class DataAnalyzer:
    """
    数据分析类 - 专注于证监会行业资金流向数据分析
    """
    
    @staticmethod
    def save_to_csv(data, filename=None):
        """
        保存数据到CSV文件
        
        Args:
            data: 要保存的数据
            filename: 文件名，默认自动生成
            
        Returns:
            str: 保存的文件名，失败返回None
        """
        if not data:
            print("没有数据可保存")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"AI证监会行业资金流向数据_{timestamp}.csv"
        
        try:
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"数据已保存到 {filename}")
            return filename
        except Exception as e:
            print(f"保存CSV文件出错: {str(e)}")
            return None
    
    @staticmethod
    def get_industry_summary(data):
        """
        获取证监会行业资金流向概况统计
        
        Args:
            data: 行业数据列表
            
        Returns:
            dict: 汇总统计数据
        """
        if not data:
            return {}
        
        df = pd.DataFrame(data)
        
        # 基础统计
        total_industries = len(df)
        positive_3d = len(df[df['3日平均涨跌幅'] > 0])
        positive_5d = len(df[df['5日平均涨跌幅'] > 0])
        positive_10d = len(df[df['10日平均涨跌幅'] > 0])
        
        # 净流入统计
        total_inflow_3d = df['3日净流入'].sum()
        total_inflow_5d = df['5日净流入'].sum()
        total_inflow_10d = df['10日净流入'].sum()
        
        # 流入流出比统计
        avg_ratio_3d = df['3日流入流出比'].mean()
        avg_ratio_5d = df['5日流入流出比'].mean()
        avg_ratio_10d = df['10日流入流出比'].mean()
        
        # 净流入前10（多时间维度）
        top_inflow_3d = df.nlargest(10, '3日净流入')[['行业代码', '行业名称', '3日净流入', '3日平均涨跌幅']].to_dict('records')
        top_inflow_5d = df.nlargest(10, '5日净流入')[['行业代码', '行业名称', '5日净流入', '5日平均涨跌幅']].to_dict('records')
        top_inflow_10d = df.nlargest(10, '10日净流入')[['行业代码', '行业名称', '10日净流入', '10日平均涨跌幅']].to_dict('records')
        
        summary = {
            'total_industries': total_industries,
            'positive_3d_count': positive_3d,
            'positive_5d_count': positive_5d,
            'positive_10d_count': positive_10d,
            'total_inflow_3d_billion': total_inflow_3d / 1e8,
            'total_inflow_5d_billion': total_inflow_5d / 1e8,
            'total_inflow_10d_billion': total_inflow_10d / 1e8,
            'avg_ratio_3d': avg_ratio_3d,
            'avg_ratio_5d': avg_ratio_5d,
            'avg_ratio_10d': avg_ratio_10d,
            'top_inflow_3d': top_inflow_3d,
            'top_inflow_5d': top_inflow_5d,
            'top_inflow_10d': top_inflow_10d
        }
        
        return summary
    
    @staticmethod
    def analyze_market_structure(data):
        """
        对证监会行业资金流向数据进行结构化分析
        重点分析多时间维度的行业轮动和资金趋势
        
        Args:
            data: 行业数据列表
            
        Returns:
            dict: 结构化分析结果
        """
        if not data:
            return None
        
        df = pd.DataFrame(data)
        
        analysis_result = {
            'summary': {},
            'flow_trends': {},
            'sector_rotation': {},
            'risk_industries': {},
            'hot_industries': {}
        }
        
        # 基础统计
        total_industries = len(df)
        positive_3d = len(df[df['3日平均涨跌幅'] > 0])
        positive_5d = len(df[df['5日平均涨跌幅'] > 0])
        positive_10d = len(df[df['10日平均涨跌幅'] > 0])
        
        # 净流入统计
        total_inflow_3d = df['3日净流入'].sum()
        total_inflow_5d = df['5日净流入'].sum()
        total_inflow_10d = df['10日净流入'].sum()
        
        # 流入流出比统计
        avg_ratio_3d = df['3日流入流出比'].mean()
        avg_ratio_5d = df['5日流入流出比'].mean()
        avg_ratio_10d = df['10日流入流出比'].mean()
        
        # 基础分析汇总
        analysis_result['summary'] = {
            'total_industries': total_industries,
            'positive_3d_count': positive_3d,
            'positive_5d_count': positive_5d,
            'positive_10d_count': positive_10d,
            'total_inflow_3d_billion': total_inflow_3d / 1e8,
            'total_inflow_5d_billion': total_inflow_5d / 1e8,
            'total_inflow_10d_billion': total_inflow_10d / 1e8,
            'avg_ratio_3d': avg_ratio_3d,
            'avg_ratio_5d': avg_ratio_5d,
            'avg_ratio_10d': avg_ratio_10d
        }
        
        # 资金流向趋势分析
        big_inflow_3d = df[df['3日净流入'] > 5e7]  # 3日净流入超5000万
        big_inflow_5d = df[df['5日净流入'] > 5e7]  # 5日净流入超5000万
        big_inflow_10d = df[df['10日净流入'] > 5e7]  # 10日净流入超5000万
        
        analysis_result['flow_trends'] = {
            'big_inflow_3d_count': len(big_inflow_3d),
            'big_inflow_5d_count': len(big_inflow_5d),
            'big_inflow_10d_count': len(big_inflow_10d),
            'top_inflow_3d': big_inflow_3d.nlargest(10, '3日净流入')[['行业代码', '行业名称', '3日净流入', '3日平均涨跌幅']].to_dict('records'),
            'top_inflow_5d': big_inflow_5d.nlargest(10, '5日净流入')[['行业代码', '行业名称', '5日净流入', '5日平均涨跌幅']].to_dict('records'),
            'top_inflow_10d': big_inflow_10d.nlargest(10, '10日净流入')[['行业代码', '行业名称', '10日净流入', '10日平均涨跌幅']].to_dict('records')
        }
        
        # 行业轮动分析
        # 计算行业强度指标
        df['3日强度'] = df['3日净流入'] * df['3日流入流出比'] * (1 + df['3日平均涨跌幅'])
        df['5日强度'] = df['5日净流入'] * df['5日流入流出比'] * (1 + df['5日平均涨跌幅'])
        df['10日强度'] = df['10日净流入'] * df['10日流入流出比'] * (1 + df['10日平均涨跌幅'])
        
        # 短期强势行业（3日）
        strong_3d = df.nlargest(15, '3日强度')[['行业代码', '行业名称', '3日强度', '3日净流入', '3日流入流出比', '3日平均涨跌幅']].to_dict('records')
        
        # 中期强势行业（5日）
        strong_5d = df.nlargest(15, '5日强度')[['行业代码', '行业名称', '5日强度', '5日净流入', '5日流入流出比', '5日平均涨跌幅']].to_dict('records')
        
        # 长期强势行业（10日）
        strong_10d = df.nlargest(15, '10日强度')[['行业代码', '行业名称', '10日强度', '10日净流入', '10日流入流出比', '10日平均涨跌幅']].to_dict('records')
        
        analysis_result['sector_rotation'] = {
            'strong_3d': strong_3d,
            'strong_5d': strong_5d,
            'strong_10d': strong_10d
        }
        
        # 风险行业识别
        # 大额流出行业
        big_outflow_3d = df[df['3日净流入'] < -5e7]  # 3日净流出超5000万
        big_outflow_5d = df[df['5日净流入'] < -5e7]  # 5日净流出超5000万
        big_outflow_10d = df[df['10日净流入'] < -5e7]  # 10日净流出超5000万
        
        # 负流入流出比行业（流出大于流入）
        negative_ratio_3d = df[df['3日流入流出比'] < 0]
        negative_ratio_5d = df[df['5日流入流出比'] < 0]
        negative_ratio_10d = df[df['10日流入流出比'] < 0]
        
        analysis_result['risk_industries'] = {
            'big_outflow_3d_count': len(big_outflow_3d),
            'big_outflow_5d_count': len(big_outflow_5d),
            'big_outflow_10d_count': len(big_outflow_10d),
            'negative_ratio_3d_count': len(negative_ratio_3d),
            'negative_ratio_5d_count': len(negative_ratio_5d),
            'negative_ratio_10d_count': len(negative_ratio_10d),
            'big_outflow_3d': big_outflow_3d[['行业代码', '行业名称', '3日净流入', '3日流入流出比']].to_dict('records'),
            'big_outflow_5d': big_outflow_5d[['行业代码', '行业名称', '5日净流入', '5日流入流出比']].to_dict('records'),
            'big_outflow_10d': big_outflow_10d[['行业代码', '行业名称', '10日净流入', '10日流入流出比']].to_dict('records')
        }
        
        # 热门行业分析
        # 高流入流出比行业（资金关注度高）
        hot_ratio_3d = df[df['3日流入流出比'] > 1.5]  # 流入是流出的1.5倍以上
        hot_ratio_5d = df[df['5日流入流出比'] > 1.5]
        hot_ratio_10d = df[df['10日流入流出比'] > 1.5]
        
        # 大额流入行业（资金规模大）
        hot_volume_3d = df[df['3日净流入'] > 2e8]  # 3日净流入超2亿
        hot_volume_5d = df[df['5日净流入'] > 2e8]  # 5日净流入超2亿
        hot_volume_10d = df[df['10日净流入'] > 2e8]  # 10日净流入超2亿
        
        analysis_result['hot_industries'] = {
            'hot_ratio_3d_count': len(hot_ratio_3d),
            'hot_ratio_5d_count': len(hot_ratio_5d),
            'hot_ratio_10d_count': len(hot_ratio_10d),
            'hot_volume_3d_count': len(hot_volume_3d),
            'hot_volume_5d_count': len(hot_volume_5d),
            'hot_volume_10d_count': len(hot_volume_10d),
            'hot_ratio_3d': hot_ratio_3d[['行业代码', '行业名称', '3日流入流出比', '3日净流入']].to_dict('records'),
            'hot_ratio_5d': hot_ratio_5d[['行业代码', '行业名称', '5日流入流出比', '5日净流入']].to_dict('records'),
            'hot_ratio_10d': hot_ratio_10d[['行业代码', '行业名称', '10日流入流出比', '10日净流入']].to_dict('records')
        }
        
        return analysis_result

# =============================================================================
# AI分析模块
# =============================================================================

class AIAnalyzer:
    """
    AI分析类 - 专注于证监会行业资金流向AI智能分析
    """
    
    @staticmethod
    def prepare_ai_context(data, analysis_result):
        """
        为AI准备结构化的分析上下文
        重点突出证监会行业多时间维度分析
        
        Args:
            data: 原始数据
            analysis_result: 结构化分析结果
            
        Returns:
            str: AI分析的上下文文本
        """
        if not analysis_result:
            return "数据分析失败，无法生成报告。"
        
        summary = analysis_result['summary']
        flow_trends = analysis_result['flow_trends']
        sector_rotation = analysis_result['sector_rotation']
        risk_industries = analysis_result['risk_industries']
        hot_industries = analysis_result['hot_industries']
        
        # 构建CSV内容用于AI分析
        df = pd.DataFrame(data)
        csv_content = df.to_csv(index=False, encoding='utf-8-sig')
        
        context = f"""
===========================================
🚀 证监会行业资金流向数据 - AI智能分析版
===========================================

💰 【市场整体概况】
- 总行业数: {summary['total_industries']}个
- 3日上涨行业: {summary['positive_3d_count']}个 ({summary['positive_3d_count']/summary['total_industries']*100:.1f}%)
- 5日上涨行业: {summary['positive_5d_count']}个 ({summary['positive_5d_count']/summary['total_industries']*100:.1f}%)
- 10日上涨行业: {summary['positive_10d_count']}个 ({summary['positive_10d_count']/summary['total_industries']*100:.1f}%)
- 3日总净流入: {summary['total_inflow_3d_billion']:.2f}亿元
- 5日总净流入: {summary['total_inflow_5d_billion']:.2f}亿元
- 10日总净流入: {summary['total_inflow_10d_billion']:.2f}亿元
- 3日平均流入流出比: {summary['avg_ratio_3d']:.3f}
- 5日平均流入流出比: {summary['avg_ratio_5d']:.3f}
- 10日平均流入流出比: {summary['avg_ratio_10d']:.3f}

🏆 【短期强势行业TOP10（3日）】"""
        
        # 短期强势行业分析
        for i, industry in enumerate(sector_rotation['strong_3d'][:10], 1):
            context += f"""
{i}. {industry['行业名称']}({industry['行业代码']})
   💰 净流入: {industry['3日净流入']/1e8:.2f}亿元
   📈 平均涨幅: {industry['3日平均涨跌幅']*100:.2f}%
   🔄 流入流出比: {industry['3日流入流出比']:.2f}
   ⭐ 强度指数: {industry['3日强度']/1e8:.2f}"""
        
        context += f"""

🎯 【中期强势行业TOP10（5日）】"""
        for i, industry in enumerate(sector_rotation['strong_5d'][:10], 1):
            context += f"""
{i}. {industry['行业名称']}({industry['行业代码']})
   💰 净流入: {industry['5日净流入']/1e8:.2f}亿元
   📈 平均涨幅: {industry['5日平均涨跌幅']*100:.2f}%
   🔄 流入流出比: {industry['5日流入流出比']:.2f}
   ⭐ 强度指数: {industry['5日强度']/1e8:.2f}"""
        
        context += f"""

🚀 【长期强势行业TOP10（10日）】"""
        for i, industry in enumerate(sector_rotation['strong_10d'][:10], 1):
            context += f"""
{i}. {industry['行业名称']}({industry['行业代码']})
   💰 净流入: {industry['10日净流入']/1e8:.2f}亿元
   📈 平均涨幅: {industry['10日平均涨跌幅']*100:.2f}%
   🔄 流入流出比: {industry['10日流入流出比']:.2f}
   ⭐ 强度指数: {industry['10日强度']/1e8:.2f}"""
        
        context += f"""

🔥 【大额流入行业汇总】
📊 3日大额流入（超5000万）: {flow_trends['big_inflow_3d_count']}个"""
        
        for i, industry in enumerate(flow_trends['top_inflow_3d'][:5], 1):
            context += f"""
{i}. {industry['行业名称']}({industry['行业代码']}) - {industry['3日净流入']/1e8:.2f}亿元"""
        
        context += f"""
📊 5日大额流入（超5000万）: {flow_trends['big_inflow_5d_count']}个"""
        for i, industry in enumerate(flow_trends['top_inflow_5d'][:5], 1):
            context += f"""
{i}. {industry['行业名称']}({industry['行业代码']}) - {industry['5日净流入']/1e8:.2f}亿元"""
        
        context += f"""
📊 10日大额流入（超5000万）: {flow_trends['big_inflow_10d_count']}个"""
        for i, industry in enumerate(flow_trends['top_inflow_10d'][:5], 1):
            context += f"""
{i}. {industry['行业名称']}({industry['行业代码']}) - {industry['10日净流入']/1e8:.2f}亿元"""
        
        context += f"""

⚠️ 【风险行业警示】
📉 3日大额流出（超5000万）: {risk_industries['big_outflow_3d_count']}个"""
        if risk_industries['big_outflow_3d']:
            for i, industry in enumerate(risk_industries['big_outflow_3d'][:5], 1):
                context += f"""
{i}. {industry['行业名称']}({industry['行业代码']}) - 净流出: {abs(industry['3日净流入'])/1e8:.2f}亿元"""
        else:
            context += "\n无大额流出行业"
        
        context += f"""
📉 5日大额流出（超5000万）: {risk_industries['big_outflow_5d_count']}个"""
        if risk_industries['big_outflow_5d']:
            for i, industry in enumerate(risk_industries['big_outflow_5d'][:5], 1):
                context += f"""
{i}. {industry['行业名称']}({industry['行业代码']}) - 净流出: {abs(industry['5日净流入'])/1e8:.2f}亿元"""
        else:
            context += "\n无大额流出行业"
        
        context += f"""
📉 10日大额流出（超5000万）: {risk_industries['big_outflow_10d_count']}个"""
        if risk_industries['big_outflow_10d']:
            for i, industry in enumerate(risk_industries['big_outflow_10d'][:5], 1):
                context += f"""
{i}. {industry['行业名称']}({industry['行业代码']}) - 净流出: {abs(industry['10日净流入'])/1e8:.2f}亿元"""
        else:
            context += "\n无大额流出行业"
        
        context += f"""

🌟 【行业轮动洞察】
- 短期热点: {sector_rotation['strong_3d'][0]['行业名称'] if sector_rotation['strong_3d'] else '无数据'}
- 中期热点: {sector_rotation['strong_5d'][0]['行业名称'] if sector_rotation['strong_5d'] else '无数据'}
- 长期热点: {sector_rotation['strong_10d'][0]['行业名称'] if sector_rotation['strong_10d'] else '无数据'}

===========================================
[完整CSV数据 - 用于深度分析]
{csv_content}
===========================================
"""
        
        # ========== 新增：打印AI上下文信息 ==========
        print("📊 AI分析上下文构建完成:")
        print(f"   - 上下文总字符数: {len(context):,} 字符")
        print(f"   - 上下文行数: {len(context.split(chr(10)))} 行")
        print(f"   - 行业总数: {summary['total_industries']} 个")
        print(f"   - 数据覆盖: 3日/5日/10日 多时间维度")
        print("="*50)
        print("📋 上下文内容预览:")
        print("-" * 50)
        print(context[:500] + "..." if len(context) > 500 else context)
        print("-" * 50)
        print("="*50)
        
        return context
    
    @staticmethod
    def call_ai_analysis(data, analysis_result):
        """
        调用DeepSeek进行证监会行业资金流向AI分析
        
        Args:
            data: 原始数据
            analysis_result: 结构化分析结果
            
        Returns:
            str: AI分析报告
        """
        if not DEEPSEEK_API_KEY or "sk-" not in DEEPSEEK_API_KEY:
            print("[Warning] 未配置 DEEPSEEK_API_KEY，跳过 AI 分析。")
            return "未配置 API Key，无法生成 AI 报告。"
        
        # 准备AI上下文
        context = AIAnalyzer.prepare_ai_context(data, analysis_result)
        
        # 构建专业提示词
        prompt = f"""
你是一位专注于中国A股市场证监会行业分类资金流向分析的资深金融分析师。
我将为你提供最新的证监会行业资金流向数据，包含3日、5日、10日多时间维度的完整分析。

{context}

请根据提供的数据生成一份全面的证监会行业资金流向AI分析报告，涵盖以下方面：
💰 **资金流向趋势分析**：分析3日、5日、10日净流入/净流出情况，判断短期、中期、长期资金趋势  
🔥 **行业轮动分析**：识别短期、中期、长期强势行业，分析行业轮动规律  
📈 **行业强度排名**：基于多时间维度综合评分，识别最强行业和最弱行业  
⚠️ **风险行业警示**：对于大额流出、负流入流出比的行业给出风险提示  
🎯 **投资策略建议**：基于行业资金流向分析，给出短线、中长线的行业投资建议  
📊 **市场情绪判断**：通过行业资金流向数据判断当前市场整体情绪和行业偏好  
🌊 **行业轮动洞察**：分析行业轮动的短期、中期、长期逻辑

**重要要求**：
- 请直接输出中文报告，确保分析深入且具有实际指导价值
- **不要使用表格格式**，保持报告的简洁性和易读性
- **报告内容请严格控制在3500字以内**
- 重点关注多时间维度的对比分析和行业轮动规律
- 使用Markdown格式，结构清晰，便于阅读
"""

        # ========== 新增：打印完整提示词功能 ==========
        print("\n" + "="*80)
        print("🚀 准备发送给 DeepSeek API 的完整提示词:")
        print("="*80)
        print("\n📋 【系统提示词】:")
        print("你是一位专业的A股证监会行业资金流向分析师。")
        print("\n📝 【用户提示词】:")
        print(prompt)
        print("\n" + "="*80)
        print(f"📊 【提示词统计信息】:")
        print(f"   - 总字符数: {len(prompt):,} 字符")
        print(f"   - 行数: {len(prompt.split(chr(10)))} 行")
        print(f"   - 预计令牌数: ~{len(prompt.split()) * 1.3:.0f} tokens")
        print("="*80)
        
        print("\n=== 向 DeepSeek API 发送请求 ===")
        
        # 使用requests直接调用DeepSeek API
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "你是一位专业的A股证监会行业资金流向分析师。"},
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

# =============================================================================
# 报告生成模块
# =============================================================================

class ReportGenerator:
    """
    报告生成类 - 专注于证监会行业资金流向分析报告生成
    """
    
    @staticmethod
    def generate_analysis_report(data, ai_report, filename=None):
        """
        生成证监会行业资金流向AI分析报告文件
        
        Args:
            data: 原始数据
            ai_report: AI分析报告
            filename: 文件名，默认自动生成
            
        Returns:
            str: 保存的文件名，失败返回None
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"AI证监会行业资金流向分析报告_{timestamp}.md"
        
        try:
            # 获取市场概况
            summary = DataAnalyzer.get_industry_summary(data)
            
            # 生成报告内容
            report_content = f"""# 证监会行业资金流向AI分析报告

## 📊 行业整体概况
- **数据获取时间**: {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}
- **行业总数**: {summary['total_industries']}个
- **3日上涨行业**: {summary['positive_3d_count']}个 ({summary['positive_3d_count']/summary['total_industries']*100:.1f}%)
- **5日上涨行业**: {summary['positive_5d_count']}个 ({summary['positive_5d_count']/summary['total_industries']*100:.1f}%)
- **10日上涨行业**: {summary['positive_10d_count']}个 ({summary['positive_10d_count']/summary['total_industries']*100:.1f}%)
- **3日总净流入**: {summary['total_inflow_3d_billion']:.2f}亿元
- **5日总净流入**: {summary['total_inflow_5d_billion']:.2f}亿元
- **10日总净流入**: {summary['total_inflow_10d_billion']:.2f}亿元
- **3日平均流入流出比**: {summary['avg_ratio_3d']:.3f}
- **5日平均流入流出比**: {summary['avg_ratio_5d']:.3f}
- **10日平均流入流出比**: {summary['avg_ratio_10d']:.3f}

## 💰 净流入前10行业（3日）
"""
            for i, stock in enumerate(summary['top_inflow_3d'], 1):
                report_content += f"{i}. **{stock['行业名称']}**({stock['行业代码']}) - 净流入: {stock['3日净流入']/1e8:.2f}亿元, 涨跌幅: {stock['3日平均涨跌幅']*100:.2f}%\n"
            
            report_content += f"""
## 💰 净流入前10行业（5日）
"""
            for i, stock in enumerate(summary['top_inflow_5d'], 1):
                report_content += f"{i}. **{stock['行业名称']}**({stock['行业代码']}) - 净流入: {stock['5日净流入']/1e8:.2f}亿元, 涨跌幅: {stock['5日平均涨跌幅']*100:.2f}%\n"
            
            report_content += f"""
## 💰 净流入前10行业（10日）
"""
            for i, stock in enumerate(summary['top_inflow_10d'], 1):
                report_content += f"{i}. **{stock['行业名称']}**({stock['行业代码']}) - 净流入: {stock['10日净流入']/1e8:.2f}亿元, 涨跌幅: {stock['10日平均涨跌幅']*100:.2f}%\n"
            
            report_content += f"""
## 🤖 AI智能分析报告

{ai_report}

---
*报告生成时间: {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}*
*数据来源: 新浪财经证监会行业资金流向数据*
*分析工具: DeepSeek AI*
"""
            
            # 保存报告
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            print(f"AI分析报告已保存到: {filename}")
            return filename
            
        except Exception as e:
            print(f"生成分析报告出错: {str(e)}")
            return None

# =============================================================================
# 推送功能模块
# =============================================================================

class PushNotifier:
    """
    推送通知类 - 专注于微信推送功能
    """
    
    @staticmethod
    def send_push(title, content, url=None):
        """
        使用 WxPusher 推送消息
        
        Args:
            title: 推送标题
            content: 推送内容
            url: 推送链接
            
        Returns:
            bool: 推送是否成功
        """
        print("\n" + "="*20 + f" PUSH: {title} " + "="*20)
        print("正在发送 WxPusher 推送...")
        print("="*50 + "\n")
        
        payload = {
            "appToken": WXPUSHER_APP_TOKEN,
            "content": content,
            "summary": title,
            "contentType": 3,  # 3 表示 Markdown 格式
            "topicIds": WXPUSHER_TOPIC_IDS,
            "url": url,
            "verifyPay": False,
            "selfUid": "",
            "showPushType": 1
        }

        try:
            response = requests.post(WXPUSHER_URL, 
                                   json=payload, 
                                   headers={'Content-Type': 'application/json'},
                                   timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 1000:
                    print("✅ WxPusher 推送成功")
                    return True
                else:
                    print(f"❌ WxPusher 推送失败: {result.get('msg', '未知错误')}")
                    return False
            else:
                print(f"❌ HTTP请求失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 推送过程出错: {str(e)}")
            return False
    
    @staticmethod
    def generate_push_content(summary, csv_file, ai_report, full_report=False):
        """
        生成推送内容（只推送AI分析报告的markdown格式）
        
        Args:
            summary: 分析摘要数据
            csv_file: CSV数据文件路径
            ai_report: DeepSeek返回的AI分析报告内容
            full_report: 是否推送完整报告内容
            
        Returns:
            str: 推送内容
        """
        try:
            if ai_report:
                # 直接使用AI报告内容（已控制在3000字以内）
                content = ai_report
                return content
            elif csv_file is not None:
                # 如果有CSV文件但没有AI报告，显示基础信息
                basic_content = f"""证监会行业资金流向分析报告

📊 数据概况：
- 行业总数: {summary.get('total_industries', 0)}个
- 3日总净流入: {summary.get('total_inflow_3d_billion', 0):.2f}亿元  
- 5日总净流入: {summary.get('total_inflow_5d_billion', 0):.2f}亿元
- 10日总净流入: {summary.get('total_inflow_10d_billion', 0):.2f}亿元

📁 数据文件：{os.path.basename(csv_file)}
🕒 生成时间：{get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ AI分析生成失败，请检查API配置。"""
                return basic_content
            else:
                  # 既没有AI报告也没有CSV文件，显示最简信息
                  minimal_content = f"""证监会行业资金流向分析报告

📊 数据概况：
- 行业总数: {summary.get('total_industries', 0)}个
- 3日总净流入: {summary.get('total_inflow_3d_billion', 0):.2f}亿元  
- 5日总净流入: {summary.get('total_inflow_5d_billion', 0):.2f}亿元
- 10日总净流入: {summary.get('total_inflow_10d_billion', 0):.2f}亿元

🕒 生成时间：{get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ AI分析生成失败，请检查API配置。"""
                  return minimal_content
            
        except Exception as e:
            print(f"⚠️  生成推送内容失败: {str(e)}")
            # 如果生成失败，使用简化的错误提示
            error_content = f"""证监会行业资金流向AI分析报告

⚠️  内容生成失败: {str(e)}

🕒 生成时间：{get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}"""
            return error_content
    
    @staticmethod
    def push_analysis_results(summary, csv_file, ai_report, push_enabled=True, full_report=False):
        """
        推送分析结果
        
        Args:
            summary: 分析摘要数据
            csv_file: CSV数据文件路径
            ai_report: AI分析报告内容
            push_enabled: 是否启用推送
            full_report: 是否推送完整报告内容
        """
        if not push_enabled:
            print("📱 推送功能已禁用")
            return
        
        if not WXPUSHER_APP_TOKEN:
            print("⚠️  未配置 WXPUSHER_APP_TOKEN，跳过推送")
            return
        
        try:
            # 生成推送内容
            title = f"AI行业资金流向分析 - {get_beijing_time().strftime('%m月%d日')}"
            content = PushNotifier.generate_push_content(summary, csv_file, ai_report, full_report)
            
            # 设置URL (如果没有CSV文件则不设置URL)
            url = f"file://{os.path.abspath(csv_file)}" if csv_file else None
            
            # 发送推送
            success = PushNotifier.send_push(title, content, url)
            
            if success:
                if full_report:
                    print("🎉 完整分析报告推送完成")
                else:
                    print("🎉 分析结果推送完成")
            else:
                print("❌ 分析结果推送失败")
                
        except Exception as e:
            print(f"❌ 推送过程出错: {str(e)}")

# =============================================================================
# 主程序模块
# =============================================================================

class CSRCIndustryAIAnalyzer:
    """
    证监会行业资金流向AI分析师 - 主控制器
    整合数据获取、分析、AI处理和推送功能
    """
    
    def __init__(self):
        """初始化分析器"""
        self.data_fetcher = DataFetcher()
        self.data_analyzer = DataAnalyzer()
        self.ai_analyzer = AIAnalyzer()
        self.report_generator = ReportGenerator()
        self.push_notifier = PushNotifier()
    
    def run_analysis(self, total_pages=8, page_size=20, push_enabled=True):
        """
        运行完整的证监会行业资金流向分析流程
        
        Args:
            total_pages: 获取的数据页数
            page_size: 每页数据量
            push_enabled: 是否启用推送
            
        Returns:
            dict: 分析结果，包含文件路径等信息
        """
        results = {
            'data': None,
            'csv_file': None,
            'summary': None,
            'analysis_result': None,
            'ai_report': None,
            'report_file': None
        }
        
        print("=== 证监会行业资金流向AI分析师 ===")
        
        # 1. 获取数据（获取完整数据）
        print("\n=== 第一步：获取证监会行业资金流向数据 ===")
        results['data'] = self.data_fetcher.collect_batch_data(total_pages=total_pages, page_size=page_size)
        
        if not results['data']:
            print("❌ 行业数据获取失败，无法继续分析")
            return results
        
        # 2. 基础行业分析
        print("\n=== 第二步：基础行业市场分析 ===")
        results['summary'] = self.data_analyzer.get_industry_summary(results['data'])
        self._print_summary(results['summary'])
        
        # 3. 结构化分析
        print("\n=== 第三步：深度行业结构化分析 ===")
        results['analysis_result'] = self.data_analyzer.analyze_market_structure(results['data'])
        
        # 4. AI智能分析
        print("\n=== 第四步：AI智能行业分析 ===")
        results['ai_report'] = self.ai_analyzer.call_ai_analysis(results['data'], results['analysis_result'])
        
        if results['ai_report'] and not results['ai_report'].startswith("未配置"):
            print("✅ AI行业分析完成")
            print("AI行业分析结果:")
            print("-" * 50)
            print(results['ai_report'])
            print("-" * 50)
            
            print(f"\n🎉 行业分析完成！")
            print(f"📄 AI报告: DeepSeek返回的markdown格式分析报告")
            
            # 5. 推送分析结果（推送AI报告内容）
            if push_enabled:
                print("\n=== 第五步：推送DeepSeek分析报告 ===")
                self.push_notifier.push_analysis_results(
                    results['summary'], 
                    None,  # 不再需要CSV文件路径
                    results['ai_report'], 
                    push_enabled=True, 
                    full_report=True
                )
        else:
            print("❌ AI行业分析失败或未配置API")
        
        return results
    
    def _print_summary(self, summary):
        """打印分析摘要"""
        print("行业市场概况:")
        for key, value in summary.items():
            if not key.startswith('top_inflow'):
                print(f"  {key}: {value}")
        
        print("\n净流入前5行业（3日）:")
        for i, stock in enumerate(summary['top_inflow_3d'][:5], 1):
            print(f"  {i}. {stock['行业名称']}({stock['行业代码']}) - {stock['3日净流入']/1e8:.2f}亿元")

def main():
    """主函数 - 证监会行业资金流向数据获取与AI分析"""
    analyzer = CSRCIndustryAIAnalyzer()
    
    # 运行完整分析流程
    results = analyzer.run_analysis(
        total_pages=8,     # 获取8页完整数据
        page_size=20,      # 每页20条数据
        push_enabled=True  # 启用推送
    )
    
    return results

if __name__ == "__main__":
    main()