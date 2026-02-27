# Plan A Revalidation 执行清单

**创建时间**: 2026-02-23  
**更新时间**: 2026-02-28  
**状态**: Active  
**用途**: 不重写代码，按新 Plan A 完成闭环重验

---

## 1. 执行规则

1. 本清单只做重验（revalidation），不做 rewrite。
2. 通过标准以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 为准。
3. 每一项都要有 `run/test/artifact/review/sync` 五件套证据。
4. 每个螺旋收口必须附“设计对齐结论”（`docs/design/core-algorithms/`、`docs/design/core-infrastructure/`、`docs/design/enhancements/eq-improvement-plan-core-frozen.md`）。

---

## 2. 螺旋1（Canary）重验

### 2.1 数据窗口重验（S0-S2 输入，P0）

- [x] 执行 `eq fetch-batch --start 20200101 --end 20241231 --batch-size 365 --workers 3`（以本地 2000-2026 全量已落库数据替代重抓）
- [x] 执行 `eq fetch-retry`（窗口内无缺口，等效完成）
- [x] 执行 `eq data-quality-check --comprehensive`（等效校验：trade_cal vs raw_daily 覆盖率审计）
- [x] 产出覆盖率与质量报告，目标覆盖率 `>=99%`（最低窗口：2020-2024；理想：2019-01-01~2026-02-13）
- [x] 固化证据：`artifacts/spiral-s0s2/revalidation/coverage_2020_2024.md`（按年列出可交易日覆盖率与缺口摘要）
- [x] 固化证据：`artifacts/spiral-s0s2/revalidation/coverage_2020_2024.json`（机器可读口径，供 scoreboard/development-status 回填）
- [x] 门禁判定：若任一年度覆盖率 `<99%`，螺旋1 直接 `NO_GO`，仅允许在 S0-S2 修复（当前覆盖率=100%）

### 2.2 端到端同窗重验（S0-S2 -> S3(min) -> S3b(min)，P0）

- [x] 执行 `python -m src.pipeline.main recommend --date 20241220 --mode integrated --with-validation-bridge --evidence-lane release`（CLI 现口径替代 `run --full-pipeline`）
- [x] 执行 `python -m src.pipeline.main backtest --start 20240101 --end 20241220 --engine local_vectorized`
- [x] 执行 `python -m src.pipeline.main analysis --start 20240101 --end 20241220 --ab-benchmark`
- [x] 输出最小归因：`signal/execution/cost` 三分解
- [x] 输出对比归因：`MSS vs 随机基准`、`MSS vs 技术基线(MA/RSI/MACD)`（`benchmark_comparison.py` 实现：随机=同等数量随机选股 seed=42，技术=MA5/MA20+RSI14+MACD 投票 >=2）
- [x] 固化证据：`artifacts/spiral-s3b/20201220/ab_benchmark_report.md`（2020 窗口：MSS -30.4% / Random +3.9% / Technical -10.0%），`artifacts/spiral-s3b/20260219/ab_benchmark_report.md`（2026 窗口：MSS -5.6% / Random -1.7% / Technical -3.8%）
- [x] 固化证据：`artifacts/spiral-s3b/{trade_date}/attribution_summary.json`（必须可追溯到同窗 `backtest`）
- [x] 门禁判定：MSS 在两个窗口均不优于随机与技术基线 → 螺旋1 `NO_GO`，停留 S3/S3b 修复

### 2.3 螺旋1收口判定

- [x] 更新 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md`（螺旋1全部字段）
- [x] 给出螺旋1 `GO/NO_GO`（当前 `NO_GO`，阻断项为“随机/技术基线对比证据缺失”）
- [x] 若 `NO_GO`：只允许在 S0-S2/S3/S3b 修复，不推进螺旋2
- [x] 明确阻断项清零：`5y 覆盖率统计` closed、`MSS vs 基准对比实验` closed（实验已完成，结论为 NO_GO：MSS 未超越基准）

### 2.4 螺旋1设计对齐复核

- [x] `core-algorithms`：MSS/IRS/PAS/Validation/Integration 语义无降级（S0A-S2C 顺序重验 + 失败恢复后全绿）
- [x] `core-infrastructure`：Data/Backtest/Analysis 契约链路无绕过
- [x] `enhancements`：执行动作与 `eq-improvement-plan-core-frozen.md` 一致

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

- [ ] 执行口径采用双档：
  - `MVP`：最小可用（无 FAIL，WARN 可解释）
  - `FULL`：完整生产口径
- [ ] 允许并行准备：`S3c/S3d/S3e` 数据准备与实验可并行
- [ ] 强制串行收口：`S3c -> S3d -> S3e`
- [ ] `S3c`：SW31 行业语义校准证据齐全
- [ ] `S3d`：MSS adaptive 与 probe 真实收益证据齐全
- [ ] `S3e`：Validation 生产校准证据齐全
- [ ] `S4b`：极端防御参数来源可追溯（`S3b + S3e`）

### 3.4 螺旋2收口判定

- [ ] 更新 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md`（螺旋2全部字段）
- [ ] 给出螺旋2 `GO/NO_GO`
- [ ] 螺旋2未 `GO` 前，S5-S7 只可开发，不可宣称生产就绪

### 3.5 螺旋2设计对齐复核

- [ ] `core-algorithms`：S3c/S3d/S3e 的 MVP/FULL 门禁与设计语义一致
- [ ] `core-infrastructure`：Data/Backtest/Trading/Analysis 证据链完整
- [ ] `enhancements`：ENH-09/10 的执行与主计划一致

---

## 4. 螺旋3（Production）准入重验

- [ ] 校验螺旋2状态为 `GO`
- [ ] 校验 `S6` 全链路一致性报告
- [ ] 校验 `S7a` 调度可安装/可观测/可恢复
- [ ] 产出生产就绪评审报告（`GO/NO_GO`）

## 4.5 螺旋3.5（Pre-Live）重验

- [ ] 连续 20 个交易日实盘预演（零真实下单）
- [ ] 每日偏差复盘：`signal/execution/cost` 三分解
- [ ] 完成至少 1 次故障恢复演练（数据延迟/调度失败/重试补偿）
- [ ] 输出预演评审报告（`GO/NO_GO`）
- [ ] 未通过 `GO` 禁止进入任何真实资金实盘

## 4.6 螺旋3设计对齐复核

- [ ] `core-infrastructure/gui`：只读消费，不在展示层做算法重算
- [ ] `core-infrastructure/trading/analysis`：运行日志与偏差复盘可追溯
- [ ] `enhancements`：ENH-07/08/11 的收口证据齐备

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
|| v1.4 | 2026-02-28 | 螺旋1阻断项清零：完成 MSS vs 随机基准/技术基线(MA/RSI/MACD)对比实验（2020+2026 双窗口），结论 NO_GO |
|| v1.3 | 2026-02-26 | 将螺旋1两项 P0 阻断执行化：补充覆盖率与基准对照的必备产物与 NO_GO 判定规则 |
| v1.2 | 2026-02-24 | 增加 PlanA/PlanB 同精度“设计对齐复核”条目：螺旋1/2/3均要求 `docs/design` 与主计划对齐结论 |
| v1.1 | 2026-02-23 | 与 Plan B 对齐精度：canary窗口升级、新增归因对比、S3c/S3d/S3e 双档门禁、增加螺旋3.5 Pre-Live 重验 |
| v1.0 | 2026-02-23 | 首版：按新 Plan A 三螺旋门禁定义 revalidation 执行清单 |
