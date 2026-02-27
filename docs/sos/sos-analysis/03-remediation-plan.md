# 03 — 修复方案（Analysis 篇）

分级、分批、可执行的急救路线。

---

## 修复策略总纲

**核心原则**: 先修数据通路（P0），再补功能（P1），最后增强体验（P2）。

**方向判断（待决策）**:
- 选项 A：**以设计为准修代码** — 代码向设计文档对齐，实现设计中定义的完整功能
- 选项 B：**以代码为准修设计** — 设计文档降级，标记当前实现为 MVP，未实现部分移入 Future 口径
- 选项 C：**分层对齐** — P0 以设计为准修代码，P1/P2 以代码为准修设计，后续增量补齐

**建议**: 选项 C。理由：
1. P0 数据正确性问题必须修代码（0.0 值不可接受）
2. P1 日报/风险等可以标记为 Future，不阻塞当前螺旋
3. P2 纯文档同步

---

## 第一批：P0 紧急修复（阻塞性 — 数据正确性）

### 批次 1a：打通 equity_curve 数据通路

**目标**: 解除 GAP-A07 阻塞，为绩效计算提供数据基础

**修改范围**: `src/backtest/pipeline.py`

**具体步骤**:
1. 在 `BACKTEST_RESULT_COLUMNS` 中新增 `equity_curve` 列（存储 JSON 字符串）
2. 在 `run_backtest()` 结尾构建 result_frame 时，将 `equity_curve` 序列化为 JSON 字符串写入
3. 对于已有的 backtest_results 表，DuckDB 的 `ALTER TABLE ADD COLUMN` 会自动处理
4. 验证：运行回测后检查 `SELECT equity_curve FROM backtest_results` 非空

**影响面**: 仅 Backtest 持久化逻辑。不影响现有回测计算。

**工作量估算**: ~30 分钟

**覆盖 GAP**: A07

---

### 批次 1b：实现真实绩效指标计算

**目标**: 解除 GAP-A01，让 performance_metrics 表中的数据真实有效

**修改范围**: `src/analysis/pipeline.py`

**具体步骤**:
1. 新增 `_compute_performance_metrics(equity_curve, trades)` 函数，实现设计文档中的算法：
   - daily_returns = equity[t] / equity[t-1] - 1
   - annual_return = (1 + total_return)^(252/N) - 1
   - volatility = std(daily_returns) × sqrt(252)
   - sharpe = sqrt(252) × (mean(r) - rf/252) / std(r)
   - sortino = sqrt(252) × (mean(r) - rf/252) / sqrt(mean(min(r-rf/252,0)^2))
   - calmar = annual_return / abs(max_drawdown)
   - 异常处理：std=0→Sharpe/Sortino置0、max_drawdown=0→Calmar置0、无交易→全部置0
2. 在 ab_benchmark 子任务中，从 backtest_results 读取 equity_curve JSON，反序列化后调用此函数
3. 在 ab_benchmark 子任务中，从 backtest_trade_records 读取 sell 方向的 pnl 计算 profit_factor
4. 替换硬编码的 0.0 值
5. 验证：运行 analysis 后检查 performance_metrics 表中 sharpe_ratio 等字段非零

**前置依赖**: 批次 1a 完成

**工作量估算**: ~1.5 小时

**覆盖 GAP**: A01

---

### 批次 1c：修复偏差归因量纲问题

**目标**: 解除 GAP-A06，让 live_backtest_deviation 数据物理自洽

**修改范围**: `src/analysis/pipeline.py` 偏差归因子任务

**方案选择（需决策）**:

**方案 C1：改代码对齐设计 — 使用 forward_return_5d**
- 从 raw_daily 读取 T+5 收盘价，计算 forward_return_5d
- signal_deviation = mean(live.forward_return_5d) - mean(bt.forward_return_5d)
- 所有偏差维度统一为收益率量纲
- 优点：物理自洽，可加性正确
- 缺点：需要 T+5 行情数据（可能超出回测窗口）

**方案 C2：改设计接受 score-based proxy**
- 保留当前代码逻辑
- 更新设计文档：signal_deviation 定义改为 (live_score_mean - bt_score_mean) / 100
- 补充说明：signal_deviation 为信号强度代理偏差，非收益偏差
- 优点：零代码改动
- 缺点：total_deviation 仍然是量纲混合的

**方案 C3：混合 — 归一化所有偏差到同一量纲**
- 保留 score-based signal_deviation
- 但在汇总时不做加法，改为分别报告三个维度
- 移除 total_deviation 和 dominant_component（或改为各自排名）
- 优点：承认量纲不同，避免误导
- 缺点：需修改代码和设计

**建议**: 方案 C1（如果数据可用）或方案 C3（如果 T+5 数据不可用）

**工作量估算**: C1 ~2小时 / C2 ~30分钟 / C3 ~1小时

**覆盖 GAP**: A06

---

## 第二批：P1 功能补齐

### 批次 2a：回测交易记录补充费用和持仓字段

**目标**: 解除 GAP-A08 + A12 + A15

**修改范围**: `src/backtest/pipeline.py`

**具体步骤**:
1. 在 `BACKTEST_TRADE_COLUMNS` 中新增：`commission`, `stamp_tax`, `transfer_fee`, `impact_cost`, `total_fee_per_trade`, `hold_days`
2. 在回测循环的 buy/sell trade_rows 构建中填充实际费用值
3. hold_days：在 sell 时计算 `(sell_date - buy_date).days`（需在 positions 中记录 buy_date）
4. 验证：查询 backtest_trade_records 确认新字段有值

**影响面**: Backtest 回测循环 + 持久化

**工作量估算**: ~1.5 小时

**覆盖 GAP**: A08, A12, A15（A15 修复后在 analysis 中读取真实 bt_cost_rate）

---

### 批次 2b：风险分析模块

**目标**: 解除 GAP-A04

**修改范围**: `src/analysis/pipeline.py` 或新建 `src/analysis/risk.py`

**具体步骤**:
1. 实现 `_calculate_risk_distribution(recommendations)` — 基于 neutrality 的三级分布
2. 实现 `_analyze_concentration(positions)` — HHI 计算
3. 在 run_analysis 中新增 `--risk-analysis` 子任务
4. 持久化到新表或扩展现有表
5. 验证：检查风险输出字段

**前置依赖**: 无（可并行）

**工作量估算**: ~2 小时

**覆盖 GAP**: A04

---

### 批次 2c：L3 直读 + 日报生成

**目标**: 解除 GAP-A03 + A11

**修改范围**: `src/analysis/pipeline.py`

**具体步骤**:
1. 新增 L3 表读取函数：`_read_mss_panorama()`, `_read_irs_industry_daily()`, `_read_stock_pas_daily()`
2. 实现 `_generate_daily_report(trade_date)` — 汇总市场/行业/信号/绩效/风险
3. 实现简化的 Markdown 渲染（不需要完整模板系统）
4. 创建 `daily_report` 表并持久化
5. 在 run_analysis 中新增 `--daily-report` 子任务
6. 验证：运行后检查 daily_report 表和 Markdown 文件

**前置依赖**: 批次 1b（绩效指标）、批次 2b（风险数据）

**工作量估算**: ~3 小时

**覆盖 GAP**: A03, A11

---

### 批次 2d：CP-08 闭环对齐

**目标**: 解除 GAP-A02

**修改范围**: `src/analysis/pipeline.py` 或设计文档

**方案选择（需决策）**:

**方案 D1：新增 run_minimal 入口**
- 在 run_analysis 基础上新增 `run_minimal(trade_date, start_date, end_date)` 入口
- 按设计串行执行：compute_metrics → attribute_signals → generate_daily_report → persist/export
- 保留现有 run_analysis 的三子任务模式

**方案 D2：更新设计文档**
- 将 CP-08 闭环定义改为当前三子任务模式
- 标注 run_minimal 为「规划口径」

**建议**: 方案 D1（如果已完成 1b+2b+2c）或方案 D2（如果决定延后 2b+2c）

**覆盖 GAP**: A02

---

## 第三批：P2 体验增强 + 文档同步

### 批次 3a：文档同步（快速）

**具体步骤**:
1. analysis-api.md：补充 `benchmark_mode` 参数说明 → 覆盖 A13
2. analysis-algorithm.md §1：更新产物路径为 `artifacts/spiral-s3b/{anchor_date}/` → 覆盖 A14

**工作量估算**: ~15 分钟

**覆盖 GAP**: A13, A14

---

### 批次 3b：Dashboard 快照 + CSV 导出

**具体步骤**:
1. 实现 `_build_dashboard_snapshot()` — 汇总绩效/归因/风险/偏差为 JSON → 覆盖 A09
2. 实现 `_export_csv(frame, filename)` — DataFrame to CSV → 覆盖 A10

**前置依赖**: 批次 1b + 2b

**工作量估算**: ~1 小时

**覆盖 GAP**: A09, A10

---

### 批次 3c：数据模型引入（可选）

**具体步骤**:
1. 创建 `src/analysis/models.py`，定义核心 dataclass
2. 优先引入：PerformanceMetrics, SignalAttribution, LiveBacktestDeviation
3. 逐步重构 pipeline.py 中的 dict 传递为 dataclass

**工作量估算**: ~2 小时（仅核心模型），~4 小时（完整 14 个模型）

**覆盖 GAP**: A05

---

### 批次 3d：Markdown 模板（可选，建议延后）

**覆盖 GAP**: A16

---

## 修复路线图

```
第一批 P0（必须）:
  1a equity_curve持久化 ──→ 1b 绩效指标计算 ──→ 1c 偏差量纲修复
                                                       │
第二批 P1（功能补齐）:                                    │
  2a 回测字段补充（可并行）                                │
  2b 风险分析（可并行）──→ 2c 日报生成 ──→ 2d CP-08对齐 ──┘
                                │
第三批 P2（增强）:                │
  3a 文档同步（随时可做）          │
  3b Dashboard+CSV ←─────────────┘
  3c 数据模型（可选）
  3d Markdown模板（延后）
```

## 工作量估算汇总

| 批次 | 内容 | 估算 | 覆盖 GAP |
|------|------|------|----------|
| 1a | equity_curve 持久化 | 30 min | A07 |
| 1b | 绩效指标计算 | 1.5 h | A01 |
| 1c | 偏差量纲修复 | 1-2 h | A06 |
| 2a | 回测字段补充 | 1.5 h | A08, A12, A15 |
| 2b | 风险分析 | 2 h | A04 |
| 2c | L3直读+日报 | 3 h | A03, A11 |
| 2d | CP-08闭环 | 1-2 h | A02 |
| 3a | 文档同步 | 15 min | A13, A14 |
| 3b | Dashboard+CSV | 1 h | A09, A10 |
| 3c | 数据模型 | 2-4 h | A05 |
| 3d | Markdown模板 | 延后 | A16 |
| **总计** | | **~14-18 h** | **全部 16 项** |
