# R5 Backtest 重建 (Qlib 主线) — 执行卡

**阶段目标**：可信的回测结果，Qlib 为主线引擎。
**总工期**：12-14 天
**前置条件**：R4 完成（依赖正确的 integrated_recommendation + validation_gate_decision）
**SOS 覆盖**：docs/sos/backtest 全部 19 项 + sos-enhancements ENH-09

---

## CARD-R5.1: 卖出逻辑重写

**工作量**：2 天
**优先级**：P0（回测退化为"买入→次日即卖"）
**SOS 映射**：GAP-B01, GAP-B12

### 交付物

- [ ] 实现条件触发退出
  - 止损：`drawdown_from_cost = (close - cost_price) / cost_price <= -stop_loss_pct`
  - 止盈：`close >= target_price`
  - 时限平仓：`hold_days >= max_holding_days`
  - 优先级：`stop_loss > take_profit > time_exit`
- [ ] 卖出信号顺延机制
  - 卖出信号在 signal_date 生成，execute_date 执行
  - execute_date 跌停 → 信号顺延到下一可成交日
  - execute_date 停牌 → 信号顺延，停牌日不计入 hold_days
- [ ] 停牌处理 (GAP-B12)
  - 显式停牌检测（volume=0 OR suspend 标记）
  - 停牌日不成交、不计入可卖天数
  - 区分"停牌"和"数据缺失"
- [ ] 删除当前无条件清仓逻辑
  - 位置：`pipeline.py:1102-1185`

### 验收标准

1. 买入后不再次日无条件卖出
2. 持仓可保持多日（直到止损/止盈/时限触发）
3. 跌停日卖出信号顺延
4. 停牌日持仓天数冻结

### 技术要点

- 每日收盘后扫描所有持仓：检查止损 → 止盈 → 时限
- hold_days 计算：排除停牌日
- cost_price 需在买入时记录并持久化

---

## CARD-R5.2: 核心指标与公式修正

**工作量**：1.5 天
**优先级**：P0（指标全部错误或缺失）
**SOS 映射**：GAP-B02, GAP-B03, GAP-B07

### 交付物

- [ ] max_drawdown 公式修正 (B02)
  - **正确**：峰谷追踪 `drawdown_t = (equity_t - peak_t) / peak_t; max_drawdown = min(drawdown_t)`
  - 删除 `(全局最高 - 全局最低) / 全局最高`
  - 位置：`pipeline.py:1520-1522`
- [ ] total_return 口径修正 (B03)
  - **正确**：`total_return = (equity_end - equity_start) / equity_start`
  - equity_end = cash + 持仓市值（含未平仓浮动盈亏）
  - 删除"仅统计已卖出 PnL"的逻辑
  - 位置：`pipeline.py:1513-1514`
- [ ] 核心绩效指标实现 (B07)
  - `annual_return = (1 + total_return) ^ (252/trading_days) - 1`
  - `volatility = std(daily_returns) * sqrt(252)`
  - `sharpe_ratio = (annual_return - risk_free_rate) / volatility`
  - `sortino_ratio = (annual_return - risk_free_rate) / downside_deviation`
  - `calmar_ratio = annual_return / abs(max_drawdown)`
  - `profit_factor = sum(wins) / abs(sum(losses))`
  - `win_rate = count(pnl > 0) / total_trades`
  - `avg_trade / avg_win / avg_loss / max_win / max_loss / fill_rate`

### 验收标准

1. 曲线 [80,100,120,90]：max_drawdown = -25%（非 33.3%）
2. 回测结束有未平仓持仓时 total_return 含浮盈
3. 12 项绩效指标全部有值（非 0）
4. sharpe/sortino/calmar 与手算一致

---

## CARD-R5.3: 信号过滤 + Gate 粒度修正

**工作量**：1 天
**优先级**：P0
**SOS 映射**：GAP-B04, GAP-B05

### 交付物

- [ ] 4 层信号过滤 (B04)
  - 层 1：`final_score < config.min_final_score` → 跳过
  - 层 2：`recommendation` 等级排序（STRONG_BUY>BUY>HOLD>SELL>AVOID），低于阈值跳过
  - 层 3：`direction == "neutral"` → 跳过
  - 层 4：`risk_reward_ratio < 1.0` → 跳过（单信号过滤，非全局阻断）
  - 位置：`pipeline.py:1085-1091`
- [ ] Gate 逐日粒度修正 (B05)
  - 逐日检查：`gate_decision = get_gate(signal_date)`
  - 当日 FAIL → 仅跳过当日信号
  - 其余日正常运行
  - 删除"任何一天 FAIL → 整个回测阻断"
  - 位置：`pipeline.py:995-997`

### 验收标准

1. final_score=50（< 55）的信号被过滤
2. risk_reward_ratio=0.8 的信号被跳过（非阻断整个回测）
3. Gate FAIL 仅影响当日，次日 PASS 正常交易

---

## CARD-R5.4: 仓位与成交模型修正

**工作量**：1.5 天
**优先级**：P0
**SOS 映射**：GAP-B06, GAP-B08, GAP-B09, GAP-B11

### 交付物

- [ ] 仓位基数修正 (B06)
  - **正确**：`equity = cash + 持仓市值`
  - `target_cash = equity × min(signal.position_size, max_position_pct)`
  - `shares = floor(target_cash / entry / 100) × 100`
  - 位置：`pipeline.py:1336-1339`
- [ ] max_positions 约束实现 (B08)
  - 在回测循环中检查 `len(positions) >= config.max_positions` → 跳过新买入
  - 已持有的不影响
- [ ] 成交价滑点 (B09)
  - 买入：`filled_price = open + slippage`
  - 卖出：`filled_price = open - slippage`
  - slippage 从 config 读取
- [ ] 成交概率模型统一 (B11)
  - 复用 `src/shared/execution_model.py`
  - `fill_probability = limit_lock_factor × (0.45 × queue_factor + 0.55 × participation_factor)`
  - 删除简化版 `1 - queue_ratio`

### 验收标准

1. 持仓 3 只时新买入基数包含已有持仓市值
2. 持仓数达到 max_positions 时不再新买入
3. filled_price ≠ open（含滑点）
4. fill_probability 公式与 Trading 一致

---

## CARD-R5.5: integration_mode 模式过滤

**工作量**：1 天
**优先级**：P0
**SOS 映射**：GAP-B10

### 交付物

- [ ] 读取信号中的 `integration_mode` 字段
- [ ] 按模式消费信号
  - top_down：仅消费 TD 模式信号
  - bottom_up：消费 BU 信号 + 活跃度门控
  - dual_verify：消费 DV 信号
  - complementary：消费 COMP 信号
- [ ] BU 模式活跃度门控
  - 查询 `pas_breadth_daily.pas_sa_ratio`
  - 活跃度不足 → 回退 TD 信号 + 标记 `warn_mode_fallback`
- [ ] BacktestState 逐信号标记
  - normal / warn_data_fallback / warn_mode_fallback / blocked_gate_fail

### 验收标准

1. 不同模式信号不会混用
2. BU 模式在活跃度不足时回退 TD 并标记 warn
3. 每笔交易有 backtest_state 标记

---

## CARD-R5.6: Qlib 适配层

**工作量**：2 天
**优先级**：P0（AD-03 裁决 Qlib 为主线引擎）
**SOS 映射**：ENH-09 (E-11)

### 交付物

- [ ] `src/backtest/adapters/qlib_adapter.py`
  - `to_qlib_signal(recommendations: pd.DataFrame) -> QlibSignalFormat`
  - `from_qlib_result(qlib_output) -> BacktestResult`
  - Qlib 数据格式转换（trade_date/stock_code → Qlib instrument/datetime）
  - Qlib 配置模板生成
- [ ] `src/backtest/adapters/local_engine.py`
  - 从 pipeline.py 重构现有本地向量化回测逻辑
  - 作为 Qlib 不可用时的 fallback
  - 实现与 Qlib 相同的 `run(signals) -> BacktestResult` 接口
- [ ] 引擎切换逻辑
  - 默认使用 Qlib
  - Qlib import 失败或初始化失败 → 自动降级到 local_engine + 标记 warn
  - 配置项：`backtest_engine = "qlib" | "local"`

### 验收标准

1. Qlib 可用时 → 使用 Qlib 运行回测
2. Qlib 不可用时 → 自动降级到 local_engine + 日志警告
3. 两个引擎返回相同格式的 BacktestResult
4. to_qlib_signal 正确映射 integrated_recommendation 字段

### 技术要点

- Qlib 需要特定的数据格式（CSI300 instrument 等），adapter 负责格式转换
- local_engine 保留现有回测循环逻辑但封装为类

---

## CARD-R5.7: 数据持久化 + 表结构对齐

**工作量**：1 天
**优先级**：P1
**SOS 映射**：GAP-B14, GAP-B15, GAP-B16, GAP-B17, GAP-B18

### 交付物

- [ ] equity_curve 持久化
  - 写入 DuckDB：`(backtest_id, trade_date, equity, cash, position_value, daily_return)`
  - 供 Analysis(R7) 消费
- [ ] 逐笔费用持久化
  - backtest_trade_records 补增：commission, stamp_tax, impact_cost_bps, slippage, total_fee
  - 使用 `src/shared/fee_calculator.py` 统一计算
- [ ] hold_days 字段
  - 卖出时计算 `hold_days = sell_date - buy_date`（排除停牌日）
  - 写入 backtest_trade_records
- [ ] 7 个 dataclass 实现 (B14)
  - BacktestConfig, AShareFeeConfig, BacktestSignal, BacktestTrade, Position, EquityPoint, BacktestMetrics
- [ ] 7 个枚举实现 (B15)
  - OrderType, TradeStatus, FilledReason, SignalSource, BacktestMode, EngineType, BacktestState
- [ ] 表结构对齐 (B16, B17)
  - backtest_trade_records：补齐设计字段，删除设计中不存在的字段
  - backtest_results：补齐 annual_return, volatility, sharpe_ratio 等

### 验收标准

1. equity_curve 表有数据，Analysis 可读取
2. 逐笔费用可追溯（非仅汇总）
3. hold_days > 0（非 T+1 即卖导致的 =1）

---

## CARD-R5.8: BacktestService OOP 层

**工作量**：1 天
**优先级**：P1（架构）
**前置依赖**：CARD-R5.1~R5.7
**SOS 映射**：GAP-B13

### 交付物

- [ ] `src/backtest/service.py` — BacktestService
  - 构造函数注入 config, repository, engine(Qlib/Local)
  - 方法：`run()`, `get_results()`, `get_equity_curve()`, `get_trade_records()`
- [ ] `src/backtest/engine.py` — BacktestEngine（接口）
  - 定义 `run(signals) -> BacktestResult` 通用接口
  - QlibEngine 和 LocalEngine 均实现此接口
- [ ] `src/backtest/repository.py` — BacktestRepository
  - 读写 backtest_results, backtest_trade_records, equity_curve 三表
- [ ] `src/backtest/models.py` — 集中 dataclass
- [ ] A/B/C 对照框架 (ENH-06)
  - A 组：系统推荐信号
  - B 组：MSS/IRS/PAS 评分偏移基准
  - C 组：等权买入持有（buy & hold）
  - 三组使用相同的 BacktestEngine 运行
- [ ] 重构 pipeline.py
  - 仅保留编排（加载配置 → 调用 BacktestService → 输出日志）
  - 业务逻辑全部在 BacktestService + engine 中

### 验收标准

1. pipeline.py 代码行数从 ~1800 行减少 70%+
2. A/B/C 三组结果可对比
3. BacktestService 可被 Analysis/GUI 导入

---

## CARD-R5.9: 回测验证 + 数据采集增强

**工作量**：1 天
**优先级**：P1（验证）+ P2（ENH-10）
**前置依赖**：CARD-R5.1~R5.8
**SOS 映射**：GAP-B19, ENH-10

### 交付物

- [ ] 3 月区间回测验证
  - 选择有代表性的 3 个月区间（含牛市/熊市/震荡）
  - 对比 Qlib 输出与 local_engine 输出
  - 检查绩效指标合理性（sharpe > -3, drawdown < 80%）
  - 输出验证报告：`artifacts/r5-validation-report.md`
- [ ] 契约测试 `tests/contracts/test_backtest.py`
  - backtest_results 表字段完整性
  - equity_curve 表有数据
  - backtest_trade_records 含逐笔费用
  - hold_days > 0
- [ ] ENH-10 数据采集增强
  - 分批下载：每批 500 只，批间休眠
  - 断点续传：记录已下载日期，中断后从断点继续
  - 进度报告：`{completed}/{total} stocks, ETA: {minutes}m`

### 验收标准

1. Qlib 与 local_engine 在相同信号下绩效指标方向一致
2. 3 个月回测无异常中断
3. 断点续传：中断后重跑不重复下载已有数据

---

## R5 阶段验收总览

完成以上 9 张卡后，需满足：

1. **卖出逻辑**：条件平仓（止损/止盈/时限），非 T+1 无条件清仓
2. **指标正确**：max_drawdown 峰谷追踪，12 项绩效指标全部有值
3. **信号过滤**：4 层过滤 + Gate 逐日粒度
4. **仓位模型**：equity 基数 + max_positions + 滑点 + 统一成交模型
5. **模式支持**：TD/BU/DV/COMP 四模式 + BU 活跃度门控回退
6. **Qlib 主线**：Qlib adapter 可用，local_engine 作为 fallback
7. **持久化完整**：equity_curve + 逐笔费用 + hold_days 全部落库
8. **OOP 架构**：BacktestService + BacktestEngine 接口化
9. **质量闭环**：3 月验证 + 契约测试 + A/B/C 对照

**下一步**：进入 R6 Trading 重建（纸上交易与回测共享成交模型）。
