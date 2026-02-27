# 03 — 急救修复方案

## 修复策略总原则

鉴于差异的广度和深度，建议采用**"代码向设计对齐，设计承认阶段性现实"**的折中策略：

1. **代码必须修的**：风控漏洞、算法语义错误、阈值数量级偏差 → 代码修向设计
2. **设计可以降级标注的**：完整WFA、15因子全量验证、10个API → 设计标注 `[MVP-DEFERRED]`，记录当前简化实现与目标态的差距
3. **双向对齐的**：表结构、命名 → 以设计为准统一命名，代码中有价值的额外字段反哺设计

---

## 第一批：P0 紧急修复（预计工时：1-2天）

### FIX-01: 修复 Gate Fallback 风控漏洞 (GAP-11)

**问题**: 核心输入缺失时 `failure_class=factor_failure, position_cap_ratio=0.50`，应为 `data_failure, 0.00`

**代码修改** (`pipeline.py` L799-805):

```python
# 当前代码
if issues:
    final_gate = "FAIL"
    failure_class = "factor_failure"     # ← 错误
    fallback_plan = "baseline"           # ← 错误
    position_cap_ratio = 0.50            # ← 风控漏洞

# 修复为
if issues:
    final_gate = "FAIL"
    failure_class = "data_failure"       # ← 对齐设计
    fallback_plan = "halt"               # ← 对齐设计
    position_cap_ratio = 0.00            # ← 硬阻断
```

**验证**: 确认现有测试 `test_validation_fail_contains_prescription` 不会因此破坏（该测试检查 `final_gate == "FAIL"` 和 prescription 非空，修复后仍满足）。

---

### FIX-02: 修复 ICIR 计算公式 (GAP-03 核心部分)

**问题**: ICIR 使用 `abs(IC) * sqrt(N)` 而非标准定义 `mean_ic / std(ic)`

**代码修改** (`pipeline.py` L536):

```python
# 当前代码
icir = abs(ic) * math.sqrt(sample_size)

# 修复为: 需要滚动IC序列才能计算 mean/std
# 短期 hotfix: 在无法获得多期IC的场景下，使用 abs(ic) 作为 ICIR 的保守近似
# 并将阈值调整为与设计一致
icir = abs(ic)  # 保守近似，待 GAP-03 完整修复后替换为真实 ICIR
```

**注意**: 这是临时修复。完整修复需要 FIX-06（因子验证逻辑重写）。

---

### FIX-03: 修复 ValidationConfig 阈值 (GAP-01)

**代码修改** (`pipeline.py` L54-69):

```python
# 对齐设计文档默认值
@dataclass(frozen=True)
class ValidationConfig:
    threshold_mode: str = "fixed"          # 暂保持 fixed，regime 模式待 FIX-04 修复后启用
    stale_days_threshold: int = 3
    min_sample_count: int = 5000           # [新增] 对齐设计
    ic_pass: float = 0.02                  # 不变
    ic_warn: float = 0.00                  # 0.01 → 0.00 对齐设计
    icir_pass: float = 0.20               # 1.00 → 0.20 对齐设计 (5倍修正!)
    icir_warn: float = 0.10               # 0.50 → 0.10 对齐设计
    positive_ic_ratio_pass: float = 0.55   # [新增] 对齐设计
    positive_ic_ratio_warn: float = 0.50   # [新增] 对齐设计
    coverage_pass: float = 0.95            # [新增] 对齐设计
    coverage_warn: float = 0.90            # [新增] 对齐设计
    # 保留代码中有价值的字段（后续反哺设计）
    rank_ic_pass: float = 0.03
    rank_ic_warn: float = 0.015
    decay_pass: float = 0.05
    decay_warn: float = 0.025
    sharpe_pass: float = 0.60
    sharpe_warn: float = 0.40
    max_drawdown_pass: float = 0.15
    max_drawdown_warn: float = 0.20
    # [新增] 对齐设计
    max_weight_per_module: float = 0.60
    max_drawdown_tolerance: float = 0.02
    turnover_cap: float = 0.35
    impact_cost_cap_bps: float = 35.0
    min_tradability_ratio: float = 0.80
```

**验证**: 阈值大幅降低后，之前因阈值过高而持续 FAIL 的场景可能变为 PASS/WARN，需要检查下游是否能正确处理。

---

### FIX-04: 修复 Regime 分类逻辑 (GAP-04)

**代码修改** (`pipeline.py` L242-247, `_to_regime` 函数):

```python
# 当前代码（语义反转）
def _to_regime(mss_score, market_volatility_20d):
    if mss_score >= 75.0 and market_volatility_20d <= 0.02:
        return "hot_stable"
    if mss_score < 45.0 or market_volatility_20d >= 0.045:
        return "cold_or_volatile"
    return "neutral"

# 修复为（对齐设计）
def _to_regime(temperature: float, market_volatility_20d: float) -> str:
    if temperature >= 70.0 or market_volatility_20d >= 0.035:
        return "hot_or_volatile"
    if temperature < 40.0 or market_volatility_20d < 0.020:
        return "cold_or_quiet"
    return "neutral"
```

**注意**: 参数语义从 `mss_score` 改为 `temperature`（来自 `mss_panorama.temperature`），需确认调用处传入正确字段。

---

### FIX-05: 修复 Regime 阈值调整策略 (GAP-05)

**代码修改** (`pipeline.py` L250-285, `_regime_adjusted_config` 函数):

```python
# 对齐设计意图
def _regime_adjusted_config(base: ValidationConfig, regime: str) -> ValidationConfig:
    if regime == "hot_or_volatile":
        # 设计: 放宽 ic_warn/coverage_warn（降低误阻断），但提高 icir_pass（防噪声）
        return dataclasses.replace(base,
            ic_warn=max(base.ic_warn - 0.005, -0.02),
            coverage_warn=max(base.coverage_warn - 0.05, 0.80),
            icir_pass=base.icir_pass + 0.05,  # 收紧 ICIR 防噪声
        )
    if regime == "cold_or_quiet":
        # 设计: 提高 positive_ic_ratio_pass 与 coverage_pass（抑制低质量信号）
        return dataclasses.replace(base,
            positive_ic_ratio_pass=base.positive_ic_ratio_pass + 0.05,
            coverage_pass=min(base.coverage_pass + 0.02, 0.99),
        )
    return base
```

---

## 第二批：P1 架构补齐（预计工时：3-5天）

### FIX-06: 因子验证逻辑重写 (GAP-02 + GAP-03)

**方案**: 分两步走

**步骤A — 最小可行因子验证** (先做):
1. 添加 `ValidatedFactor` 枚举（对齐设计15个因子）
2. 重写因子验证核心循环：对每个因子提取 `factor_series`，与 `future_returns` 做截面IC
3. 实现正确的 ICIR = `mean_ic / std(ic)`
4. 添加 `positive_ic_ratio` 和 `coverage_ratio` 计算
5. 保留现有的 `irs_pas_coupling` 等作为辅助诊断指标（不参与门禁判定）

**步骤B — 多持有期衰减** (后做):
1. 实现 `decay_1d/3d/5d/10d` 真实衰减计算
2. 因子→L2数据源映射实现（按信息流文档 §4.1）

**设计修订**: 在设计文档中标注当前阶段为 `[MVP]`，完整15因子验证标注为 `[TARGET]`。

---

### FIX-07: WFA 框架搭建 (GAP-06)

**方案**: 分阶段实现

**阶段1 — 搭建WFA骨架** (本轮):
1. 实现 `build_dual_wfa_windows()` — 按设计生成双窗口定义
2. 改造 `evaluate_candidate()` — 接受 signals + prices 作为输入
3. 用简化回测替代启发式公式（至少要基于历史价格数据）

**阶段2 — 完整OOS回测** (下轮):
1. 接入 Backtest 引擎做真实OOS评估
2. 实现 `long_vote/short_vote` 投票机制
3. 实现 `vs_baseline` 系统性对照

**设计修订**: WFA 设计保持不变，代码中标注 `# WFA-PHASE-1: 简化回测` / `# WFA-PHASE-2: 完整OOS`。

---

### FIX-08: 补齐关键API (GAP-12)

**优先实现** (本轮):
- `classify_fallback()` — 解耦 fallback 逻辑，便于测试和复用
- `resolve_weight_plan()` — Integration 桥接必需
- `build_integration_inputs()` — 下游直连入参

**延后实现** (下轮，设计标注 `[MVP-DEFERRED]`):
- `validate_factor_set()` — 待 FIX-06 完成后自然衍生
- `run_spiral_full_validation()` — 待项目进入 Spiral 收口阶段
- `resolve_regime_thresholds()` — 待 regime 模式启用后
- `get_run_manifest()` — 审计需求优先级较低
- `decide_gate()` — 从 `run_validation_gate` 中抽取独立函数

---

## 第三批：P2 表结构对齐（预计工时：1-2天）

### FIX-09: 统一表结构命名 (GAP-07/08/09/10)

**原则**:
- 字段名以设计DDL为准
- 代码中有价值的额外字段（`contract_version`, `vote_detail`, `validation_prescription` 等）保留，并反哺设计DDL

**具体动作**:

| 表 | 重命名 | 补齐 | 反哺设计 |
|----|--------|------|---------|
| factor_report | `gate→decision`, `ic→mean_ic`, `rank_ic→mean_rank_ic`, `sample_size→sample_count` | `factor_source`, `window_id`, `start_date`, `end_date`, `positive_ic_ratio`, `decay_1d/3d/10d`, `coverage_ratio`, `reason` | `contract_version`, `vote_detail` |
| weight_report | `plan_id→candidate_id`, `window_group→window_set`, `expected_return→oos_return`, `turnover_cost→turnover`, `tradability_score→tradability_pass_ratio`, `gate→decision` | `window_id`, `long_vote`, `short_vote`, `w_mss/w_irs/w_pas`, `cost_sensitivity`, `impact_cost_bps`, `vs_baseline`, `reason` | `contract_version` |
| run_manifest | — | `run_type`, `command`, `test_command`, `artifact_dir`, `started_at`, `finished_at`, `status`, `failed_reason` | `threshold_mode`, `regime`, `final_gate`, `input_summary`, `vote_detail`, `contract_version` |
| weight_plan | — | `source_candidate_id` | `plan_status`, `contract_version` |
| gate_decision | — | — | `issues`, `tradability_pass_ratio`, `impact_cost_bps`, `candidate_exec_pass`, `threshold_mode`, `regime`, `validation_prescription`, `vote_detail`, `contract_version` |

**注意**: 表重命名需要迁移脚本（DuckDB ALTER TABLE 或 重建表 + 数据迁移），并协调所有查询该表的上下游代码。

---

## 第四批：P3 收尾 (预计工时：0.5天)

### FIX-10: 产物路径统一 (GAP-13)

将 `artifacts/spiral-s2c/{trade_date}/` 改为 `.reports/validation/{trade_date}/`，或在设计中承认当前路径。

### FIX-11: Baseline 权重精确化 (GAP-14)

`(0.34, 0.33, 0.33)` → `(1/3, 1/3, 1/3)` 使用 `round(1/3, 6)` 或直接使用浮点精度。

---

## 设计文档修订清单

在代码修复的同时，设计文档也需要相应更新：

| 文档 | 修订内容 |
|------|---------|
| `factor-weight-validation-data-models.md` | §1.7 ValidationConfig 新增 `rank_ic_pass/warn`, `decay_pass/warn`, `sharpe_pass/warn`, `max_drawdown_pass/warn`；5张DDL补齐 `contract_version`, `vote_detail` 等代码已有字段 |
| `factor-weight-validation-algorithm.md` | §3 添加 `[MVP]` / `[TARGET]` 阶段标注；§4.2 WFA 标注分阶段实现 |
| `factor-weight-validation-api.md` | 延后的API标注 `[MVP-DEFERRED]` |
| `factor-weight-validation-information-flow.md` | §4.1 因子映射表标注哪些已实现、哪些待实现 |

---

## 修复顺序与依赖关系

```
第一批 P0 (Day 1-2):
  FIX-01 (Fallback风控)  ← 无依赖，最先修
  FIX-03 (Config阈值)    ← 无依赖
  FIX-04 (Regime分类)    ← 无依赖
  FIX-05 (Regime调整)    ← 依赖 FIX-03, FIX-04
  FIX-02 (ICIR公式)      ← 依赖 FIX-03

第二批 P1 (Day 3-7):
  FIX-06 (因子验证重写)   ← 依赖 FIX-02, FIX-03
  FIX-07 (WFA框架)       ← 依赖 FIX-03
  FIX-08 (API补齐)       ← 依赖 FIX-01, FIX-04, FIX-05

第三批 P2 (Day 8-9):
  FIX-09 (表结构对齐)     ← 依赖 FIX-06, FIX-07

第四批 P3 (Day 10):
  FIX-10, FIX-11          ← 无依赖
```

---

## 测试策略

| 修复项 | 需要新增/修改的测试 |
|--------|-------------------|
| FIX-01 | 新增: `test_data_failure_hard_blocks_with_zero_position_cap` |
| FIX-02 | 修改: 现有因子验证测试的 ICIR 预期值 |
| FIX-03 | 修改: 所有阈值相关的 assertion |
| FIX-04+05 | 新增: `test_regime_classification_matches_design`, `test_regime_threshold_adjustment_direction` |
| FIX-06 | 新增: `test_factor_validation_against_future_returns`, `test_icir_is_mean_over_std` |
| FIX-07 | 新增: `test_dual_wfa_windows_252_63_63`, `test_wfa_oos_evaluation` |
| FIX-09 | 修改: 所有读取DuckDB validation 表的查询测试 |
