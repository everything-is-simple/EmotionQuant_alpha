# 01 — 差异完整清单

**对比基线**
- 设计文档: `docs/design/core-algorithms/validation/` (v2.2.0, 2026-02-14)
- 代码: `src/algorithms/validation/pipeline.py` + `calibration.py`

---

## 🔴 GAP-01: ValidationConfig 阈值默认值严重偏离

**设计** (`factor-weight-validation-data-models.md` §1.7):

```
ic_pass          = 0.02       ic_warn         = 0.00
icir_pass        = 0.20       icir_warn       = 0.10
threshold_mode   = "regime"   min_sample_count = 5000
positive_ic_ratio_pass = 0.55 positive_ic_ratio_warn = 0.50
coverage_pass    = 0.95       coverage_warn   = 0.90
```

加上 6 个 WFA 窗口参数、`max_weight_per_module`=0.60、`max_drawdown_tolerance`=0.02、`turnover_cap`=0.35、`impact_cost_cap_bps`=35.0、`min_tradability_ratio`=0.80、4 个 regime 分界参数。

**代码** (`pipeline.py` L54-69):

```
ic_pass          = 0.02       ic_warn         = 0.01    ← 偏离
icir_pass        = 1.00       icir_warn       = 0.50    ← 5倍偏差!
threshold_mode   = "fixed"                              ← 偏离
```

加上设计中不存在的: `rank_ic_pass/warn`, `decay_pass/warn`, `sharpe_pass/warn`, `max_drawdown_pass/warn`。

**缺失汇总**:
- 设计有、代码无 (14项): `min_sample_count`, `positive_ic_ratio_pass/warn`, `coverage_pass/warn`, 6×WFA窗口, `max_weight_per_module`, `max_drawdown_tolerance`, `turnover_cap`, `impact_cost_cap_bps`, `min_tradability_ratio`, 4×regime分界
- 代码有、设计无 (8项): `rank_ic_pass/warn`, `decay_pass/warn`, `sharpe_pass/warn`, `max_drawdown_pass/warn`

---

## 🔴 GAP-02: ValidatedFactor 枚举完全缺失

**设计** (`factor-weight-validation-data-models.md` §1.1) 定义 15 个因子:

```
MSS(6): mss_market_coefficient, mss_profit_effect, mss_loss_effect,
        mss_continuity_factor, mss_extreme_factor, mss_volatility_factor
IRS(6): irs_relative_strength, irs_continuity_factor, irs_capital_flow,
        irs_valuation, irs_leader_score, irs_gene_score
PAS(3): pas_bull_gene_score, pas_structure_score, pas_behavior_score
```

**代码**: 没有 `ValidatedFactor` 枚举。使用 4 个硬编码因子名，与设计 15 个因子**零重叠**:

```
irs_pas_coupling           ← 设计中不存在
irs_internal_stability     ← 设计中不存在
pas_internal_stability     ← 设计中不存在
mss_future_returns_alignment ← 设计中不存在
```

**影响**: 因子名是全链路的业务键。上下游（信息流文档 §4.1 因子→数据源映射表）完全无法对接。

---

## 🔴 GAP-03: 因子验证核心算法根本性错位

**设计** (`factor-weight-validation-algorithm.md` §3):
- 每个因子独立验证: `factor_series` vs `future_returns` 按 `(trade_date, stock_code)` 截面对齐
- 逐日计算截面 IC (Pearson) 和 RankIC (Spearman)，取均值
- ICIR = `mean_ic / std(ic)` （信息比率标准定义）
- 必算: `mean_ic`, `mean_rank_ic`, `icir`, `positive_ic_ratio`, `decay_1d/3d/5d/10d`, `coverage_ratio`
- 门禁: 4 维判定 (IC / ICIR / positive_ic_ratio / coverage_ratio)

**代码** (`pipeline.py` L511-620):
- 不验证设计中的15个因子，而是对 IRS行业分 vs PAS个股分 做配对相关
- IC: `corr(irs_scores, pas_scores)` — 不是因子 vs 未来收益
- ICIR: `abs(IC) * sqrt(N)` — 公式完全错误（应为 mean/std）
- Decay: `abs(IC) * 2.5` 代理公式 — 不是真实多持有期衰减
- 完全没有 `positive_ic_ratio` 计算
- 完全没有 `coverage_ratio` 计算
- 只有 `decay_5d`，缺少 `decay_1d/3d/10d`
- 没有截面对齐，没有 `(trade_date, stock_code)` 维度

**本质**: 代码验证的不是"因子对未来收益的预测力"，而是"IRS分数和PAS分数的相关性"——完全不同的业务语义。

---

## 🔴 GAP-04: Regime 分类逻辑完全反转

**设计** (`factor-weight-validation-algorithm.md` §3.4):

```
hot_or_volatile:  temperature >= 70  OR   volatility >= 0.035
neutral:          40 <= temp < 70    AND  0.020 <= vol < 0.035
cold_or_quiet:    temperature < 40   OR   volatility < 0.020
```

**代码** (`pipeline.py` L242-247):

```python
hot_stable:       mss_score >= 75  AND  volatility <= 0.02   # ← 语义完全反转!
cold_or_volatile: mss_score < 45   OR   volatility >= 0.045
neutral:          其余
```

**差异对照**:

| 维度 | 设计 | 代码 |
|------|------|------|
| "热"的语义 | 热 **或** 波动 → 同一类 | 热 **且** 稳定 → 语义反转 |
| 温度分界 | 70 / 40 | 75 / 45 |
| 波动分界 | 0.035 / 0.020 | 0.045 / 0.02 |
| 组合逻辑 | OR / AND / OR | AND / OR / else |

**后果**: 同一市场状态，设计和代码会分到不同regime，导致阈值调整方向相反。

---

## 🔴 GAP-05: Regime 阈值调整策略矛盾

**设计** (`factor-weight-validation-algorithm.md` §3.4):
- `hot_or_volatile`: 放宽 `ic_warn/coverage_warn`（降低误阻断），但**提高** `icir_pass`（防噪声）
- `cold_or_quiet`: **提高** `positive_ic_ratio_pass` 与 `coverage_pass`（抑制低质量信号）

**代码** (`pipeline.py` L250-285):
- `hot_stable`: **全面提高** ic_pass, ic_warn, icir_pass, sharpe 等（更严格）
- `cold_or_volatile`: **全面降低** ic, rank_ic, icir, sharpe（更宽松），提高 drawdown 容忍度

| regime | 设计策略 | 代码策略 | 一致性 |
|--------|---------|---------|--------|
| 热/波动 | 放宽IC但收紧ICIR | 全面收紧 | ❌ 不一致 |
| 冷/安静 | 收紧覆盖率和正IC率 | 全面放宽 | ❌ 方向相反 |

---

## 🔴 GAP-06: 权重验证——没有真实 Walk-Forward Analysis

**设计** (`factor-weight-validation-algorithm.md` §4.2):
- 双窗口并行: `long_cycle` 252/63/63 + `short_cycle` 126/42/42
- 用真实 `signals` + `prices` 做 OOS 回测
- 比较 candidate vs baseline: `oos_return`, `max_drawdown`, `sharpe`, `turnover`, `impact_cost_bps`, `tradability_pass_ratio`
- 投票规则: 两组均PASS→PASS, 一PASS一WARN→WARN, 任一FAIL→FAIL
- 候选约束: 非负、归一、max≤0.60

**代码** (`pipeline.py` L675-743):
- 没有任何真实OOS回测
- `expected_return` = 启发式公式: `max(0.015, 0.030 + (mss_score-50)/2500)`
- `max_drawdown` = 启发式公式: `max(0.03, 0.060 - (mss_score-50)/3000)`
- `sharpe` = `expected_return / max(drawdown, 0.01)` — 不是真实夏普
- "dual-window" 仅用乘子 1.05/0.95 微调 — 不是真实双窗口
- 没有权重约束验证（非负、归一、max≤0.60）
- 没有 `long_vote/short_vote` 投票机制
- 没有 `vs_baseline` 系统性对照判定

**本质**: 设计的WFA是数据驱动的，代码的"WFA"是公式驱动的启发式估算。

---

## 🔴 GAP-07: Factor Report 表结构偏离

**设计DDL** (`factor-weight-validation-data-models.md` §3.1):

| 设计字段 | 代码字段 | 状态 |
|---------|---------|------|
| `factor_name` | `factor_name` | ✅ (但值不同, 见GAP-02) |
| `factor_source` | — | ❌ 缺失 |
| `window_id` | — | ❌ 缺失 |
| `start_date` | — | ❌ 缺失 |
| `end_date` | — | ❌ 缺失 |
| `sample_count` | `sample_size` | ⚠️ 命名不同 |
| `mean_ic` | `ic` | ⚠️ 命名不同 |
| `mean_rank_ic` | `rank_ic` | ⚠️ 命名不同 |
| `icir` | `icir` | ⚠️ 值计算方式不同 |
| `positive_ic_ratio` | — | ❌ 缺失 |
| `decay_1d` | — | ❌ 缺失 |
| `decay_3d` | — | ❌ 缺失 |
| `decay_5d` | `decay_5d` | ⚠️ 代理值非真实衰减 |
| `decay_10d` | — | ❌ 缺失 |
| `coverage_ratio` | — | ❌ 缺失 |
| `decision` | `gate` | ⚠️ 命名不同 |
| `reason` | — | ❌ 缺失 (有 vote_detail 替代) |
| — | `contract_version` | ➕ 设计中无 |
| — | `vote_detail` | ➕ 设计中无 |

---

## 🔴 GAP-08: Weight Report 表结构偏离

**设计DDL** (`factor-weight-validation-data-models.md` §3.2):

| 设计字段 | 代码字段 | 状态 |
|---------|---------|------|
| `candidate_id` | `plan_id` | ⚠️ 命名不同 |
| `window_id` | — | ❌ 缺失 |
| `window_set` | `window_group` | ⚠️ 命名不同 |
| `long_vote` | — | ❌ 缺失 |
| `short_vote` | — | ❌ 缺失 |
| `w_mss/w_irs/w_pas` | — | ❌ 缺失 |
| `oos_return` | `expected_return` | ⚠️ 命名+语义不同 |
| `turnover` | `turnover_cost` | ⚠️ 命名不同 |
| `cost_sensitivity` | — | ❌ 缺失 |
| `impact_cost_bps` | — | ❌ 缺失 |
| `tradability_pass_ratio` | `tradability_score` | ⚠️ 命名不同 |
| `vs_baseline` | — | ❌ 缺失 |
| `decision` | `gate` | ⚠️ 命名不同 |
| `reason` | — | ❌ 缺失 |

---

## 🔴 GAP-09: RunManifest 几乎完全不同

**设计DDL** (`factor-weight-validation-data-models.md` §3.5) vs 代码 (`pipeline.py` L948-969):

| 设计字段 | 代码字段 | 状态 |
|---------|---------|------|
| `run_type` | — | ❌ 缺失 |
| `command` | — | ❌ 缺失 |
| `test_command` | — | ❌ 缺失 |
| `artifact_dir` | — | ❌ 缺失 |
| `started_at` | — | ❌ 缺失 |
| `finished_at` | — | ❌ 缺失 |
| `status` | — | ❌ 缺失 |
| `failed_reason` | — | ❌ 缺失 |
| — | `threshold_mode` | ➕ 设计中无 |
| — | `regime` | ➕ 设计中无 |
| — | `final_gate` | ➕ 设计中无 |
| — | `selected_weight_plan` | ➕ 设计中无 |
| — | `input_summary` | ➕ 设计中无 |
| — | `vote_detail` | ➕ 设计中无 |

仅共享 `trade_date`, `run_id`, `created_at` 三个字段。结构相似度 < 20%。

---

## 🔴 GAP-10: WeightPlan 桥接表偏离

**设计DDL** (`factor-weight-validation-data-models.md` §3.4) vs 代码 (`pipeline.py` L905-918):

| 设计字段 | 代码字段 | 状态 |
|---------|---------|------|
| `source_candidate_id` | — | ❌ 缺失 |
| — | `plan_status` | ➕ 设计中无 |
| — | `contract_version` | ➕ 设计中无 |

---

## 🔴 GAP-11: GateDecision 表——超集 + 语义错误

**代码比设计多出的字段** (`pipeline.py` L863-898):
`issues`, `tradability_pass_ratio`, `impact_cost_bps`, `candidate_exec_pass`, `threshold_mode`, `regime`, `validation_prescription`, `vote_detail`, `contract_version`

**关键语义错误**:

| 场景 | 设计 | 代码 | 问题 |
|------|------|------|------|
| 核心输入缺失 | `failure_class=data_failure`, `position_cap_ratio=0.00` (硬阻断) | `failure_class=factor_failure`, `position_cap_ratio=0.50` | 该硬阻断却只降仓50% |

设计明确：`data_failure` → `halt` → `position_cap_ratio=0.00`（不允许开任何仓位）。
代码：把核心数据缺失归为 `factor_failure`，仍允许50%仓位运行——**风控漏洞**。

---

## 🔴 GAP-12: API 结构全面偏离

**设计** (`factor-weight-validation-api.md`) 定义 4 个类、13 个方法:

```
FactorValidator:   validate_factor, validate_factor_set
WeightValidator:   evaluate_candidate, select_weight_plan, build_dual_wfa_windows
ValidationGate:    decide_gate
Orchestrator:      run_daily_gate, run_spiral_full_validation, resolve_weight_plan,
                   build_integration_inputs, get_run_manifest,
                   resolve_regime_thresholds, classify_fallback
```

**代码** 实现 3 个扁平函数:

```
validate_factor(trade_date, config, factor_name, ...)
evaluate_candidate(trade_date, config, plan_id, ...)
run_validation_gate(trade_date, config, irs_count, pas_count, mss_exists, ...)
```

**完全未实现的API** (10个):

| API | 设计用途 | 缺失影响 |
|-----|---------|---------|
| `validate_factor_set()` | 批量验证多因子 | 无法执行设计的15因子批量验证 |
| `select_weight_plan()` | 多候选比较择优 | 无法进行系统性权重方案比选 |
| `build_dual_wfa_windows()` | 构建双窗口定义 | WFA窗口构建无独立入口 |
| `decide_gate()` | 独立Gate决策 | Gate逻辑耦合在run_validation_gate中 |
| `run_spiral_full_validation()` | 圈级完整验证 | 无法执行Spiral收口验证 |
| `resolve_weight_plan()` | 权重桥接解析 | Validation→Integration桥接无独立API |
| `build_integration_inputs()` | Integration直连入参 | 下游必须自行拼装 |
| `get_run_manifest()` | 运行轨迹查询 | 审计追溯无入口 |
| `resolve_regime_thresholds()` | 动态阈值解析 | Regime阈值调整无独立入口 |
| `classify_fallback()` | 分层回退分类 | Fallback逻辑耦合不可复用 |

**已实现API签名也不同**: `validate_factor` 设计入参是 `(factor_name, factor_series, future_return_series, ...)`，代码入参是 `(trade_date, config, factor_name, ...)`——不接受外部传入的因子序列和收益序列。

---

## 🟡 GAP-13: 报告产物路径偏离

**设计**: `.reports/validation/{trade_date}/summary_{YYYYMMDD_HHMMSS}.md`
**代码**: `artifacts/spiral-s2c/{trade_date}/` + parquet + JSON

影响较低，但若有外部工具依赖设计路径则会找不到文件。

---

## 🟡 GAP-14: Baseline 权重微偏

**设计** (`factor-weight-validation-algorithm.md` §4.1): `[1/3, 1/3, 1/3]`
**代码** (`pipeline.py` L903): `(0.34, 0.33, 0.33)` — MSS 多 0.67%

影响较低，但违反了设计的等权基线语义。
