# Reborn 第一螺旋：金丝雀闭环（Plan B）

**螺旋编号**: Reborn-Spiral-1  
**目标**: 建立最小可用的情绪量化系统  
**预期周期**: 2-3个月  
**状态**: Plan B 设计方案  

---

## 螺旋目标

建立一个完整的端到端情绪量化系统，虽然规模较小但功能完整，能够：
- 每日产生可执行的交易信号
- 进行历史回测验证
- 提供基础的风险控制
- 输出可视化的分析报告

---

## 数据层设计

### 金丝雀数据包
```
选股标准：
- 市值排名前50的活跃股票
- 涵盖主要行业（金融、科技、消费、医药、制造）
- 日均成交额 > 5亿元
- 上市时间 > 2年

数据范围：
- 时间跨度：最近1年（252个交易日）
- 数据频率：日频数据
- 数据内容：OHLCV + 基本面 + 行业分类
```

### 本地数据库设计
```sql
-- 股票基础信息表
CREATE TABLE stock_basic (
    stock_code VARCHAR(10) PRIMARY KEY,
    stock_name VARCHAR(50),
    industry VARCHAR(20),
    market_cap DECIMAL(15,2),
    list_date DATE
);

-- 日行情数据表
CREATE TABLE daily_quotes (
    trade_date DATE,
    stock_code VARCHAR(10),
    open_price DECIMAL(10,2),
    high_price DECIMAL(10,2),
    low_price DECIMAL(10,2),
    close_price DECIMAL(10,2),
    volume BIGINT,
    amount DECIMAL(15,2),
    PRIMARY KEY (trade_date, stock_code)
);

-- 基本面数据表
CREATE TABLE fundamental_data (
    trade_date DATE,
    stock_code VARCHAR(10),
    pe_ratio DECIMAL(8,2),
    pb_ratio DECIMAL(8,2),
    roe DECIMAL(6,2),
    debt_ratio DECIMAL(6,2),
    PRIMARY KEY (trade_date, stock_code)
);
```

### 数据获取策略
```python
# 数据获取优先级
1. TuShare Pro（主要数据源）
2. AKShare（备用数据源）
3. 本地缓存（离线模式）

# 更新策略
- 历史数据：一次性批量导入
- 增量数据：每日收盘后更新
- 数据校验：自动检查数据完整性和一致性
```

---

## 核心算法设计

### MSS 简化版（市场情绪评分）
```python
def calculate_mss_simple(stock_data):
    """
    简化版MSS算法
    基于成交量和价格动量的情绪评分
    """
    # 成交量因子（20日均量比）
    volume_factor = stock_data['volume'] / stock_data['volume'].rolling(20).mean()
    
    # 价格动量因子（5日收益率）
    price_momentum = stock_data['close'].pct_change(5)
    
    # 波动率因子（20日波动率）
    volatility = stock_data['close'].pct_change().rolling(20).std()
    
    # 综合情绪评分
    mss_score = (
        0.4 * normalize(volume_factor) +
        0.4 * normalize(price_momentum) +
        0.2 * normalize(1/volatility)  # 低波动率为正面情绪
    )
    
    return mss_score
```

### IRS 简化版（行业轮动评分）
```python
def calculate_irs_simple(industry_data):
    """
    简化版IRS算法
    基于行业相对强度的配置建议
    """
    industries = ['金融', '科技', '消费', '医药', '制造']
    
    industry_scores = {}
    for industry in industries:
        # 行业平均收益率（10日）
        industry_return = industry_data[industry]['return_10d'].mean()
        
        # 行业相对强度（vs 市场）
        market_return = industry_data['market']['return_10d']
        relative_strength = industry_return - market_return
        
        # 行业资金流入（成交额变化）
        money_flow = industry_data[industry]['amount_change_5d'].mean()
        
        # 综合评分
        industry_scores[industry] = (
            0.5 * normalize(relative_strength) +
            0.3 * normalize(money_flow) +
            0.2 * normalize(industry_return)
        )
    
    return industry_scores
```

### PAS 简化版（个股评分）
```python
def calculate_pas_simple(stock_data):
    """
    简化版PAS算法
    基于技术指标的个股评分
    """
    # RSI指标
    rsi = calculate_rsi(stock_data['close'], 14)
    
    # MACD指标
    macd, signal, histogram = calculate_macd(stock_data['close'])
    
    # 布林带位置
    bb_position = calculate_bollinger_position(stock_data['close'], 20)
    
    # 综合评分
    pas_score = (
        0.3 * normalize_rsi(rsi) +           # RSI超卖超买
        0.4 * normalize(histogram) +          # MACD动量
        0.3 * normalize(bb_position)          # 布林带位置
    )
    
    return pas_score
```

### 集成逻辑（简单版）
```python
def integrate_signals(mss_scores, irs_scores, pas_scores):
    """
    简单加权集成
    固定权重：MSS 40%, IRS 30%, PAS 30%
    """
    final_scores = {}
    
    for stock_code in mss_scores.keys():
        industry = get_stock_industry(stock_code)
        
        final_score = (
            0.4 * mss_scores[stock_code] +
            0.3 * irs_scores[industry] +
            0.3 * pas_scores[stock_code]
        )
        
        final_scores[stock_code] = final_score
    
    return final_scores
```

---

## 验证与回测设计

### 回测框架
```python
class SimpleBacktester:
    def __init__(self, initial_capital=1000000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}
        self.trade_history = []
        
    def run_backtest(self, signals, price_data, start_date, end_date):
        """
        简单回测引擎
        """
        for date in pd.date_range(start_date, end_date):
            if date in signals.index:
                # 获取当日信号
                daily_signals = signals.loc[date]
                
                # 执行交易
                self.execute_trades(daily_signals, price_data.loc[date])
                
                # 更新持仓价值
                self.update_portfolio_value(price_data.loc[date])
        
        return self.generate_performance_report()
```

### 风险控制
```python
class RiskManager:
    def __init__(self):
        self.max_position_size = 0.05  # 单只股票最大仓位5%
        self.max_total_position = 0.95  # 最大总仓位95%
        self.stop_loss_ratio = 0.08    # 止损比例8%
        
    def check_position_limits(self, new_positions):
        """检查仓位限制"""
        # 检查单只股票仓位
        for stock, weight in new_positions.items():
            if weight > self.max_position_size:
                new_positions[stock] = self.max_position_size
        
        # 检查总仓位
        total_position = sum(new_positions.values())
        if total_position > self.max_total_position:
            scale_factor = self.max_total_position / total_position
            for stock in new_positions:
                new_positions[stock] *= scale_factor
        
        return new_positions
    
    def check_stop_loss(self, current_positions, current_prices, entry_prices):
        """检查止损"""
        stop_loss_signals = {}
        for stock, position in current_positions.items():
            if position > 0:  # 多头持仓
                loss_ratio = (entry_prices[stock] - current_prices[stock]) / entry_prices[stock]
                if loss_ratio > self.stop_loss_ratio:
                    stop_loss_signals[stock] = 'SELL'
        
        return stop_loss_signals
```

---

## 交易执行设计

### 信号生成
```python
class SignalGenerator:
    def __init__(self, threshold_buy=0.6, threshold_sell=0.4):
        self.threshold_buy = threshold_buy
        self.threshold_sell = threshold_sell
    
    def generate_daily_signals(self, integrated_scores):
        """生成每日交易信号"""
        signals = {}
        
        # 排序选择前10名买入
        sorted_scores = sorted(integrated_scores.items(), 
                             key=lambda x: x[1], reverse=True)
        
        buy_candidates = [stock for stock, score in sorted_scores[:10] 
                         if score > self.threshold_buy]
        
        # 卖出信号：评分低于阈值的持仓股票
        sell_candidates = [stock for stock, score in integrated_scores.items() 
                          if score < self.threshold_sell]
        
        # 生成信号
        for stock in buy_candidates:
            signals[stock] = 'BUY'
        
        for stock in sell_candidates:
            signals[stock] = 'SELL'
        
        return signals
```

### 模拟交易
```python
class PaperTrader:
    def __init__(self, commission_rate=0.0003):
        self.commission_rate = commission_rate
        self.slippage_rate = 0.001  # 滑点0.1%
        
    def execute_trade(self, stock_code, action, quantity, price):
        """执行模拟交易"""
        # 计算实际成交价格（考虑滑点）
        if action == 'BUY':
            actual_price = price * (1 + self.slippage_rate)
        else:
            actual_price = price * (1 - self.slippage_rate)
        
        # 计算手续费
        trade_value = quantity * actual_price
        commission = trade_value * self.commission_rate
        
        # 记录交易
        trade_record = {
            'date': datetime.now(),
            'stock_code': stock_code,
            'action': action,
            'quantity': quantity,
            'price': actual_price,
            'commission': commission,
            'total_cost': trade_value + commission
        }
        
        return trade_record
```

---

## 分析输出设计

### 日报生成
```python
class DailyReporter:
    def generate_daily_report(self, date, signals, positions, performance):
        """生成每日报告"""
        report = {
            'date': date,
            'signals': {
                'buy_signals': [s for s, a in signals.items() if a == 'BUY'],
                'sell_signals': [s for s, a in signals.items() if a == 'SELL'],
                'signal_count': len(signals)
            },
            'positions': {
                'total_value': sum(positions.values()),
                'stock_count': len(positions),
                'top_holdings': sorted(positions.items(), 
                                     key=lambda x: x[1], reverse=True)[:5]
            },
            'performance': {
                'daily_return': performance['daily_return'],
                'total_return': performance['total_return'],
                'max_drawdown': performance['max_drawdown']
            }
        }
        
        return report
```

### GUI界面
```python
import streamlit as st
import plotly.graph_objects as go

class SimpleGUI:
    def __init__(self):
        st.set_page_config(page_title="EmotionQuant 金丝雀系统")
    
    def show_dashboard(self):
        """显示主仪表板"""
        st.title("EmotionQuant 金丝雀系统")
        
        # 今日信号
        st.header("今日交易信号")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("买入信号")
            buy_signals = self.get_buy_signals()
            for signal in buy_signals:
                st.write(f"📈 {signal['stock_name']} ({signal['stock_code']})")
                st.write(f"   评分: {signal['score']:.2f}")
        
        with col2:
            st.subheader("卖出信号")
            sell_signals = self.get_sell_signals()
            for signal in sell_signals:
                st.write(f"📉 {signal['stock_name']} ({signal['stock_code']})")
                st.write(f"   评分: {signal['score']:.2f}")
        
        # 绩效图表
        st.header("历史绩效")
        performance_data = self.get_performance_data()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=performance_data['date'],
            y=performance_data['cumulative_return'],
            mode='lines',
            name='策略收益'
        ))
        fig.add_trace(go.Scatter(
            x=performance_data['date'],
            y=performance_data['benchmark_return'],
            mode='lines',
            name='基准收益'
        ))
        
        st.plotly_chart(fig)
```

---

## 收口标准

### 数据层收口
- [ ] 金丝雀数据包完整入库（50只股票，1年历史）
- [ ] 数据质量检查通过（无缺失，无异常值）
- [ ] 每日增量更新机制正常运行
- [ ] 数据库查询性能满足要求（<1秒）

### 算法层收口
- [ ] MSS/IRS/PAS三个算法模块正常运行
- [ ] 每日能产生5-10个交易信号
- [ ] 信号质量检查通过（无异常信号）
- [ ] 算法执行时间<5分钟

### 回测层收口
- [ ] 6个月历史回测完成
- [ ] 年化收益率 > 10%
- [ ] 最大回撤 < 15%
- [ ] 夏普比率 > 1.0
- [ ] 胜率 > 55%

### 交易层收口
- [ ] 模拟交易系统正常运行
- [ ] 风险控制机制有效
- [ ] 交易成本计算准确
- [ ] 持仓管理功能完整

### 分析层收口
- [ ] 日报自动生成
- [ ] GUI界面功能完整
- [ ] 绩效分析准确
- [ ] 风险指标计算正确

---

## 实施计划

### 第1个月：数据基础
- Week 1-2: 搭建本地数据库，设计数据模型
- Week 3-4: 实现数据获取和清洗，建立金丝雀数据包

### 第2个月：算法实现
- Week 5-6: 实现MSS和PAS算法
- Week 7-8: 实现IRS算法和信号集成

### 第3个月：系统集成
- Week 9-10: 实现回测框架和风险控制
- Week 11-12: 开发GUI界面和报告系统

---

## 成功指标

1. **系统可用性**: 系统能够7×24小时稳定运行
2. **信号质量**: 每日产生的信号数量稳定在5-10个
3. **回测表现**: 历史回测年化收益>10%，回撤<15%
4. **用户体验**: GUI界面响应时间<3秒
5. **数据质量**: 数据完整性>99.5%

完成第一螺旋后，系统将具备基本的量化交易能力，为第二螺旋的全市场扩展奠定坚实基础。