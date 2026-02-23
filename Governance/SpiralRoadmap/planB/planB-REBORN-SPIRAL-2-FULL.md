# Reborn 第二螺旋：完整闭环（Plan B）

**螺旋编号**: Reborn-Spiral-2  
**目标**: 扩展到全市场，完善核心算法  
**预期周期**: 3-4个月  
**前置**: 第一螺旋完成  

---

## 核心目标

在第一螺旋基础上扩展到全A股市场，实现：
- 全市场4000+股票覆盖
- 16年完整历史数据
- 多周期严格回测验证
- 专业级风险管理
- 完整归因分析体系

---

## 执行口径（与 Plan A 同精度）

1. `S3c/S3d/S3e` 采用双档门禁：
   - `MVP`：最小可用（无 FAIL、WARN 可解释）
   - `FULL`：完整生产口径
2. 允许并行准备：`S3c/S3d/S3e` 的数据准备与实验可并行。
3. 强制串行收口：`S3c -> S3d -> S3e` 的收口与宣告必须串行。
4. 螺旋2必须输出 `GO/NO_GO` 并同步到 `PLAN-B-READINESS-SCOREBOARD.md`。

---

## 数据层升级

### 全市场数据
```
覆盖范围：
- A股全市场：主板+创业板+科创板+北交所
- 股票数量：4000+只
- 历史跨度：2008-2024（16年）
- 数据频率：日频+分钟频（关键时点）

数据源策略：
- 主源：TuShare Pro
- 备源：Wind/AKShare
- 应急：本地缓存
```

### 数据质量体系
```python
class DataQualityManager:
    def __init__(self):
        self.quality_rules = {
            'completeness': 0.995,  # 完整性>99.5%
            'consistency': 0.999,   # 一致性>99.9%
            'timeliness': 300,      # 延迟<5分钟
            'accuracy': 0.9999      # 准确性>99.99%
        }
    
    def daily_quality_check(self):
        # 数据完整性检查
        # 数据一致性检查  
        # 异常值检测
        # 质量报告生成
        pass
```

---

## 算法层完整版

### MSS完整版
```python
class MSS_Full:
    def __init__(self):
        self.factors = [
            'volume_surge',      # 成交量异动
            'price_momentum',    # 价格动量
            'volatility_regime', # 波动率状态
            'sentiment_proxy',   # 情绪代理指标
            'market_microstructure' # 微观结构
        ]
    
    def calculate_adaptive_score(self, stock_data, market_regime):
        # 根据市场状态自适应调整权重
        # 多因子综合评分
        # 历史分位数标准化
        pass
```

### IRS完整版
```python
class IRS_Full:
    def __init__(self):
        self.industries = self.load_sw_industries()  # 申万31个行业
        self.factors = [
            'relative_strength',  # 相对强度
            'rotation_momentum',  # 轮动动量
            'fund_flow',         # 资金流向
            'valuation_spread',  # 估值差异
            'policy_impact'      # 政策影响
        ]
    
    def calculate_industry_allocation(self, market_data):
        # 行业轮动识别
        # 动态权重分配
        # 风险预算控制
        pass
```

---

## 验证体系升级

### 多周期回测
```python
class MultiPeriodBacktester:
    def __init__(self):
        self.test_periods = [
            ('2008-2010', '金融危机'),
            ('2014-2016', '股灾周期'), 
            ('2018-2020', '贸易战+疫情'),
            ('2021-2024', '结构性行情')
        ]
    
    def run_comprehensive_backtest(self):
        results = {}
        for period, description in self.test_periods:
            results[period] = self.backtest_period(period)
        return self.generate_comprehensive_report(results)
```

### 归因分析系统
```python
class AttributionAnalyzer:
    def __init__(self):
        self.attribution_factors = [
            'stock_selection',   # 选股贡献
            'industry_allocation', # 行业配置贡献
            'timing',           # 择时贡献
            'interaction'       # 交互效应
        ]
    
    def decompose_returns(self, portfolio_returns, benchmark_returns):
        # Brinson归因模型
        # 多因子风险模型归因
        # 时变归因分析
        pass
```

### 归因对比（新增硬门禁）

- 必须包含 `signal/execution/cost` 三分解。
- 必须包含 `MSS vs 随机基准` 与 `MSS vs 技术基线`。
- 必须明确“收益来源主要由信号还是执行驱动”。

---

## 收口标准

### 数据层
- [ ] 全市场16年数据完整入库
- [ ] 数据质量>99.5%
- [ ] 实时更新延迟<5分钟

### 算法层  
- [ ] 每日产生20-50个信号
- [ ] 多市场状态下稳定运行
- [ ] 算法执行时间<30分钟

### 回测层
- [ ] 多周期回测年化收益>15%
- [ ] 最大回撤<20%
- [ ] 信息比率>1.5
- [ ] 完整归因分析报告
- [ ] S3c/S3d/S3e `MVP` 与 `FULL` 门禁均通过

### 系统层
- [ ] 7×24小时稳定运行
- [ ] 完整监控告警体系
- [ ] 专业级GUI界面

---

## 螺旋2退出约束（新增）

1. 若仅通过 `MVP` 未通过 `FULL`，状态为 `WARN`，不得进入真实资金流程。
2. 螺旋2未 `GO` 时，螺旋3只能做开发，不得宣称实战就绪。
