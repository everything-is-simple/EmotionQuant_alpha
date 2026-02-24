# Plan B 执行清单（设计绑定版）

**创建时间**: 2026-02-23  
**更新时间**: 2026-02-24  
**状态**: Active  
**用途**: Plan B 切换后的唯一执行清单（按螺旋闭环执行）

---

## 1. 总规则

1. 只做闭环重建，不做文档式推进。
2. 每圈必须有：`run/test/artifact/review/sync`。
3. 每螺旋必须有：`GO/NO_GO`，且同步业务看板。
4. 所有动作必须可映射到 `docs/design/**`。

---

## 2. 螺旋1（Canary）执行项

### 2.1 数据闭环（S0-S2 输入）

- [ ] `eq fetch-batch --start 20200101 --end 20241231 --batch-size 365 --workers 3`
- [ ] `eq fetch-retry`
- [ ] `eq data-quality-check --comprehensive`
- [ ] 本地窗口覆盖率 `>=99%`（理想扩到 `2019-01-01 ~ 2026-02-13`）
- [ ] `data_readiness_gate` 可审计

### 2.2 算法与集成闭环（S1/S2）

- [ ] `eq run --date {trade_date} --full-pipeline --validate-each-step`
- [ ] MSS/IRS/PAS/Validation/Integration 产物齐备并符合契约
- [ ] `validation_weight_plan` 桥接链可追溯

### 2.3 回测与归因闭环（S3(min)/S3b(min)）

- [ ] `eq backtest --start {start} --end {end} --engine local`
- [ ] `eq analysis --start {start} --end {end} --ab-benchmark`
- [ ] 最小归因：`signal/execution/cost`
- [ ] 对比归因：`MSS vs 随机`、`MSS vs 技术基线`
- [ ] 输出“去掉 MSS 后收益/风险变化”结论

### 2.4 螺旋1收口

- [ ] 更新 `PLAN-B-READINESS-SCOREBOARD.md` 螺旋1字段
- [ ] 输出 `GO/NO_GO`
- [ ] `NO_GO` 时仅允许在螺旋1内修复

---

## 3. 螺旋2（Full）执行项

### 3.1 数据与采集增强（S3a/S3ar）

- [ ] 16年落库：`2008-01-01 ~ 2024-12-31`
- [ ] 采集增强/稳定性证据齐全（断点续传、重试、锁恢复）
- [ ] 全市场质量报告可复核

### 3.2 完整回测与归因（S3/S4/S3b）

- [ ] 多窗口回测：`1y/3y/5y + 典型牛熊段`
- [ ] A/B/C 对照完成
- [ ] 完整归因完成并可回答收益来源

### 3.3 校准与极端防御（S3c/S3d/S3e/S4b）

- [ ] `S3c/S3d/S3e` 达到 `MVP`
- [ ] `S3c/S3d/S3e` 达到 `FULL`
- [ ] 准备可并行、收口宣告必须串行
- [ ] `S4b` 参数来源可追溯（`S3b + S3e`）

### 3.4 螺旋2收口

- [ ] 更新 `PLAN-B-READINESS-SCOREBOARD.md` 螺旋2字段
- [ ] 输出 `GO/NO_GO`
- [ ] 螺旋2未 `GO` 时，螺旋3仅允许开发，不得宣称生产就绪

---

## 4. 螺旋3（Production）执行项

### 4.1 S5-S7a

- [ ] GUI 仅消费真实产物（只读，不二次计算）
- [ ] 全链路重跑一致性通过
- [ ] 调度安装/状态/历史/重试可审计

### 4.2 螺旋3.5（Pre-Live）

- [ ] 连续20交易日零真实下单预演
- [ ] 每日偏差复盘（signal/execution/cost）
- [ ] 至少1次故障恢复演练通过
- [ ] 预演期间 0 个 P0 事故

### 4.3 螺旋3收口

- [ ] 更新 `PLAN-B-READINESS-SCOREBOARD.md` 螺旋3与3.5字段
- [ ] 输出 `GO/NO_GO`
- [ ] 未 `GO` 禁止进入真实资金

---

## 5. 每圈同步清单

- [ ] `Governance/specs/spiral-{spiral_id}/final.md`
- [ ] `Governance/record/development-status.md`
- [ ] `Governance/record/debts.md`
- [ ] `Governance/record/reusable-assets.md`
- [ ] `Governance/SpiralRoadmap/planB/PLAN-B-READINESS-SCOREBOARD.md`

---

## 6. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v2.1 | 2026-02-24 | 改为设计绑定执行清单：按螺旋闭环组织，不再按理想化模块罗列 |
| v2.0 | 2026-02-23 | 实事求是版 |
