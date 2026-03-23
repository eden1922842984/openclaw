#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辨势交易法 - A股智能选股器
基于胜率最高策略：突破20日高低点 + EMA多头排列 + RSI不超买

使用方法：
1. 安装依赖：pip install akshare pandas numpy
2. 运行：python stock_screener.py

作者：AI Assistant
日期：2026-03-23
"""

import warnings
warnings.filterwarnings('ignore')

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json

# ======================
# 策略参数配置
# ======================
CONFIG = {
    # 均线参数
    'ema_short': 10,
    'ema_medium': 20,
    'ema_long': 50,
    
    # RSI参数
    'rsi_period': 14,
    'rsi_low': 30,
    'rsi_high': 70,
    
    # 突破参数
    'breakout_period': 20,
    
    # 筛选条件
    'min_price': 1,           # 最低价格（元）
    'max_price': 500,         # 最高价格（元）
    'min_volume': 10000000,   # 最低成交量（10万）
    
    # 数量限制（避免超时）
    'max_stocks': 100,        # 最多筛选股票数
    
    # 板块过滤
    'exclude_st': True,       # 排除ST股票
}

# ======================
# 技术指标计算
# ======================
def calculate_indicators(df):
    """计算技术指标"""
    df = df.copy()
    
    # 排序
    df = df.sort_values('date').reset_index(drop=True)
    
    # EMA计算
    df['EMA10'] = df['close'].ewm(span=10, adjust=False).mean()
    df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # ATR计算
    hl = df['high'] - df['low']
    hc = np.abs(df['high'] - df['close'].shift())
    lc = np.abs(df['low'] - df['close'].shift())
    df['ATR'] = pd.concat([hl, hc, lc], axis=1).max(axis=1).ewm(span=14, adjust=False).mean()
    
    # RSI计算
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + gain / loss))
    
    # 20日高低点
    df['HIGH20'] = df['high'].rolling(20).max()
    df['LOW20'] = df['low'].rolling(20).min()
    
    return df

# ======================
# 选股策略
# ======================
def check_entry_signals(df, lookback=5):
    """
    检查入场信号
    
    信号类型：
    1. 突破20日新高（做多）
    2. 突破20日新低（做空）
    3. EMA回踩（做多）
    
    返回：信号类型 或 None
    """
    if len(df) < 60:  # 需要足够数据
        return None, None
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 检查趋势（EMA多头排列）
    trend_up = (last['EMA10'] > last['EMA20'] > last['EMA50'] and last['close'] > last['EMA10'])
    trend_down = (last['EMA10'] < last['EMA20'] < last['EMA50'] and last['close'] < last['EMA10'])
    
    # RSI条件
    rsi_ok_long = CONFIG['rsi_low'] < last['RSI'] < CONFIG['rsi_high']
    
    signal = None
    direction = None
    
    # 上升趋势中检查做多信号
    if trend_up and rsi_ok_long:
        # 突破20日新高
        if last['close'] > prev['HIGH20']:
            signal = 'BREAKOUT_LONG'
            direction = 'LONG'
        # 回踩EMA20
        elif last['close'] > last['EMA20'] * 0.98 and last['close'] < last['EMA20'] * 1.02:
            signal = 'EMA_RET_LONG'
            direction = 'LONG'
    
    # 下降趋势中检查做空信号
    elif trend_down and rsi_ok_long:
        # 突破20日新低
        if last['close'] < prev['LOW20']:
            signal = 'BREAKOUT_SHORT'
            direction = 'SHORT'
        # 反弹到EMA20
        elif last['close'] < last['EMA20'] * 1.02 and last['close'] > last['EMA20'] * 0.98:
            signal = 'EMA_RET_SHORT'
            direction = 'SHORT'
    
    return signal, direction

# ======================
# 获取股票列表
# ======================
def get_stock_list():
    """获取A股股票列表"""
    print("📡 获取A股股票列表...")
    
    try:
        # 获取所有A股
        df = ak.stock_zh_a_spot_em()
        
        # 基本列名映射
        column_map = {}
        for col in df.columns:
            if '代码' in col:
                column_map[col] = 'code'
            elif '名称' in col:
                column_map[col] = 'name'
            elif '最新价' in col:
                column_map[col] = 'close'
            elif '涨跌幅' in col:
                column_map[col] = 'pct_chg'
            elif '成交量' in col:
                column_map[col] = 'volume'
            elif '成交额' in col:
                column_map[col] = 'amount'
            elif '市值' in col:
                column_map[col] = 'mkt_cap'
        
        df = df.rename(columns=column_map)
        
        # 过滤条件
        if 'close' in df.columns:
            df = df[df['close'] > CONFIG['min_price']]
            df = df[df['close'] < CONFIG['max_price']]
        
        if 'volume' in df.columns:
            df = df[df['volume'] > CONFIG['min_volume']]
        
        if CONFIG['exclude_st'] and 'name' in df.columns:
            df = df[~df['name'].str.contains('ST', na=False)]
        
        # 只取有代码的
        if 'code' in df.columns:
            df = df[df['code'].str.match(r'^\d{6}$', na=False)]
        
        print(f"✅ 初步筛选后: {len(df)} 只股票")
        return df
        
    except Exception as e:
        print(f"❌ 获取股票列表失败: {e}")
        return pd.DataFrame()

# ======================
# 获取单只股票历史数据
# ======================
def get_stock_history(code, period='daily', adjust='qfq'):
    """获取单只股票历史数据"""
    try:
        if period == 'daily':
            df = ak.stock_zh_a_hist(symbol=code, period='daily', 
                                    start_date='20250101', 
                                    end_date=datetime.now().strftime('%Y%m%d'),
                                    adjust=adjust)
        else:
            df = ak.stock_zh_a_hist(symbol=code, period='weekly', 
                                    start_date='20240101', 
                                    end_date=datetime.now().strftime('%Y%m%d'),
                                    adjust=adjust)
        
        # 统一列名
        if '日期' in df.columns:
            df = df.rename(columns={
                '日期': 'date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume',
                '成交额': 'amount', '振幅': 'amplitude',
                '涨跌幅': 'pct_chg', '涨跌额': 'pct_value',
                '换手率': 'turnover'
            })
            df['date'] = pd.to_datetime(df['date'])
        
        return df
        
    except Exception as e:
        return None

# ======================
# 筛选单只股票
# ======================
def screen_stock(code, name):
    """筛选单只股票"""
    # 获取历史数据
    df = get_stock_history(code)
    
    if df is None or len(df) < 60:
        return None
    
    # 计算指标
    df = calculate_indicators(df)
    
    # 检查信号
    signal, direction = check_entry_signals(df)
    
    if signal is None:
        return None
    
    # 获取最新数据
    last = df.iloc[-1]
    
    # 计算其他辅助指标
    recent_5 = df.tail(5)
    avg_volume = recent_5['volume'].mean()
    
    return {
        'code': code,
        'name': name,
        'signal': signal,
        'direction': direction,
        'close': last['close'],
        'pct_chg': last.get('pct_chg', 0),
        'EMA10': last['EMA10'],
        'EMA20': last['EMA20'],
        'EMA50': last['EMA50'],
        'RSI': last['RSI'],
        'ATR': last['ATR'],
        'HIGH20': last['HIGH20'],
        'LOW20': last['LOW20'],
        'volume': last['volume'],
        'avg_volume_5d': avg_volume,
        'trend': '多头' if direction == 'LONG' else '空头',
    }

# ======================
# 主筛选流程
# ======================
def screen_stocks():
    """主筛选流程"""
    print("=" * 60)
    print("🚀 辨势交易法 - A股智能选股器")
    print("=" * 60)
    print(f"⏰ 筛选时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 策略: 突破20日高低点 + EMA多头排列 + RSI不超买")
    print("=" * 60)
    
    # 获取股票列表
    stocks_df = get_stock_list()
    
    if stocks_df.empty:
        print("❌ 没有找到符合条件的股票")
        return
    
    # 限制数量
    stocks_df = stocks_df.head(CONFIG['max_stocks'])
    
    # 逐个筛选
    results = []
    print(f"\n🔍 开始筛选 {len(stocks_df)} 只股票...")
    print("-" * 60)
    
    for idx, row in stocks_df.iterrows():
        code = row.get('code', '')
        name = row.get('name', '')
        
        if not code or len(code) != 6:
            continue
        
        # 显示进度
        progress = len(results)
        if progress % 10 == 0:
            print(f"  已筛选 {progress} 只，符合条件 {len(results)} 只...")
        
        # 筛选
        result = screen_stock(code, name)
        
        if result:
            results.append(result)
            print(f"  ✅ {code} {name:8s} | {result['signal']:15s} | RSI={result['RSI']:.1f} | 价格={result['close']:.2f}")
        
        # 避免请求过快
        time.sleep(0.1)
    
    # 排序和输出
    print("\n" + "=" * 60)
    print(f"📋 筛选结果: 共 {len(results)} 只股票符合条件")
    print("=" * 60)
    
    if results:
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('RSI', ascending=False)
        
        # 分类输出
        long_stocks = results_df[results_df['direction'] == 'LONG']
        short_stocks = results_df[results_df['direction'] == 'SHORT']
        
        print("\n🟢 【做多信号】(建议买入)")
        print("-" * 60)
        print(f"{'代码':<8} {'名称':<10} {'信号':<15} {'最新价':<10} {'RSI':<8} {'EMA10':<10} {'趋势'}")
        print("-" * 60)
        for _, r in long_stocks.head(20).iterrows():
            print(f"{r['code']:<8} {r['name']:<10} {r['signal']:<15} {r['close']:<10.2f} {r['RSI']:<8.1f} {r['EMA10']:<10.2f} {r['trend']}")
        
        if short_stocks.empty:
            print("  (无做空信号)")
        else:
            print("\n🔴 【做空信号】(融券或观望)")
            print("-" * 60)
            for _, r in short_stocks.head(10).iterrows():
                print(f"{r['code']:<8} {r['name']:<10} {r['signal']:<15} {r['close']:<10.2f} {r['RSI']:<8.1f} {r['trend']}")
        
        # 保存结果
        output_file = f"筛选结果_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n💾 结果已保存到: {output_file}")
        
        # 返回JSON格式
        print("\n📄 JSON格式结果:")
        print(json.dumps(results[:5], ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 60)
    print("⚠️  风险提示：以上仅供参考，不构成投资建议！")
    print("=" * 60)
    
    return results

# ======================
# 快速筛选（仅演示）
# ======================
def quick_demo():
    """快速演示（不下载历史数据）"""
    print("📡 获取A股实时行情...")
    
    try:
        df = ak.stock_zh_a_spot_em()
        
        # 只显示可用的列
        print("\n可用数据列:")
        for col in df.columns[:15]:
            print(f"  - {col}")
        
        # 基本信息
        print(f"\n当前A股总数: {len(df)}")
        
        # 演示筛选
        print("\n" + "=" * 60)
        print("💡 提示：完整选股需要下载历史数据")
        print("请运行: python stock_screener.py")
        print("或直接在同花顺中导入选股公式")
        print("=" * 60)
        
    except Exception as e:
        print(f"获取失败: {e}")

# ======================
# 主入口
# ======================
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--demo':
        quick_demo()
    else:
        screen_stocks()
