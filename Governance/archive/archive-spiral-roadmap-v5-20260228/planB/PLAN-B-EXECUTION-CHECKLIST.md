# Plan B 执行清单（微圈体系版）

**创建时间**: 2026-02-23  
**更新时间**: 2026-02-25  
**状态**: Active  
**用途**: Plan B 切换后的唯一执行清单（按 PB-1.1~PB-3.4 微圈执行）

---

## 1. 总规则

1. 只做闭环重建，不做文档式推进。
2. 每微圈必须有：`run/test/artifact/gate_report/consumption/review/sync`。
3. 每螺旋必须有：`GO/NO_GO`，且同步业务看板。
4. 所有动作必须可映射到 `docs/design/**`。
5. `gate_report.md` 必须包含 §Design-Alignment-Fields（字段级设计对齐）。

---

## 2. 螺旋1（Canary）执行项

### PB-1.1 数据闭环（对应 Plan A S0a-S0c）

- [ ] `eq run --date {trade_date} --source tushare`
- [ ] 本地窗口覆盖率 >=99%（2020-2024，理想 2019-01-01~2026-02-13）
- [ ] `raw_daily` 字段与 DDL 一一对应
- [ ] `Config.from_env()` 无硬编码
- [ ] gate_report + §Design-Alignment-Fields

### PB-1.2 算法闭环（对应 Plan A S1a-S2c）

- [ ] `eq run --date {trade_date} --full-pipeline --validate-each-step`
- [ ] MSS/IRS/PAS/Validation/Integration 产物齐备且符合契约
- [ ] `validation_weight_plan` 桥接链可追溯
- [ ] 集成 4模式可审计 + 硬约束硬运行
- [ ] gate_report + §Design-Alignment-Fields

### PB-1.3 最小回测闭环（对应 Plan A S3(min)）

- [ ] `eq backtest --engine {engine} --start {start} --end {end}`
- [ ] T+1/涨跌停/费用模型与 backtest-test-cases 一致
- [ ] A/B/C 对照指标摘要可产出
- [ ] gate_report + §Design-Alignment-Fields

### PB-1.4 最小归因闭环（对应 Plan A S3b(min)）

- [ ] `eq analysis --start {start} --end {end} --ab-benchmark`
- [ ] 三分解：`signal/execution/cost`
- [ ] 双对比：MSS 超额 >5%（vs随机）、>3%（vs技术基线）
- [ ] 夏普 >1.0 / 回撤 <20% / 胜率 >50%
- [ ] `dominant_component≠'none'` 比例 >=50%
- [ ] gate_report + §Design-Alignment-Fields

### 螺旋1收口

- [ ] 更新 `PLAN-B-READINESS-SCOREBOARD.md` 螺旋1
- [ ] 输出 `GO/NO_GO`

---

## 3. 螺旋2（Full）执行项

### PB-2.1 采集扩窗（对应 Plan A S3a/S3ar）

- [ ] 16年落库（2008-2024）覆盖率 >=99%
- [ ] 采集稳定性证据（断点续传、重试、锁恢复、幂等写入）
- [ ] gate_report + §Design-Alignment-Fields

### PB-2.2 完整回测与归因（对应 Plan A S3/S4/S3b）

- [ ] 多窗口回测（1y/3y/5y + 牛熊段）
- [ ] backtest-test-cases >=19条核心用例通过
- [ ] A/B/C 对照 + 完整归因
- [ ] RejectReason 4核心路径 + TradingState 4值覆盖
- [ ] gate_report + §Design-Alignment-Fields

### PB-2.3 行业校准（对应 Plan A S3c）

- [ ] SW31 全行业覆盖（MVP + FULL）
- [ ] gate_report + §Design-Alignment-Fields

### PB-2.4 MSS/Validation 校准（对应 Plan A S3d/S3e）

- [ ] MSS adaptive 可运行 + probe 可复跑（MVP + FULL）
- [ ] Validation 双窗口 WFA + factor_gate_raw 健康度检查
- [ ] factor_gate_raw=FAIL 升级策略已执行
- [ ] gate_report + §Design-Alignment-Fields

### PB-2.5 极端防御（对应 Plan A S4b）

- [ ] 防御参数可追溯到 S3b+S3e
- [ ] 压力场景可回放
- [ ] gate_report + §Design-Alignment-Fields

### 螺旋2收口

- [ ] 更新 `PLAN-B-READINESS-SCOREBOARD.md` 螺旋2
- [ ] 输出 `GO/NO_GO`

---

## 4. 螺旋3（Production）执行项

### PB-3.1 展示闭环（对应 Plan A S5）

**Plan A 锚点**：`S5-EXECUTION-CARD.md` v1.0  
**设计依据**：`gui-algorithm.md`、`gui-data-models.md`、`gui-api.md`、`gui-information-flow.md`（均 v3.2.0）

模块分解：

| 模块 | 必须项 | 验收要点 |
|---|---|---|
| 7 页面 | Dashboard / MSS / IRS / PAS / Integrated / Trading / Analysis | 全部只读消费真实产物，不二次计算 |
| FreshnessMeta | 新鲜度徽标（≤4h fresh / ≤24h stale / >24h expired） | 数据源时间戳可追溯 |
| FilterConfig | 过滤配置持久化 + 回显 | GUI 配置可复现 |
| pnl_color | A 股红涨绿跌色彩方案 | 与 gui-algorithm §4 一致 |
| 日报导出 | 日报 PDF/HTML 导出 | 可追溯到 pipeline 产物 |

- [ ] 7 页面全部只读消费 + FreshnessMeta/FilterConfig 验证
- [ ] pnl_color A 股红涨绿跌 + 日报导出可追溯
- [ ] `pytest tests/unit/gui/ -q` 全通过（含 freshness_meta / filter_config / pnl_color 3 个 target 测试）
- [ ] gate_report + §Design-Alignment-Fields

### PB-3.2 稳定化闭环（对应 Plan A S6）

**Plan A 锚点**：`S6-EXECUTION-CARD.md` v1.0  
**设计依据**：`eq-improvement-plan-core-frozen.md` ENH-08、`system-overview.md` §Pipeline

模块分解：

| 模块 | 必须项 | 验收要点 |
|---|---|---|
| FullChainReplay | `eq run-all --date {trade_date}` | 全链路可单命令重跑 |
| ConsistencyChecker | gate 链精确匹配 / score 链 <1e-6 / return 链 <1e-4 | 三层阈值全 PASS |
| DebtSettlement | debts.md 存量逐条清偿或标注保留理由 | 合并前零未决债务 |

- [ ] `eq run-all` 全链路重跑一致性通过（三层阈值：gate 精确 / score <1e-6 / return <1e-4）
- [ ] 债务清偿记录完成（debts.md 存量零未决）
- [ ] `pytest tests/unit/pipeline/test_full_chain_contract.py tests/unit/pipeline/test_replay_reproducibility.py tests/unit/pipeline/test_design_freeze_guard.py -q` 全通过
- [ ] gate_report + §Design-Alignment-Fields

### PB-3.3 调度闭环（对应 Plan A S7a）

**Plan A 锚点**：`S7A-EXECUTION-CARD.md` v1.0  
**设计依据**：`data-layer-api.md` §6 DataScheduler API、`data-layer-algorithm.md` §7 每日调度流程

模块分解：

| 模块 | 必须项 | 验收要点 |
|---|---|---|
| SchedulerCore | `eq scheduler install/status/run-once` | 三命令可用，内部按 data-layer 设计抽象 |
| CalendarGuard | 消费 `raw_trade_cal` 判断交易日 | 非交易日自动跳过并记录 skip 事件 |
| RunHistory + Idempotency | `task_execution_log` 记录 + 同 trade_date+task_name 幂等去重 + 失败重试≤3次 | 运行历史可审计；重复执行不重复写入 |

- [ ] `eq scheduler install/status/run-once` 三命令可用
- [ ] CalendarGuard 非交易日自动跳过 + 幂等去重可验证
- [ ] `pytest tests/unit/pipeline/test_scheduler_install_contract.py tests/unit/pipeline/test_scheduler_calendar_idempotency.py tests/unit/pipeline/test_scheduler_run_history_contract.py -q` 全通过
- [ ] gate_report + §Design-Alignment-Fields

### PB-3.4 Pre-Live 预演（对应 Plan A 螺旋3.5）

- [ ] 连续 >=20 交易日零下单预演
- [ ] 每日偏差复盘 + 故障恢复演练
- [ ] 预演期 P0=0，偏差均值 <5%
- [ ] gate_report + §Design-Alignment-Fields

### 螺旋3收口

- [ ] 更新 `PLAN-B-READINESS-SCOREBOARD.md` 螺旋3+3.5
- [ ] 输出 `GO/NO_GO`
- [ ] 未 GO 禁止真实资金

---

## 5. 每微圈同步清单

- [ ] `gate_report.md`（含 §Design-Alignment-Fields）
- [ ] `consumption.md`
- [ ] `review.md`

每螺旋收口额外同步：

- [ ] `Governance/specs/spiral-{spiral_id}/final.md`
- [ ] `Governance/record/development-status.md`
- [ ] `Governance/record/debts.md`
- [ ] `Governance/record/reusable-assets.md`
- [ ] `Governance/SpiralRoadmap/planB/PLAN-B-READINESS-SCOREBOARD.md`

---

## 6. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v3.1 | 2026-02-26 | PB-3.1/3.2/3.3 升级：增加模块分解+设计依据+Plan A 执行卡锚点+验收测试命令 |
| v3.0 | 2026-02-25 | 堵最大缺口：按 PB-1.1~PB-3.4 微圈重构；增加字段级设计对齐、量化阈值、微圈同步清单 |
| v2.1 | 2026-02-24 | 改为设计绑定执行清单 |
| v2.0 | 2026-02-23 | 实事求是版 |
