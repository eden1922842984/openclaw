#!/usr/bin/env python3
"""
东方财富网实时股票信息爬虫
使用方法: python3 eastmoney_crawler.py [股票代码]
示例: python3 eastmoney_crawler.py 605066
      python3 eastmoney_crawler.py        # 默认获取天正电器
"""

import requests
import re
import sys
from datetime import datetime

# 东方财富API
EASTMONEY_API = "http://push2.eastmoney.com/api/qt/stock/get"

def get_realtime_data(code, market="1"):
    """
    获取个股实时行情
    
    Args:
        code: 股票代码 (如 605288)
        market: 市场代码 (1=上海, 0=深圳)
    
    Returns:
        dict: 股票数据
    """
    fields = "f43,f44,f45,f46,f47,f48,f49,f50,f57,f58,f60,f107,f169,f170,f171"
    
    params = {
        "secid": f"{market}.{code}",
        "fields": fields,
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "fltt": "2",
        "invt": "2",
        "wbp2u": "|0|0|0|web"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://quote.eastmoney.com/"
    }
    
    try:
        resp = requests.get(EASTMONEY_API, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        j = resp.json()
        
        if j.get('data'):
            d = j['data']
            return {
                'name': d.get('f58', ''),
                'code': d.get('f57', ''),
                'price': d.get('f43', 0) / 100,
                'open': d.get('f60', 0) / 100,
                'high': d.get('f44', 0) / 100,
                'low': d.get('f45', 0) / 100,
                'close_prev': d.get('f60', 0) / 100,
                'volume': d.get('f48', 0),
                'amount': d.get('f49', 0),
                'chg_pct': d.get('f170', 0),
                'chg': d.get('f169', 0),
                'bid1': d.get('f50', 0) / 100,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    except Exception as e:
        print(f"获取数据失败: {e}")
    return None


def get_realtime_data_sina(code):
    """备用：使用新浪API获取实时数据"""
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "http://finance.sina.com.cn"
    }
    
    url = f"http://hq.sinajs.cn/list=sh{code}"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
        m = re.search(r'"(.+)"', resp.text)
        if m:
            d = m.group(1).split(',')
            if len(d) > 31:
                price = float(d[3])
                yclose = float(d[2])
                chg_pct = (price - yclose) / yclose * 100
                
                return {
                    'name': d[0],
                    'code': code,
                    'price': price,
                    'open': float(d[1]),
                    'high': float(d[4]),
                    'low': float(d[5]),
                    'close_prev': yclose,
                    'chg_pct': chg_pct,
                    'chg': price - yclose,
                    'volume': float(d[8]) / 100,
                    'amount': float(d[9]) / 10000,
                    'date': d[30],
                    'time': d[31]
                }
    except Exception as e:
        print(f"新浪API失败: {e}")
    return None


def display_stock_info(data):
    """格式化显示股票信息"""
    if not data:
        print("无数据")
        return
    
    print("\n" + "=" * 50)
    print(f"📊 {data['name']} ({data['code']}) 实时行情")
    print("=" * 50)
    print(f"  💰 当前价格: {data['price']:.2f}")
    print(f"  📈 涨跌幅:   {data['chg_pct']:+.2f}%")
    print(f"  📉 涨跌额:   {data['chg']:+.2f}")
    print("-" * 50)
    print(f"  📅 今开:     {data['open']:.2f}")
    print(f"  🔺 最高:     {data['high']:.2f}")
    print(f"  🔻 最低:     {data['low']:.2f}")
    print(f"  📍 昨收:     {data['close_prev']:.2f}")
    print("-" * 50)
    print(f"  📦 成交量:   {data['volume']:.0f}手")
    print(f"  💵 成交额:   {data['amount']:.2f}万元")
    print("=" * 50)
    
    if 'time' in data and data['time']:
        print(f"  🕐 更新时间: {data['time']}")


def main():
    default_code = "605066"
    
    if len(sys.argv) > 1:
        code = sys.argv[1]
    else:
        code = default_code
    
    print(f"🔍 获取股票 {code} 实时数据...")
    
    # 方法1：东方财富API
    data = get_realtime_data(code)
    
    # 方法2：新浪API（备用）
    if not data:
        print("东方财富API失败，尝试新浪API...")
        data = get_realtime_data_sina(code)
    
    if data:
        display_stock_info(data)
    else:
        print("❌ 所有方法均失败")


if __name__ == "__main__":
    main()
