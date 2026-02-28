# R6 Trading 重建 — 执行卡

**阶段目标**：纸上交易与回测共享成交模型和信号过滤逻辑。
**总工期**：7-8 天
**前置条件**：R5 完成（共享 execution_model / fee_calculator 已在 R0 建立，R5 已验证）
**SOS 覆盖**：docs/sos/trading 全部 26 项（A 区 16 项 + B 区 10 项）

---

## CARD-R6.1: 成交模型统一 + 信号过滤对齐

**工作量**：1.5 天
**优先级**：P0（三方不一致是系统性风险）
**SOS 映射**：T-09, B-01, B-02, T-06

### 交付物

- [ ] 复用 `src/shared/execution_model.py`
  - fill_probability: `limit_lock_factor × (0.45 × queue + 0.55 × participation)`
  - fill_ratio: `1.0 - 0.5×queue_ratio - 0.5×capacity_ratio`
  - liquidity_tier: L1(p70) / L2(p30) / L3
  - impact_cost_bps: L1=8 / L2=18 / L3=35
  - `min_fill_probability < 0.35 → reject`
  - 删除 Trading 当前"全额成交"逻辑
- [ ] 复用 `src/shared/fee_calculator.py`
  - commission + stamp_tax + impact_cost
  - Trading 和 Backtest 使用相同费率（删除 Backtest 独有的 S/M/L 分档）
- [ ] 信号过滤与 Backtest 统一（4 层）
  - 层 1：`final_score >= 55`
  - 层 2：`recommendation ∉ {AVOID, SELL}` + `grade != "D"`（补齐 T-06 缺失的 grade 过滤）
  - 层 3：`direction != "neutral"`（bearish → 生成卖出信号而非丢弃）
  - 层 4：`risk_reward_ratio >= 1.0`
  - 删除 Trading 独有的 strict+fallback 双模式
- [ ] 信号字段读取补齐 (T-05)
  - 补读 8 字段：stop, target, opportunity_grade, integration_mode, neutrality, mss_score, irs_score, pas_score

### 验收标准

1. Trading 和 Backtest 的 fill_probability 使用相同公式
2. 同一信号在两模块的费用计算一致
3. 信号过滤逻辑 4 层完全一致
4. bearish 方向生成卖出信号（非丢弃）

---

## CARD-R6.2: 风控检查补齐 + 信号验证

**工作量**：2 天
**优先级**：P0
**SOS 映射**：T-07, T-08, T-10

### 交付物

- [ ] 风控检查 6 项全部实现 (T-08)
  - [0] Regime 阈值解析：从 MSS 温度读取当前 regime → 调整仓位上限
  - [1] 资金充足检查（已有）
  - [2] 单股仓位上限：含已有持仓（`(existing + new) / equity <= 20%`）
  - [2.5] 行业集中度：`sum(same_industry_positions) / equity <= 30%`
  - [3] 总仓位上限（已有）
  - [4] T+1 限制（已有）
  - [5] 涨跌停检查（已有）
- [ ] 信号质量验证 v2.0 (T-07)
  - 读取 neutrality 字段
  - risk_level 分级：neutrality ≥ 0.7 → low; ≥ 0.4 → medium; else → high
  - position_adjustment：low → ×1.0; medium → ×0.8; high → ×0.5
  - 创建 `ValidationResult` dataclass
- [ ] 止损/止盈/回撤检查 (T-10)
  - 止损：`pct_loss <= -8%` → 生成卖出信号
  - 止盈：`close >= target_price` → 生成卖出信号
  - 最大回撤：`drawdown >= 15%` → 生成强制平仓信号
  - 复用 R5 的条件平仓逻辑
- [ ] `src/trading/risk/risk_manager.py`
  - `RiskManager` 类封装全部 6 项风控检查
  - 方法：`check_all(signal, positions, equity) -> RiskCheckResult`
  - RiskCheckResult：pass/reject + reject_reason

### 验收标准

1. 单股仓位含已有持仓（非仅新买入金额）
2. 同一行业持仓超 30% 时拒绝新信号
3. neutrality=0.3 → position 缩减 50%
4. 持仓亏损 -8% → 自动生成卖出信号

---

## CARD-R6.3: 数据模型 + 表结构对齐

**工作量**：1.5 天
**优先级**：P1
**SOS 映射**：T-02, T-03, T-04, T-11, T-12, T-13, T-16

### 交付物

- [ ] trade_records 字段对齐 (T-02)
  - 补增 11 字段：stock_name, slippage, fill_probability, fill_ratio, liquidity_tier, impact_cost_bps, trading_state, execution_mode, slice_seq, signal_id, updated_at
  - 保留合理扩展字段（t1_restriction_hit 等）并反向更新设计
- [ ] positions 字段对齐 (T-03)
  - 补增 10 字段：id, stock_name, direction, cost_amount, unrealized_pnl, unrealized_pnl_pct, signal_id, stop_price, target_price, updated_at
  - 存储模型决策：采用设计的 `stock_code UNIQUE`（最新快照），增加 `positions_history` 表保留每日快照
- [ ] t1_frozen 独立表 (T-04)
  - 创建 DuckDB 表：`(stock_code, buy_date, can_sell_date, shares, cost_price)`
  - 从 positions 字典迁移到独立表
- [ ] 订单状态机 (T-11)
  - 6 态：pending → submitted → partially_filled → filled / cancelled / rejected
  - 纸上交易场景下简化：pending → filled / rejected
- [ ] 7 个枚举实现 (T-12)
  - OrderType, TradeStatus, TradeDirection, SignalQuality, ExecutionMode, TradingState, RejectReason
  - RejectReason 扩展到 11 值（从当前 3 个）
- [ ] risk_events 纳入设计 (T-13)
  - 更新 trading-data-models.md 添加 risk_events 表定义
- [ ] RejectReason 命名统一 (T-16)
  - `REJECT_NO_MARKET_PRICE` → `REJECT_NO_OPEN_PRICE`

### 验收标准

1. trade_records 28 字段全部有值
2. positions 存储为 stock_code UNIQUE 最新快照
3. t1_frozen 独立表可查询
4. RejectReason 11 个值全部可用

---

## CARD-R6.4: TradingService OOP 层

**工作量**：1 天
**优先级**：P1（架构）
**前置依赖**：CARD-R6.1~R6.3
**SOS 映射**：T-01, T-14, T-15

### 交付物

- [ ] `src/trading/service.py` — TradingService
  - 构造函数注入 config, repository, risk_manager
  - 方法：`execute_daily()`, `get_positions()`, `get_trade_records()`, `get_risk_events()`
- [ ] `src/trading/engine.py` — TradingEngine
  - 信号消费 + 撮合逻辑
  - 复用 shared/execution_model + fee_calculator
- [ ] `src/trading/models.py` — 集中 dataclass
  - TradeSignal, TradeRecord, Position, T1Frozen, RiskEvent, TradingRunResult
- [ ] `src/trading/repository.py` — TradingRepository
  - 读写 trade_records, positions, t1_frozen, risk_events 四表
- [ ] Gate 机制对齐 (T-14)
  - 统一使用 `get_validation_gate_decision()` 单一门禁
  - 删除双重门禁逻辑
- [ ] 更新设计文档实现状态 (T-01)
  - trading-algorithm.md / trading-data-models.md / trading-information-flow.md
  - 更新实现状态为"R6 重建完成"

### 验收标准

1. pipeline.py 仅做编排，业务逻辑在 TradingService 中
2. 单一 Gate 门禁（非双重）
3. 设计文档实现状态已更新

---

## CARD-R6.5: 纸上交易验证

**工作量**：1 天
**优先级**：P0（质量闭环）
**前置依赖**：CARD-R6.1~R6.4

### 交付物

- [ ] 5 个交易日纸上交易验证
  - 运行全链路：Data → MSS/IRS/PAS → Validation → Integration → Trading
  - 检查订单生成：有买入 + 有卖出（非全买或全卖）
  - 检查持仓管理：持仓天数 > 1（非 T+1 即卖）
  - 检查风控日志：risk_events 有记录
  - 检查费用计算：commission / stamp_tax / impact_cost 非零
- [ ] 三方一致性验证
  - 同一信号在 Trading 和 Backtest 中：
    - fill_probability 一致
    - 费用计算一致
    - 信号过滤结果一致
  - 输出一致性矩阵
- [ ] 契约测试
  - trade_records 28 字段完整性
  - positions 20 字段完整性
  - t1_frozen 表有数据
- [ ] 验证报告
  - 输出：`artifacts/r6-validation-report.md`
  - 覆盖订单/持仓/风控/费用/一致性

### 验收标准

1. 5 天纸上交易无异常
2. Trading 和 Backtest 成交模型一致性 100%
3. 风控检查全部生效（有 reject 记录）

---

## R6 阶段验收总览

完成以上 5 张卡后，需满足：

1. **成交模型统一**：Trading 和 Backtest 使用 shared/execution_model + fee_calculator
2. **信号过滤统一**：4 层过滤逻辑一致
3. **风控完整**：6 项检查全部实现 + neutrality 信号验证
4. **持仓管理**：条件平仓（非 T+1 无条件清仓）
5. **OOP 架构**：TradingService + RiskManager 可用
6. **数据契约**：trade_records/positions/t1_frozen 字段完整
7. **质量闭环**：5 天纸上交易通过 + 三方一致性验证

**下一步**：进入 R7 Analysis 重建（绩效非零 + 日报）。
