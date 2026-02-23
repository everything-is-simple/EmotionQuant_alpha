# Plan A Revalidation 执行清单

**创建时间**: 2026-02-23  
**更新时间**: 2026-02-23  
**状态**: Active  
**用途**: 不重写代码，按新 Plan A 完成闭环重验

---

## 1. 执行规则

1. 本清单只做重验（revalidation），不做 rewrite。
2. 通过标准以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 为准。
3. 每一项都要有 `run/test/artifact/review/sync` 五件套证据。

---

## 2. 螺旋1（Canary）重验

### 2.1 数据窗口重验（S0-S2 输入）

- [ ] 执行 `eq fetch-batch --start 20220101 --end 20241231 --batch-size 365 --workers 3`
- [ ] 执行 `eq fetch-retry`
- [ ] 执行 `eq data-quality-check --comprehensive`
- [ ] 产出覆盖率与质量报告，目标覆盖率 `>=99%`

### 2.2 端到端同窗重验（S0-S2 -> S3(min) -> S3b(min)）

- [ ] 执行 `eq run --date 20241220 --full-pipeline --validate-each-step`
- [ ] 执行 `eq backtest --start 20240101 --end 20241220 --engine local`
- [ ] 执行 `eq analysis --start 20240101 --end 20241220 --ab-benchmark`
- [ ] 输出最小归因：`signal/execution/cost` 三分解

### 2.3 螺旋1收口判定

- [ ] 更新 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md`（螺旋1全部字段）
- [ ] 给出螺旋1 `GO/NO_GO`
- [ ] 若 `NO_GO`：只允许在 S0-S2/S3/S3b 修复，不推进螺旋2

---

## 3. 螺旋2（Full）重验

### 3.1 全历史数据落地

- [ ] 执行 16 年历史数据入库（`2008-01-01` 到 `2024-12-31`）
- [ ] 产出全市场数据质量报告

### 3.2 多窗口回测与完整归因

- [ ] 完成 1y/3y/5y 回测窗口
- [ ] 完成 A/B/C 对照
- [ ] 完成 `signal/execution/cost` 全分解与收益来源结论

### 3.3 校准与防御链路重验

- [ ] `S3c`：SW31 行业语义校准证据齐全
- [ ] `S3d`：MSS adaptive 与 probe 真实收益证据齐全
- [ ] `S3e`：Validation 生产校准证据齐全
- [ ] `S4b`：极端防御参数来源可追溯（`S3b + S3e`）

### 3.4 螺旋2收口判定

- [ ] 更新 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md`（螺旋2全部字段）
- [ ] 给出螺旋2 `GO/NO_GO`
- [ ] 螺旋2未 `GO` 前，S5-S7 只可开发，不可宣称生产就绪

---

## 4. 螺旋3（Production）准入重验

- [ ] 校验螺旋2状态为 `GO`
- [ ] 校验 `S6` 全链路一致性报告
- [ ] 校验 `S7a` 调度可安装/可观测/可恢复
- [ ] 产出生产就绪评审报告（`GO/NO_GO`）

---

## 5. 同步清单（每圈固定）

- [ ] `Governance/specs/spiral-{spiral_id}/final.md`
- [ ] `Governance/record/development-status.md`
- [ ] `Governance/record/debts.md`
- [ ] `Governance/record/reusable-assets.md`
- [ ] `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`
- [ ] `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md`

---

## 6. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-02-23 | 首版：按新 Plan A 三螺旋门禁定义 revalidation 执行清单 |
