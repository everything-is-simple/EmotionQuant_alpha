# Plan B 执行清单（同精度版）

**创建时间**: 2026-02-23  
**更新时间**: 2026-02-23  
**状态**: Active  
**用途**: 当 Plan A 失败切换时，Plan B 立即按同精度门禁启动

---

## 1. 总规则

1. Plan B 与 Plan A 使用同一精度标准，不降级。
2. 每圈必须有 `run/test/artifact/review/sync` 五件套。
3. 每个螺旋必须给出 `GO/NO_GO`。

---

## 2. 螺旋1（Canary）

- [ ] 数据窗口最低 `2020-01-01` 到 `2024-12-31`（理想 `2019-01-01` 到 `2026-02-13`）
- [ ] 数据覆盖率 `>=99%`
- [ ] 端到端同窗：数据 -> 算法 -> 回测 -> 归因
- [ ] 归因三分解：`signal/execution/cost`
- [ ] 对比归因：`MSS vs 随机`、`MSS vs 技术基线`
- [ ] 螺旋1结论：`GO/NO_GO`

---

## 3. 螺旋2（Full）

- [ ] 全市场16年数据（2008-2024）落地
- [ ] 多窗口回测（1y/3y/5y+牛熊段）
- [ ] 完整归因（A/B/C + 偏差分解）
- [ ] `S3c/S3d/S3e` MVP门禁通过
- [ ] `S3c/S3d/S3e` FULL门禁通过
- [ ] `S3c/S3d/S3e` 准备可并行、收口必须串行
- [ ] 螺旋2结论：`GO/NO_GO`

---

## 4. 螺旋3（Production）

- [ ] 螺旋2已 `GO`
- [ ] 生产级监控、调度、恢复能力可审计
- [ ] 生产就绪评估：`GO/NO_GO`

---

## 5. 螺旋3.5（Pre-Live）

- [ ] 连续20个交易日零真实下单预演
- [ ] 每日偏差复盘完整（signal/execution/cost）
- [ ] 预演期间0个P0事故
- [ ] 至少1次故障恢复演练通过
- [ ] Pre-Live评审：`GO/NO_GO`
- [ ] 未 `GO` 禁止真实资金实盘

---

## 6. 同步清单

- [ ] `Governance/SpiralRoadmap/planB/PLAN-B-READINESS-SCOREBOARD.md`
- [ ] `Governance/SpiralRoadmap/planB/planB-REBORN-SPIRAL-OVERVIEW.md`
- [ ] `Governance/record/development-status.md`
- [ ] `Governance/record/debts.md`
- [ ] `Governance/record/reusable-assets.md`
