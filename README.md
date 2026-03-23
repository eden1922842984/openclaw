# Stock Strategy Repository

股票量化交易策略集合

## 文件说明

### 1. high_winrate_strategy.py
高胜率趋势交易策略（黄金期货版）
- 50日突破信号
- RSI确认（35-65区间）
- 0.5:1止盈 + 2ATR止损
- 参数优化（750种组合）

### 2. stock_strategy_akshare.py
A股选股策略
- 基于akshare获取A股数据
- 趋势跟踪选股
- RSI + 成交量确认

### 3. eastmoney_crawler.py
东方财富爬虫
- 实时股票行情获取
- 支持单只/批量股票
- 多API自动切换

## 使用方法

```bash
# 获取股票实时行情
python3 eastmoney_crawler.py 605066

# 运行策略回测
python3 high_winrate_strategy.py
```

## 数据源

- 东方财富
- 新浪财经
- baostock
- akshare

## 注意事项

- 请勿实盘直接使用，回测结果仅供参考
- 投资有风险，决策需谨慎
