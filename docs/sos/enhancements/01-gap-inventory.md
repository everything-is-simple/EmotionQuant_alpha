# Enhancements 模块 — 偏差清单

> 审计日期 2026-02-27 | 设计基准 enhancement-selection-analysis + scheduler/monitoring designs

---

## ENH-01 统一运行入口

### E-01 CLI 框架选型偏差 `轻微`

设计: Typer 或 Click。代码: argparse（标准库）。功能等价，减少外部依赖。
设计 7 个子命令全部实现，代码额外有 12 个子命令（irs/pas/validation/fetch-batch 等），均有实现支撑。

### E-02 `--source mock` 路径不完整 `中度`

设计要求 `--source mock` 从 `tests/fixtures/canary_10d/` parquet 读取。
代码中 `--source` 无显式 mock 路径，无 token 时自动退化到 `SimulatedTuShareClient`（内存生成）。

---

## ENH-02 数据预检与限流

### E-03 validate_token() 完全缺失 `致命`

设计要求采集前通过 `tushare.pro_api().trade_cal()` 轻量请求验证 token 有效性。
代码中无此函数，token 无效时在首次正式请求才暴露错误。

### E-04 重试策略无退避等待 `中度`

设计: tenacity 指数退避。代码: 自定义 for 循环，重试次数一致（3 次），
但重试间无等待/退避——纯 immediate retry，可能触发限流。

### E-05 异常类命名不匹配 `中度`

设计: `DataFetchError` / `RateLimitError` / `ConnectionError` 三类。
代码: 仅 `FetchError` 一类。下游无法区分限流和连接失败。

---

## ENH-03 失败产物协议

### E-06 error_manifest 格式不统一 `中度`

设计要求: `error_level`(P0/P1/P2) + `step` + `timestamp` 字段。
代码实际: 缺 `error_level`、缺 `timestamp`、用 `dataset` 替代 `step`。
各模块独立实现 `_write_json()`，无统一写入函数，格式不完全一致。
写入位置为各自 artifacts 目录（非设计的全局单文件）。

---

## ENH-04/05 契约测试与金丝雀

### E-07 金丝雀 parquet 数据包完全缺失 `致命`

设计: `tests/fixtures/canary_10d/` 含 10 天 × 8 表 × 50-100 只的 parquet 包。
实际: 仅 `tests/fixtures/canary/` 下一个交易日历 JSON。
`SimulatedTuShareClient` 作为替代覆盖了 8 类 API，但数据生成逻辑嵌入被测代码中。

### E-08 契约测试目录偏差 `轻微`

设计: `tests/contracts/` + `tests/canary/`。
代码: 均在 `tests/unit/` 下，内容基本完整（7 组契约大部分有覆盖），IRS/PAS 仅间接覆盖。

---

## ENH-06 A/B/C 对照看板

### E-09 C 组等权持有缺失 `中度`

设计: C 组 = 等权买入持有（buy & hold），D 组 = 可选技术基线。
代码: 无等权持有组，技术基线直接成为 C 组。
缺少最基础的 buy & hold 基准，无法证明系统跑赢"什么都不做"。

---

## ENH-08 设计冻结检查

### E-10 实现方向与设计完全不同 `致命`

| 维度 | 设计 | 代码 |
|------|------|------|
| 机制 | SHA256 hash 锚点 — 检测设计文档是否被修改 | DESIGN_TRACE 标记 — 检查代码是否标注设计溯源 |
| 脚本 | `freeze_check.py` | `design_traceability_check.py` |
| 锚点文件 | `freeze_anchors.json` | 不存在 |

两者解决不同问题，互补但不等价。SHA256 守卫在代码中完全未实现。

---

## ENH-09 Qlib 适配层

### E-11 完全缺失 `致命`

设计标记为"核心诉求必需项"（必留 ✅），核心链路依赖度"最高"。
代码中零 Qlib 代码: `src/adapters/qlib_adapter.py` 不存在，`to_qlib_signal()` / `from_qlib_result()` 不存在。
回测由 `src/backtest/pipeline.py` 本地向量化引擎完成。

**AD-03 裁决**: Qlib 为唯一回测引擎。当前代码与此裁决完全矛盾。

---

## 调度编排

### E-12 DAG 编排未完整实现 `中度`

`_run_all()` 为纯串行 for 循环（L1→L2→MSS→IRS→PAS→recommend），缺失:
- MSS/IRS/PAS 并行能力
- Backtest/Trading/Analysis/GUI 步骤
- `blocked_by_dependency` 失败补偿
- 6 个数据就绪检查点的超时机制
- 4 个调度窗口时段限制

### E-13 重试策略偏离 `中度`

设计: 5 次指数退避 (30s→60s→120s→240s→480s)。
代码: 3 次固定 5 分钟间隔 (`MAX_RETRY_COUNT=3, RETRY_INTERVAL_SECONDS=300`)。

---

## 监控告警

### E-14 监控模块仅占位 `致命`

`src/monitoring/quality_monitor.py` 共 16 行，只有 `raise NotImplementedError`。
设计定义了:
- 6 层监控（数据/因子/Validation/集成/交易/系统）
- 9 条关键指标与阈值
- P0/P1/P2 三级告警 + 升级规则
- 通知路径（控制台 + 日志 + 即时消息）

部分监控能力散落在 `quality_gate.py`、`validation/pipeline.py`、`scheduler.py` 中，
但无统一接口、无告警分级、无升级机制。

---

## 目录结构

### E-15 3 个设计指定目录不存在 `中度`

| 设计目录 | 实际 |
|----------|------|
| `src/adapters/` | 不存在（适配器在 `src/data/adapters/`） |
| `tests/contracts/` | 不存在（在 `tests/unit/`） |
| `tests/canary/` | 不存在（在 `tests/fixtures/canary/`） |
