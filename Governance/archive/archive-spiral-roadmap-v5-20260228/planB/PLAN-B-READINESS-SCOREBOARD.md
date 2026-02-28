# Plan B 业务就绪看板（微圈量化版）

**创建时间**: 2026-02-23  
**更新时间**: 2026-02-25  
**状态**: Active  
**用途**: Plan B 螺旋闭环的业务判定面板（唯一 GO/NO_GO 载体）

---

## 1. 螺旋总览

| 螺旋 | 微圈范围 | 对应 Plan A | 状态 | 结论 |
|---|---|---|---|---|
| 螺旋1 Canary | PB-1.1~PB-1.4 | S0a-S2c + S3(min) + S3b(min) | planned | pending |
| 螺旋2 Full | PB-2.1~PB-2.5 | S3a-S4b | planned | pending |
| 螺旋3 Production | PB-3.1~PB-3.4 | S5-S7a + Pre-Live | planned | pending |

---

## 2. 螺旋1评分卡（PB-1.1~PB-1.4）

### PB-1.1 数据闭环

| 指标 | 量化目标 | 当前值 | 状态 |
|---|---|---|---|
| 数据窗口 | 最低 2020-2024（理想 2019-01-01~2026-02-13） | pending | blocked |
| 本地覆盖率 | >=99% | pending | blocked |
| raw_daily DDL 对齐 | 字段 100% 与 data-layer-data-models 一致 | pending | blocked |
| 硬编码检查 | Config.from_env() 无硬编码 | pending | blocked |
| gate_report | 含 §Design-Alignment-Fields | pending | blocked |

### PB-1.2 算法闭环

| 指标 | 量化目标 | 当前值 | 状态 |
|---|---|---|---|
| 五模块产物 | MSS/IRS/PAS/Validation/Integration 全齐 | pending | blocked |
| validation_weight_plan | 桥接链可追溯 | pending | blocked |
| 集成 4 模式 | optimistic/balanced/conservative/defensive 可审计 | pending | blocked |
| 硬约束 | T+1/涨跌停/交易时段硬运行 | pending | blocked |
| gate_report | 含 §Design-Alignment-Fields | pending | blocked |

### PB-1.3 最小回测闭环

| 指标 | 量化目标 | 当前值 | 状态 |
|---|---|---|---|
| 回测引擎 | 可运行产出净值曲线 | pending | blocked |
| A股规则 | T+1/涨跌停/费用模型与 backtest-test-cases 一致 | pending | blocked |
| A/B/C 对照 | 指标摘要可产出 | pending | blocked |
| gate_report | 含 §Design-Alignment-Fields | pending | blocked |

### PB-1.4 最小归因闭环

| 指标 | 量化目标 | 当前值 | 状态 |
|---|---|---|---|
| 三分解 | signal/execution/cost 全可产出 | pending | blocked |
| MSS 超额 vs 随机 | >5% | pending | blocked |
| MSS 超额 vs 技术基线 | >3% | pending | blocked |
| 夏普比率 | >1.0 | pending | blocked |
| 最大回撤 | <20% | pending | blocked |
| 胜率 | >50% | pending | blocked |
| dominant_component | ≠'none' 比例 >=50% | pending | blocked |
| gate_report | 含 §Design-Alignment-Fields | pending | blocked |

### 螺旋1结论

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| 螺旋1 GO/NO_GO | 以上全 PASS | pending | blocked |

---

## 3. 螺旋2评分卡（PB-2.1~PB-2.5）

### PB-2.1 采集扩窗

| 指标 | 量化目标 | 当前值 | 状态 |
|---|---|---|---|
| 历史窗口 | 2008-01-01 ~ 2024-12-31 | pending | planned |
| 覆盖率 | >=99% | pending | planned |
| 采集稳定性 | 断点续传/重试/锁恢复/幂等写入全通过 | pending | planned |
| gate_report | 含 §Design-Alignment-Fields | pending | planned |

### PB-2.2 完整回测与归因

| 指标 | 量化目标 | 当前值 | 状态 |
|---|---|---|---|
| 多窗口回测 | 1y/3y/5y + 典型牛熊段 | pending | planned |
| backtest-test-cases | >=19 条核心用例通过 | pending | planned |
| A/B/C 对照 | 完整归因可回答收益来源 | pending | planned |
| RejectReason | 4 核心拒单路径覆盖 | pending | planned |
| TradingState | 4 值全覆盖 | pending | planned |
| gate_report | 含 §Design-Alignment-Fields | pending | planned |

### PB-2.3 行业校准

| 指标 | 量化目标 | 当前值 | 状态 |
|---|---|---|---|
| SW31 行业 | MVP：覆盖 + 无 FAIL；FULL：生产口径通过 | pending | planned |
| gate_report | 含 §Design-Alignment-Fields | pending | planned |

### PB-2.4 MSS/Validation 校准

| 指标 | 量化目标 | 当前值 | 状态 |
|---|---|---|---|
| MSS adaptive | probe 可复跑，MVP + FULL | pending | planned |
| Validation WFA | 双窗口 walk-forward analysis 通过 | pending | planned |
| factor_gate_raw 健康度 | FAIL 比例 <15%；>15% 升级审计 | pending | planned |
| FAIL 升级策略 | 3 路径已执行（扩窗重算/neutral_regime审计/降级） | pending | planned |
| gate_report | 含 §Design-Alignment-Fields | pending | planned |

### PB-2.5 极端防御

| 指标 | 量化目标 | 当前值 | 状态 |
|---|---|---|---|
| 防御参数 | 可追溯到 S3b+S3e | pending | planned |
| 压力场景 | 可回放 + 结论可审计 | pending | planned |
| gate_report | 含 §Design-Alignment-Fields | pending | planned |

### 螺旋2结论

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| 螺旋2 GO/NO_GO | 以上全 PASS | pending | planned |

---

## 4. 螺旋3评分卡（PB-3.1~PB-3.4）

### PB-3.1 展示闭环

**Plan A 锚点**：`S5-EXECUTION-CARD.md` v1.0 | **设计依据**：`gui-algorithm/data-models/api/information-flow` v3.2.0

| 指标 | 量化目标 | 当前值 | 状态 |
|---|---|---|---|
| 7 页面覆盖 | Dashboard/MSS/IRS/PAS/Integrated/Trading/Analysis 全可用 | 0/7 | planned |
| GUI 消费口径 | 只读消费真实产物（不二次计算） | pending | planned |
| FreshnessMeta | 新鲜度三级：≤4h fresh / ≤24h stale / >24h expired | pending | planned |
| FilterConfig | 过滤配置持久化 + 回显可复现 | pending | planned |
| pnl_color | A 股红涨绿跌（gui-algorithm §4） | pending | planned |
| 日报导出 | PDF/HTML 可追溯到 pipeline 产物 | pending | planned |
| 字段对齐率 | GUI dataclass 字段 vs gui-data-models.md ≥95% | pending | planned |
| target 测试 | freshness_meta + filter_config + pnl_color 3 测试全 PASS | 0/3 | planned |
| gate_report | 含 §Design-Alignment-Fields | pending | planned |

### PB-3.2 稳定化闭环

**Plan A 锚点**：`S6-EXECUTION-CARD.md` v1.0 | **设计依据**：ENH-08 + system-overview §Pipeline

| 指标 | 量化目标 | 当前值 | 状态 |
|---|---|---|---|
| eq run-all | 全链路单命令可重跑 | pending | planned |
| gate 链一致性 | 精确匹配（bitwise equal） | pending | planned |
| score 链一致性 | 差异 <1e-6 | pending | planned |
| return 链一致性 | 差异 <1e-4 | pending | planned |
| 债务清偿 | debts.md 存量零未决 | pending | planned |
| target 测试 | full_chain + replay_reproducibility + design_freeze_guard 3 测试全 PASS | 0/3 | planned |
| gate_report | 含 §Design-Alignment-Fields | pending | planned |

### PB-3.3 调度闭环

**Plan A 锚点**：`S7A-EXECUTION-CARD.md` v1.0 | **设计依据**：data-layer-api §6 + data-layer-algorithm §7

| 指标 | 量化目标 | 当前值 | 状态 |
|---|---|---|---|
| SchedulerCore | `eq scheduler install/status/run-once` 三命令可用 | 0/3 | planned |
| CalendarGuard | 非交易日自动跳过 + skip 事件可审计 | pending | planned |
| Idempotency | 同 trade_date+task_name 重复执行不重复写入 | pending | planned |
| RunHistory | `task_execution_log` 可查询 + 失败重试≤3次可追溯 | pending | planned |
| target 测试 | scheduler_install + calendar_idempotency + run_history 3 测试全 PASS | 0/3 | planned |
| gate_report | 含 §Design-Alignment-Fields | pending | planned |

### PB-3.4 Pre-Live 预演

| 指标 | 量化目标 | 当前值 | 状态 |
|---|---|---|---|
| 连续预演 | >=20 交易日 | pending | planned |
| 预演期 P0 | =0 | pending | planned |
| 偏差均值 | <5%（signal/execution/cost） | pending | planned |
| 故障恢复 | 至少 1 次演练通过 | pending | planned |
| gate_report | 含 §Design-Alignment-Fields | pending | planned |

### 螺旋3结论

| 指标 | 目标 | 当前值 | 状态 |
|---|---|---|---|
| 螺旋3 GO/NO_GO | 以上全 PASS | pending | planned |
| 真实资金许可 | 螺旋3 GO 后方可启用 | pending | planned |

---

## 5. 设计对齐检查（docs/design）

| 设计域 | 检查项 | 首次校验微圈 | 状态 |
|---|---|---|---|
| core-algorithms/mss | `mss_panorama` 字段与语义一致 | PB-1.2 | pending |
| core-algorithms/irs | SW31 门禁与行业覆盖一致 | PB-1.2 | pending |
| core-algorithms/pas | PAS 输出字段一致 | PB-1.2 | pending |
| core-algorithms/validation | `validation_weight_plan` 桥接一致 | PB-1.2 | pending |
| core-algorithms/integration | 四模式与硬约束一致 | PB-1.2 | pending |
| core-infrastructure/data-layer | L1-L4 依赖与落库口径一致 | PB-1.1 | pending |
| core-infrastructure/backtest | 回测口径与主线引擎一致 + backtest-test-cases | PB-1.3 | pending |
| core-infrastructure/trading | A股规则与风控口径一致 + RejectReason/TradingState | PB-2.2 | pending |
| core-infrastructure/analysis | 归因链路与偏差分解一致 + dominant_component | PB-1.4 | pending |
| core-infrastructure/gui | 只读展示口径一致 + FreshnessMeta/FilterConfig | PB-3.1 | pending |

---

## 6. 更新规则

1. 每个微圈收口后必须更新本看板对应行。
2. 任一 P0 指标 `blocked` 时，不得宣称螺旋完成。
3. 任一设计对齐检查为 `pending`，不得给出最终生产 `GO`。
4. 未通过螺旋3 PB-3.4 `GO`，禁止真实资金实盘。
5. 量化阈值不达标时，gate_report 必须给出降级说明或修复计划。

---

## 7. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v3.1 | 2026-02-26 | PB-3.1/3.2/3.3 升级：增加 Plan A 执行卡锚点+设计依据标注+量化行（7页面覆盖/字段对齐率/三层一致性阈值/调度3命令/target测试计数） |
| v3.0 | 2026-02-25 | 堵最大缺口：按 PB-1.1~PB-3.4 微圈拆分评分卡；补充量化阈值（超额>5%/3%、夏普>1.0、回撤<20%、胜率>50%、dominant_component、factor_gate_raw、backtest-test-cases>=19、FreshnessMeta、偏差<5%）；设计对齐增加首次校验微圈标注 |
| v2.1 | 2026-02-24 | 改为设计绑定业务看板：增加 docs/design 对齐检查与螺旋闭环口径 |
| v2.0 | 2026-02-23 | 实事求是版 |
