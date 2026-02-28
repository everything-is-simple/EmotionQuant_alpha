# 02 — 风险评估（Analysis 篇）

对 01-gap-inventory.md 中的每项差异进行业务风险与技术债评估。

**风险等级**: P0（阻塞性/数据正确性） | P1（功能完整性） | P2（体验/可维护性）

---

## 一、阻塞性风险（P0）— 数据正确性与系统可用性

### GAP-A07 equity_curve 跨模块断裂

- **业务风险**: **最高**。这是整个 Analysis 层绩效计算的阻塞项。没有 equity_curve，analysis-algorithm.md §2 中定义的所有绩效指标（Sharpe/Sortino/Calmar/年化收益/波动率）都无法计算。
- **当前影响**: GAP-A01 的根因。performance_metrics 表中 7 个字段永远为 0.0，下游任何依赖这些指标的决策（如 GUI 展示、治理门禁）都会得到无意义的数据。
- **技术债**: 需要修改 Backtest 模块（src/backtest/pipeline.py），在 `backtest_results` 表中新增 equity_curve 列（JSON 序列化），或者单独建表存储。
- **修复前置依赖**: 无。可独立修复。
- **修复影响面**: Backtest 持久化逻辑 + Analysis 读取逻辑。

### GAP-A01 绩效指标全部硬编码 0.0

- **业务风险**: **最高**。performance_metrics 表中 annual_return / volatility / sharpe_ratio / sortino_ratio / calmar_ratio / profit_factor / avg_holding_days 全为 0.0，任何读取该表做分析或展示的下游模块都会收到错误数据。
- **当前影响**: 如果 GUI 或治理看板读取 performance_metrics 表展示分析结果，会显示「年化收益0%、夏普比率0」等误导性数据。
- **技术债**: 在 GAP-A07 修复后，需要在 Analysis 层实现 compute_performance_metrics 逻辑。
- **修复前置依赖**: GAP-A07（equity_curve 持久化）。
- **修复影响面**: src/analysis/pipeline.py ab_benchmark 子任务。

### GAP-A06 信号偏差计算逻辑不一致

- **业务风险**: **高**。偏差归因的 signal_deviation 使用 final_score 差值作为代理，与设计中的 forward_return_5d 语义不同。这意味着：
  - 代码输出的 signal_deviation 量纲是「评分单位 / 100」，而非「收益率」
  - 与 execution_deviation（收益率量纲）和 cost_deviation（费率量纲）不可加
  - `total_deviation = signal_deviation + execution_deviation - cost_deviation` 是量纲混合的无意义计算
- **当前影响**: live_backtest_deviation 表中的数据在物理意义上不自洽。dominant_component 判断基于不同量纲的绝对值比较，结论不可靠。
- **技术债**: 需要引入 forward_return_5d 计算（需要 T+5 行情数据）或者修改设计接受 score-based proxy。
- **修复前置依赖**: 需确认方向（改代码还是改设计）。

---

## 二、功能完整性风险（P1）— 设计承诺但未实现

### GAP-A02 CP-08 最小闭环未落地

- **业务风险**: **中高**。设计明确定义了 CP-08 作为最小可运行闭环，是 S3b 的交付口径。当前代码虽然实现了 S3b 的 3 个子任务，但流程架构与设计不一致。
- **当前影响**: 代码能运行并产出结果，但与设计中「绩效→归因→日报→落库→导出」的完整链路不一致。如果其他团队或文档引用 CP-08 闭环作为已完成里程碑，会产生误解。
- **技术债**: 中等。需要决策是将代码改为设计定义的闭环，还是更新设计以反映实际实现。

### GAP-A03 日报生成完全缺失

- **业务风险**: **中**。日报是设计中 Analysis 层的核心输出之一，供运营和风控日常复盘使用。
- **当前影响**: 无日度分析摘要产出。用户需要手动从 artifacts 中拼凑信息。
- **技术债**: 高。需要实现完整的日报生成链路（读取 L3 输出 → 汇总 → 渲染 → 落库 → 导出），涉及多个新函数和 L3 表的读取。
- **修复前置依赖**: GAP-A11（L3 直读）、GAP-A01（绩效指标）。

### GAP-A04 风险分析完全缺失

- **业务风险**: **中**。风险等级分布和行业集中度是风控基本面板。
- **当前影响**: 无风险维度的分析输出。无法检测风险拐点或集中度过高。
- **技术债**: 中等。风险分析相对独立，可以增量实现。
- **修复前置依赖**: 需要读取 positions 表和 integrated_recommendation。

### GAP-A08 + GAP-A12 回测交易记录字段缺失（费用明细 + hold_days）

- **业务风险**: **中**。
  - 无逐笔费用 → 无法做精确的费用归因（当前 bt_cost_rate=0 是 GAP-A15 的根因）
  - 无 hold_days → 无法计算 avg_holding_days（当前硬编码 0.0 是 GAP-A01 的一部分）
- **当前影响**: 偏差归因中的 cost_deviation 维度不可信。
- **技术债**: 需要修改 Backtest 模块的持久化逻辑，在 backtest_trade_records 中增加 commission / stamp_tax / transfer_fee / impact_cost / hold_days 字段。
- **修复影响面**: src/backtest/pipeline.py 回测循环中的 trade_rows 构建。

### GAP-A11 L3 算法输出表直读缺失

- **业务风险**: **中**。Analysis 层的设计定位是「消费 L3 算法输出」，但代码中只消费了 integrated_recommendation 和回测结果，未直接读取 L3 源表。
- **当前影响**: 日报中无法获取市场温度、行业轮动等信息。
- **技术债**: 低。读取逻辑简单，但前提是 GAP-A03（日报功能）需要先实现。

---

## 三、体验/可维护性风险（P2）— 不影响正确性但影响长期维护

### GAP-A05 数据模型类全部缺失

- **业务风险**: **低**。当前代码使用 dict/DataFrame 可以正常运行。
- **当前影响**: 无类型安全、无自动补全、无字段校验。代码可读性和维护性较差。
- **技术债**: 中等。引入 dataclass 体系需要重构数据传递方式，但不影响业务逻辑。
- **建议**: 如果近期有大量新功能开发（日报、风险分析），可以借机引入；如果只是修复现有功能，可以延后。

### GAP-A09 Dashboard 快照缺失

- **业务风险**: **低到中**。取决于 GUI 模块是否已经在读取此快照。
- **当前影响**: GUI 如果需要 Analysis 数据，需要直接查 DuckDB 表，而非读取预构建快照。
- **技术债**: 低。实现简单（汇总现有数据为一个 JSON）。
- **修复前置依赖**: GAP-A01（绩效）、GAP-A04（风险）需要先有数据才能构建快照。

### GAP-A10 CSV 导出缺失

- **业务风险**: **低**。CSV 主要用于人工分析和外部工具导入。
- **当前影响**: 数据在 DuckDB 中可查询，在 JSON/Markdown 中可读。CSV 是额外便利。
- **技术债**: 极低。几行代码即可实现。

### GAP-A13 API 签名差异

- **业务风险**: **极低**。额外参数不破坏兼容性。
- **修复**: 更新 analysis-api.md 补充 benchmark_mode 参数说明。

### GAP-A14 产物路径差异

- **业务风险**: **极低**。API 文档已更新，算法文档未同步。
- **修复**: 更新 analysis-algorithm.md §1 的路径描述。

### GAP-A15 bt_cost_rate 硬编码 0

- **业务风险**: **低**（GAP-A08 的下游影响，修复 A08 后自动解决）。

### GAP-A16 Markdown 渲染简化

- **业务风险**: **极低**。当前实现满足需求。
- **修复**: 可延后到需要复杂报告格式时再引入模板系统。

---

## 风险矩阵总览

| 优先级 | GAP ID | 风险描述 | 修复前置 |
|--------|--------|----------|----------|
| P0 | A07 | equity_curve 未持久化 → 阻塞所有绩效计算 | 无 |
| P0 | A01 | 7个绩效指标硬编码0 → 数据不可信 | A07 |
| P0 | A06 | signal_deviation 量纲错误 → 偏差归因不自洽 | 需决策 |
| P1 | A08+A12 | 回测交易记录缺字段 → 费用/持仓归因不可能 | 无 |
| P1 | A02 | CP-08闭环未落地 → 交付口径不一致 | A01+A03 |
| P1 | A03 | 日报缺失 → 无日度分析摘要 | A11+A01 |
| P1 | A04 | 风险分析缺失 → 无风控面板 | 无 |
| P1 | A11 | L3直读缺失 → 日报无数据源 | 无 |
| P2 | A05 | 数据模型缺失 → 可维护性差 | 无 |
| P2 | A09 | Dashboard快照缺失 → GUI需直查DB | A01+A04 |
| P2 | A10 | CSV导出缺失 → 外部分析不便 | 无 |
| P2 | A13 | API参数未同步 → 文档过时 | 无 |
| P2 | A14 | 产物路径不一致 → 文档自相矛盾 | 无 |
| P2 | A15 | bt_cost_rate=0 → 费用偏差不准 | A08 |
| P2 | A16 | 简化渲染 → 无模板 | 无 |
