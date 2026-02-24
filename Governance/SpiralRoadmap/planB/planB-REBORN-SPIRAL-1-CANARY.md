# Reborn 第一螺旋：Canary 闭环（Plan B）

**螺旋编号**: Reborn-Spiral-1  
**更新时间**: 2026-02-24  
**周期**: 2-3个月  
**定位**: 最小可用闭环，不追求全量，只验证“情绪主线能跑通且可解释”

---

## 1. 螺旋目标

1. 在本地数据上跑通 `数据 -> 算法 -> 回测 -> 归因`。
2. 用可审计证据回答“做成了吗、效果如何、能否进入下一螺旋”。
3. 输出 `GO/NO_GO`，不允许“工程完成但业务未知”。

---

## 2. 设计文档绑定（必须对应）

| 设计域 | 文档目录 | 螺旋1要求 |
|---|---|---|
| Data | `docs/design/core-infrastructure/data-layer/` | L1/L2 落库、交易日历一致、数据门禁可审计 |
| MSS | `docs/design/core-algorithms/mss/` | 输出 `mss_panorama`，含 rank/percentile/trend_quality |
| IRS | `docs/design/core-algorithms/irs/` | SW31 口径可校验 |
| PAS | `docs/design/core-algorithms/pas/` | `stock_pas_daily` 产物可用 |
| Validation | `docs/design/core-algorithms/validation/` | `validation_weight_plan` 桥接可追溯 |
| Integration | `docs/design/core-algorithms/integration/` | `integrated_recommendation` 可消费 |
| Backtest | `docs/design/core-infrastructure/backtest/` | 本地回测引擎可复现 |
| Analysis | `docs/design/core-infrastructure/analysis/` | 最小归因与对比归因可落地 |

---

## 3. 范围与圈位映射

- 圈位范围：`S0a -> S0b -> S0c -> S1a -> S1b -> S2a -> S2b -> S2c -> S3(min) -> S3b(min)`
- 数据窗口：最低 `2020-01-01 ~ 2024-12-31`，理想 `2019-01-01 ~ 2026-02-13`

---

## 4. 执行闭环（每圈）

1. `run`: `eq run --date {trade_date} --full-pipeline --validate-each-step`
2. `test`: `python -m scripts.quality.local_quality_check --contracts --governance`
3. `artifact`: 产出 run/test/gate/consumption/review/sync 证据
4. `review`: 更新问题清单与修复结论
5. `sync`: 同步状态与看板

---

## 5. 螺旋1硬门禁

### 5.1 入口门禁

- 本地路径与 DuckDB 可读写（`Config.from_env()`）
- TuShare 采集可运行且重试机制可用

### 5.2 出口门禁

- [ ] 覆盖率 `>=99%`
- [ ] 同窗 `eq run` + `eq backtest` + `eq analysis` 成功
- [ ] 最小归因：`signal/execution/cost`
- [ ] 对比归因：`MSS vs 随机` 与 `MSS vs 技术基线`
- [ ] 明确回答“去掉 MSS 后收益/风险变化”
- [ ] `PLAN-B-READINESS-SCOREBOARD.md` 更新并给 `GO/NO_GO`

---

## 6. 失败处理

1. 任一出口项未通过：判定 `NO_GO`。
2. `NO_GO` 时只允许在螺旋1范围修复，不得提前推进螺旋2。
3. 连续两轮评审 `NO_GO`：必须重估输入数据质量与算法契约，不得跳过。

---

## 7. 与 Plan A 对齐点

1. 同一窗口标准：`2020-2024`（理想 `2019-01-01~2026-02-13`）。
2. 同一归因口径：三分解 + 双对比。
3. 同一证据口径：`run/test/artifact/review/sync`。

---

## 8. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v2.1 | 2026-02-24 | 重写为设计绑定执行合同，删除伪代码式描述，改为可验闭环门禁 |
| v2.0 | 2026-02-23 | 同精度增强版 |
