# EmotionQuant Spiral 依赖图（执行版）

**状态**: Active  
**更新时间**: 2026-02-14  
**定位**: Spiral/ENH 依赖关系与插入点说明。

---

## 1. 主链依赖

```text
S0 -> S1 -> S2 -> S3 -> S4 -> S5 -> S6
```

约束：

1. 仅允许前向依赖，不允许跨圈反向依赖。
2. S2 需要同时覆盖 CP-03/CP-04/CP-10/CP-05。
3. S3/S4/S5 均消费 S2 的 `integrated_recommendation`。
4. S2->S3 迁移前，必须通过命名/治理一致性门禁（`--contracts --governance`）。

---

## 2. 扩展圈依赖（ENH）

```text
S2 -> S3a(ENH-10) -> S3
S6 -> S7a(ENH-11)
```

| ENH | 名称 | 挂载圈位 | 依赖 | 价值 |
|---|---|---|---|---|
| ENH-10 | 数据采集增强 | S3a（S2 后、S3 前） | S2 PASS | 高：提升历史数据准备效率 |
| ENH-11 | 定时调度器 | S7a（S6 后） | S6 PASS | 中：提升日常运营自动化 |

---

## 3. 层级依赖（数据口径）

1. L2 只读 L1。
2. L3 只读 L1/L2。
3. L4 只读 L1/L2/L3。
4. ENH-10/11 只增强执行与调度，不改变 L1-L4 语义。

---

## 4. 关键契约依赖

| 上游产物 | 下游消费 | 阻断条件 |
|---|---|---|
| `raw_*` / `raw_trade_cal` | L2 快照（S0c） | 数据缺失或交易日不匹配 |
| `mss_panorama` | S1b/S2a | 评分字段不完整 |
| `irs_industry_daily` + `stock_pas_daily` | S2b | 任一主信号缺失 |
| `validation_gate_decision` | S2b/S3/S4 | gate 不可追溯或 FAIL 未修复 |
| `docs/naming-contracts.schema.json`（`nc-v1`） | S2/S3/S4/S5 运行契约 | Schema 缺失或阈值/枚举与文档漂移 |
| `validation_gate_decision.contract_version` | S3/S4/S5 执行前检查 | `contract_version != "nc-v1"` |
| `integrated_recommendation` | S3/S4/S5 | 缺 A 股规则门禁字段或 RR 执行门槛口径不一致 |
| `python -m scripts.quality.local_quality_check --contracts --governance` | 圈间推进门禁 | contracts/governance 任一 FAIL |
| `.github/workflows/quality-gates.yml` | PR/主干合并门禁 | CI 未配置或检查项缺失 |
| `fetch_progress.json` | S3a 运维恢复 | 进度文件损坏或状态不一致 |
| `scheduler_status.json` | S7a 日常运维 | 调度状态不可查询 |

---

## 5. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.1 | 2026-02-14 | 增加 S2->S3 质量门禁依赖；补充 Schema/contract_version/本地检查/CI workflow 契约依赖 |
| v1.0 | 2026-02-13 | 重建依赖图；纳入 ENH-10/ENH-11 圈位与依赖约束 |
