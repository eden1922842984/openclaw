#!/usr/bin/env python3
"""
高胜率趋势交易策略 - 黄金期货版
基于50日突破 + RSI确认 + 0.5:1止盈 + 2ATR止损

作者：OpenClaw AI Assistant
日期：2026-03-23
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================
# 配置参数
# ============================================
CONFIG = {
    'breakout_period': 50,      # 50日突破
    'rsi_upper': 65,             # RSI<65确认强势
    'rsi_lower': 35,             # RSI>35确认不是超卖
    'stop_atr': 2.0,            # 2ATR止损
    'tp_ratio': 0.5,            # 0.5:1止盈
    'max_risk_pct': 0.02,       # 单笔风险2%
    'atr_period': 14,            # ATR周期
    'rsi_period': 14,            # RSI周期
}

# ============================================
# 技术指标计算
# ============================================
def calculate_atr(high, low, close, period=14):
    """计算ATR"""
    tr = np.maximum(high - low, 
                   np.maximum(abs(high - np.roll(close, 1)),
                              abs(low - np.roll(close, 1))))
    tr[0] = high[0] - low[0]
    atr = np.convolve(tr, np.ones(period)/period, mode='valid')
    return atr

def calculate_rsi(prices, period=14):
    """计算RSI"""
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.convolve(gains, np.ones(period)/period, mode='valid')
    avg_loss = np.convolve(losses, np.ones(period)/period, mode='valid')
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_ema(prices, period):
    """计算EMA"""
    ema = np.zeros(len(prices))
    ema[0] = prices[0]
    alpha = 2 / (period + 1)
    for i in range(1, len(prices)):
        ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
    return ema

# ============================================
# 交易信号生成
# ============================================
def generate_signals(data, config):
    """生成交易信号"""
    high = data['high'].values
    low = data['low'].values
    close = data['close'].values
    
    n = len(close)
    signals = np.zeros(n)
    stop_loss = np.zeros(n)
    take_profit = np.zeros(n)
    
    # 计算指标
    atr = calculate_atr(high, low, close, config['atr_period'])
    rsi = calculate_rsi(close, config['rsi_period'])
    
    # 50日高点
    for i in range(config['breakout_period'], n):
        lookback = i - config['breakout_period']
        highest = np.max(high[lookback:i])
        
        # 突破信号
        if close[i] > highest and rsi[i-1] < config['rsi_upper'] and rsi[i-1] > config['rsi_lower']:
            signals[i] = 1  # 买入信号
            
            # 计算止损和止盈
            atr_val = atr[i-1] if i-1 < len(atr) else atr[-1]
            stop_loss[i] = close[i] - config['stop_atr'] * atr_val
            take_profit[i] = close[i] + config['tp_ratio'] * config['stop_atr'] * atr_val
    
    return signals, stop_loss, take_profit, {'atr': atr, 'rsi': rsi}

# ============================================
# 回测
# ============================================
def backtest(data, config, initial_capital=100000):
    """回测策略"""
    signals, stop_loss, take_profit, indicators = generate_signals(data, config)
    
    close = data['close'].values
    dates = data.index
    
    capital = initial_capital
    position = 0
    entry_price = 0
    trades = []
    equity_curve = [capital]
    
    for i in range(len(close)):
        if signals[i] == 1 and position == 0:
            # 开仓
            risk_amount = capital * config['max_risk_pct']
            atr_val = indicators['atr'][i-1] if i-1 < len(indicators['atr']) else indicators['atr'][-1]
            position_size = risk_amount / (config['stop_atr'] * atr_val)
            
            position = position_size
            entry_price = close[i]
            entry_date = dates[i]
            stop = stop_loss[i]
            target = take_profit[i]
        
        elif position > 0:
            # 检查止损/止盈
            if close[i] <= stop:
                # 止损
                pnl = (stop - entry_price) * position
                capital += pnl
                trades.append({'date': entry_date, 'exit': dates[i], 'pnl': pnl, 'type': 'stop'})
                position = 0
            
            elif close[i] >= target:
                # 止盈
                pnl = (target - entry_price) * position
                capital += pnl
                trades.append({'date': entry_date, 'exit': dates[i], 'pnl': pnl, 'type': 'profit'})
                position = 0
            
            elif i == len(close) - 1:
                # 最后一天平仓
                pnl = (close[i] - entry_price) * position
                capital += pnl
                trades.append({'date': entry_date, 'exit': dates[i], 'pnl': pnl, 'type': 'close'})
                position = 0
        
        equity_curve.append(capital)
    
    # 计算统计
    if trades:
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] <= 0]
        win_rate = len(wins) / len(trades) * 100
        
        avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl'] for t in losses]) if losses else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        total_return = (capital - initial_capital) / initial_capital * 100
        sharpe = np.mean([t['pnl'] for t in trades]) / np.std([t['pnl'] for t in trades]) if len(trades) > 1 else 0
        
        return {
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_return': total_return,
            'final_capital': capital,
            'sharpe_ratio': sharpe,
            'trades': trades
        }
    
    return None

# ============================================
# 参数优化
# ============================================
def optimize_parameters(data):
    """参数优化"""
    best_params = None
    best_win_rate = 0
    results = []
    
    breakout_periods = [30, 40, 50, 60, 70]
    rsi_uppers = [60, 65, 70, 75]
    stop_atrs = [1.5, 2.0, 2.5, 3.0]
    tp_ratios = [0.5, 0.75, 1.0, 1.5]
    
    total = len(breakout_periods) * len(rsi_uppers) * len(stop_atrs) * len(tp_ratios)
    count = 0
    
    print(f"测试 {total} 种参数组合...")
    
    for bp in breakout_periods:
        for ru in rsi_uppers:
            for sa in stop_atrs:
                for tp in tp_ratios:
                    config = CONFIG.copy()
                    config['breakout_period'] = bp
                    config['rsi_upper'] = ru
                    config['stop_atr'] = sa
                    config['tp_ratio'] = tp
                    
                    result = backtest(data, config)
                    count += 1
                    
                    if result and result['total_trades'] >= 5:
                        results.append({
                            'params': config.copy(),
                            'result': result
                        })
                        
                        if result['win_rate'] > best_win_rate:
                            best_win_rate = result['win_rate']
                            best_params = config.copy()
    
    # 排序输出top10
    results.sort(key=lambda x: x['result']['win_rate'], reverse=True)
    
    print("\n🏆 Top 10 策略:")
    print("-" * 80)
    for i, r in enumerate(results[:10]):
        p = r['params']
        res = r['result']
        print(f"{i+1}. 突破{p['breakout_period']}日 RSI<{p['rsi_upper']} 止损{p['stop_atr']}ATR 止盈{p['tp_ratio']}:1")
        print(f"   胜率:{res['win_rate']:.1f}% 盈亏比:{res['profit_factor']:.2f} 交易数:{res['total_trades']}")
    
    return best_params, results


# ============================================
# 主程序
# ============================================
if __name__ == "__main__":
    print("=" * 60)
    print("高胜率趋势交易策略 - 参数优化")
    print("=" * 60)
    
    # 示例：使用随机数据测试
    np.random.seed(42)
    n = 500
    dates = pd.date_range(start='2024-01-01', periods=n, freq='d')
    
    # 生成模拟数据
    close = 100 + np.cumsum(np.random.randn(n) * 2)
    high = close + np.random.rand(n) * 3
    low = close - np.random.rand(n) * 3
    open_price = np.roll(high, 1) + np.random.rand(n) * 2
    
    data = pd.DataFrame({
        'date': dates,
        'open': open_price,
        'high': high,
        'low': low,
        'close': close
    })
    data.set_index('date', inplace=True)
    
    print(f"\n数据: {n}天 OHLC数据")
    
    # 参数优化
    best_params, all_results = optimize_parameters(data)
    
    if best_params:
        print(f"\n✅ 最优参数:")
        print(f"   突破周期: {best_params['breakout_period']}日")
        print(f"   RSI上限: {best_params['rsi_upper']}")
        print(f"   止损: {best_params['stop_atr']}ATR")
        print(f"   止盈: {best_params['tp_ratio']}:1")
        
        # 最优结果
        best_result = [r for r in all_results if r['params'] == best_params][0]['result']
        print(f"\n📊 最优结果:")
        print(f"   胜率: {best_result['win_rate']:.1f}%")
        print(f"   盈亏比: {best_result['profit_factor']:.2f}")
        print(f"   总交易: {best_result['total_trades']}")
        print(f"   总收益: {best_result['total_return']:.1f}%")
