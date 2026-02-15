# EmotionQuant Spiral 依赖图（执行版）

**状态**: Active  
**更新时间**: 2026-02-15  
**定位**: Spiral/ENH 依赖关系与插入点说明。

---

## 1. 主链依赖

```text
S0 -> S1 -> S2 -> S3a -> S3 -> S4 -> S3b -> S4b -> S5 -> S6 -> S7a
```

约束：

1. 仅允许前向依赖，不允许跨圈反向依赖。
2. S2 需要同时覆盖 CP-03/CP-04/CP-10/CP-05。
3. S3/S4/S5 均消费 S2 的 `integrated_recommendation`。
4. S2->S3 迁移前，必须通过命名/治理一致性门禁（`--contracts --governance`）。
5. S3b 依赖 S4：偏差归因必须消费纸上交易结果，不允许只基于回测推断。
6. S4b 依赖 S3b：极端防御阈值必须来自归因结论与压力回放，不允许拍脑袋设值。
7. 各圈收口前必须执行契约行为回归：`tests/unit/scripts/test_contract_behavior_regression.py`。

---

## 1.1 阶段映射依赖

1. 阶段A 对应 `S0-S2`，阶段合同见 `Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`。
2. 阶段B 对应 `S3a-S4b`，阶段合同见 `Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`。
3. 阶段C 对应 `S5-S7a`，阶段合同见 `Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`。
4. 阶段推进必须满足：上一阶段 `退出门禁` 通过，下一阶段 `入口门禁` 才允许启动。

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

## 2.1 专项圈依赖（收益验证与极端防御）

```text
S3 -> S4 -> S3b(归因验证) -> S4b(极端防御)
```

| 专项圈 | 名称 | 挂载圈位 | 依赖 | 价值 |
|---|---|---|---|---|
| S3b | 收益归因验证 | S4 后 | S4 PASS | 高：确认收益来源（信号 vs 执行） |
| S4b | 极端防御专项 | S3b 后 | S3b PASS | 高：降低连续跌停/流动性枯竭回撤 |

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
| `ab_benchmark_report` + `live_backtest_deviation` | S3b/S4b | 归因证据缺失或口径不一致 |
| `extreme_defense_report` | S4b/S5 | 连续跌停/流动性枯竭压力场景未覆盖 |
| `python -m scripts.quality.local_quality_check --contracts --governance` | 圈间推进门禁 | contracts/governance 任一 FAIL |
| `tests/unit/scripts/test_contract_behavior_regression.py` | 圈收口防跑偏门禁 | 行为与命名/契约基线漂移 |
| `.github/workflows/quality-gates.yml` | PR/主干合并门禁 | CI 未配置或检查项缺失 |
| `fetch_progress.json` | S3a 运维恢复 | 进度文件损坏或状态不一致 |
| `scheduler_status.json` | S7a 日常运维 | 调度状态不可查询 |

---

## 5. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.3 | 2026-02-15 | 新增“阶段映射依赖”小节，明确阶段A/B/C与圈序关系并链接阶段模板文档 |
| v1.2 | 2026-02-15 | 主链更新为 `S0->...->S7a` 全执行序；新增 S3b/S4b 专项圈依赖；关键契约新增归因/极端防御证据与防跑偏行为回归门禁 |
| v1.1 | 2026-02-14 | 增加 S2->S3 质量门禁依赖；补充 Schema/contract_version/本地检查/CI workflow 契约依赖 |
| v1.0 | 2026-02-13 | 重建依赖图；纳入 ENH-10/ENH-11 圈位与依赖约束 |
