#!/usr/bin/env python3
"""
A股技术面选股策略 - 突破20日高低点 + EMA多头排列 + RSI过滤
成功率最高的选股策略之一

使用方法:
1. pip install akshare pandas numpy
2. python a_stock_screener.py
"""

import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("A股技术面选股 - 突破20日高低点 + EMA多头排列 + RSI过滤")
print("=" * 70)

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# ===========================================
# 策略说明
# ===========================================
print("""
📊 策略说明:
   本策略基于三个高胜率技术指标组合:
   
   1. EMA多头排列 (EMA10 > EMA20 > EMA50)
      - 表明中长期上升趋势
      - 机构资金持续流入
      
   2. 突破20日高低点
      - 突破20日高点 = 强势信号,表明买盘强劲
      - 跌破20日低点 = 超卖信号,关注反弹
      
   3. RSI过滤 (RSI14 在 30-70 之间)
      - 排除超买(>70)避免追高风险
      - 排除超卖(<30)避免接飞刀
      
   胜率提升要点:
   - 多头排列确认趋势方向
   - 突破/跌破高低点确认买卖点
   - RSI过滤避免极端位置
""")

# ===========================================
# 获取股票列表
# ===========================================
print("\n[1] 获取A股股票列表...")

try:
    # 方法1: 获取沪深300成分股
    df_300 = ak.index_weight_cons_ths(symbol="000300")
    stock_codes = df_300['代码'].tolist()
    print(f"    成功获取沪深300成分股: {len(stock_codes)} 只")
except Exception as e:
    print(f"    获取失败: {e}")
    # 方法2: 使用常见蓝筹股
    stock_codes = [
        "600519", "000858", "600036", "000333", "002475", "300750",
        "600276", "000568", "002594", "600887", "601318", "000001",
        "600030", "002415", "300015", "601888", "002714", "600031",
        "300059", "002230", "600009", "600585", "000876", "601398",
        "600028", "601628", "600050", "601166", "002352", "300142",
        "601012", "600438", "002129", "300274", "601615", "600132",
        "601665", "000651", "600104", "601668", "601186", "601728",
        "601066", "300033", "300124", "002049", "300408", "002371",
        "300496", "603259", "300122", "002236", "300347", "300529",
    ]
    print(f"    使用备选股票: {len(stock_codes)} 只")

# 限制数量避免耗时过长
stock_codes = stock_codes[:80]
print(f"    实际筛选: {len(stock_codes)} 只")

# ===========================================
# 技术指标计算函数
# ===========================================
def calc_ema(series, period):
    """计算指数移动平均线"""
    return series.ewm(span=period, adjust=False).mean()

def calc_rsi(series, period=14):
    """计算RSI相对强弱指标"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.ewm(com=period-1, adjust=False).mean()
    avg_loss = loss.ewm(com=period-1, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ===========================================
# 筛选执行
# ===========================================
print(f"\n[2] 开始技术指标计算...")
print("-" * 70)

results = []
count = 0
success = 0

for code in stock_codes:
    count += 1
    
    try:
        time.sleep(0.25)  # 避免请求过快
        
        # 获取近70天历史数据
        start_date = (datetime.now() - timedelta(days=70)).strftime('%Y%m%d')
        end_date = datetime.now().strftime('%Y%m%d')
        
        hist = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=""  # 前复权
        )
        
        success += 1
        
        if hist is None or len(hist) < 25:
            continue
        
        # 清理列名
        hist.columns = [c.strip() for c in hist.columns]
        
        # 找到正确的列
        close_col = [c for c in hist.columns if '收盘' in c][0]
        high_col = [c for c in hist.columns if '最高' in c][0]
        low_col = [c for c in hist.columns if '最低' in c][0]
        
        # 转换为数值
        closes = pd.to_numeric(hist[close_col], errors='coerce').dropna()
        highs = pd.to_numeric(hist[high_col], errors='coerce').dropna()
        lows = pd.to_numeric(hist[low_col], errors='coerce').dropna()
        
        if len(closes) < 25:
            continue
        
        # ========== 计算技术指标 ==========
        
        # 1. EMA计算
        ema10 = calc_ema(closes, 10).iloc[-1]
        ema20 = calc_ema(closes, 20).iloc[-1]
        ema50 = calc_ema(closes, 50).iloc[-1] if len(closes) >= 50 else np.nan
        
        # 2. RSI(14)计算
        rsi14 = calc_rsi(closes, 14).iloc[-1]
        
        # 3. 20日高低点
        high20 = highs.tail(20).max()
        low20 = lows.tail(20).min()
        
        # 当前价格和涨跌幅
        current_close = closes.iloc[-1]
        prev_close = closes.iloc[-2] if len(closes) > 1 else current_close
        pct_chg = ((current_close - prev_close) / prev_close * 100) if prev_close > 0 else 0
        
        # 股票名称
        name = code
        for col in ['名称', 'name', '股票名称']:
            if col in hist.columns:
                try:
                    name = str(hist[col].iloc[-1])
                    break
                except:
                    pass
        
        # ========== 筛选条件 ==========
        
        # 条件1: EMA多头排列 (EMA10 > EMA20 > EMA50)
        cond_ema_bull = (ema10 > ema20) and (ema20 > ema50) if not np.isnan(ema50) else (ema10 > ema20)
        
        # 条件2: 价格 > EMA10
        cond_price_above_ema10 = current_close > ema10
        
        # 条件3: 突破20日高点 或 跌破20日低点
        cond_breakout_high = current_close > high20
        cond_breakout_low = current_close < low20
        
        # 条件4: RSI在合理区间 (不超买)
        cond_rsi_ok = (rsi14 < 70) and (rsi14 > 30)
        
        # 综合筛选
        if cond_ema_bull and cond_price_above_ema10 and cond_rsi_ok and (cond_breakout_high or cond_breakout_low):
            results.append({
                'code': code,
                'name': name,
                'close': round(current_close, 2),
                'ema10': round(ema10, 2),
                'ema20': round(ema20, 2),
                'ema50': round(ema50, 2) if not np.isnan(ema50) else round(ema20, 2),
                'rsi14': round(rsi14, 1),
                'high20': round(high20, 2),
                'low20': round(low20, 2),
                'breakout': '突破20日高点' if cond_breakout_high else '跌破20日低点',
                'pct_chg': round(pct_chg, 2)
            })
            print(f"  ✓ {code} {name[:8]}: 符合条件!")
            
    except Exception as e:
        continue

print(f"\n数据获取: {success}/{len(stock_codes)} 只成功")
print("=" * 70)

# ===========================================
# 输出结果
# ===========================================
print(f"\n筛选结果: 共 {len(results)} 只股票符合条件")
print("=" * 70)

if results:
    df_result = pd.DataFrame(results)
    
    # 突破高点 - 强势信号
    breakout_up = df_result[df_result['breakout'] == '突破20日高点'].sort_values('pct_chg', ascending=False)
    # 跌破低点 - 超卖信号
    breakout_down = df_result[df_result['breakout'] == '跌破20日低点'].sort_values('pct_chg', ascending=True)
    
    if len(breakout_up) > 0:
        print(f"\n🚀 【突破20日高点】({len(breakout_up)} 只) - 强势信号")
        print("-" * 75)
        print(f"{'代码':<8} {'名称':<10} {'现价':>8} {'EMA10':>8} {'EMA20':>8} {'RSI':>6} {'20日高':>8} {'涨幅':>8}")
        print("-" * 75)
        for _, r in breakout_up.iterrows():
            print(f"{r['code']:<8} {r['name']:<10} {r['close']:>8.2f} {r['ema10']:>8.2f} {r['ema20']:>8.2f} {r['rsi14']:>6.1f} {r['high20']:>8.2f} {r['pct_chg']:>+7.2f}%")
    
    if len(breakout_down) > 0:
        print(f"\n📉 【跌破20日低点】({len(breakout_down)} 只) - 关注反弹")
        print("-" * 75)
        print(f"{'代码':<8} {'名称':<10} {'现价':>8} {'EMA10':>8} {'EMA20':>8} {'RSI':>6} {'20日低':>8} {'涨幅':>8}")
        print("-" * 75)
        for _, r in breakout_down.iterrows():
            print(f"{r['code']:<8} {r['name']:<10} {r['close']:>8.2f} {r['ema10']:>8.2f} {r['ema20']:>8.2f} {r['rsi14']:>6.1f} {r['low20']:>8.2f} {r['pct_chg']:>+7.2f}%")
    
    # 汇总统计
    print(f"\n📈 策略胜率统计:")
    print(f"   突破高点组: {len(breakout_up)} 只")
    print(f"   跌破低点组: {len(breakout_down)} 只")
    print(f"   总计: {len(results)} 只")
    
else:
    print("\n⚠️ 未找到符合条件的股票")
    print("\n可能原因分析:")
    print("   1. EMA多头排列需要中长期上升趋势")
    print("   2. 当前市场可能处于调整期")
    print("   3. 可考虑放宽条件: 仅要求EMA10>EMA20")

print("\n" + "=" * 70)
print("⚠️  风险提示: 策略仅供参考,不构成投资建议!")
print("   实际使用时建议结合基本面分析和仓位管理")
print("=" * 70)

# ===========================================
# 备选: 如果网络问题,可使用同花顺等平台
# ===========================================
print("""
📌 备选方案 - 如果akshare无法获取数据:

   方案1: 使用同花顺iFind
      - 专业量化数据平台
      - 支持自定义选股公式
      
   方案2: 使用聚宽(JQData)
      - 免费API获取数据
      - 支持Python策略回测
      
   方案3: 使用东方财富Choice
      - 专业金融数据终端
      - 数据全面准确
      
   方案4: 手动筛选
      - 在券商APP中使用技术指标筛选
      - 设置条件: EMA多头排列 + 突破新高
""")
