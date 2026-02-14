# 因子与权重验证 API

**版本**: v2.2.0  
**最后更新**: 2026-02-14

---

## 1. FactorValidator

### 1.1 validate_factor

```python
def validate_factor(
    factor_name: str,
    factor_series: "SeriesLike",
    future_return_series: "SeriesLike",
    start_date: str,
    end_date: str,
    horizon_days: int = 1,
    config: ValidationConfig | None = None,
) -> FactorValidationResult
```

### 1.2 validate_factor_set

```python
def validate_factor_set(
    factors: dict[str, "SeriesLike"],
    future_returns: "SeriesLike",
    start_date: str,
    end_date: str,
    horizons: list[int] = [1, 3, 5, 10],
    config: ValidationConfig | None = None,
) -> list[FactorValidationResult]
```

---

## 2. WeightValidator

### 2.1 evaluate_candidate

```python
def evaluate_candidate(
    candidate_id: str,
    weights: dict[str, float],
    signals: "DataFrameLike",
    prices: "DataFrameLike",
    windows: list[tuple[str, str, str]],
    config: ValidationConfig | None = None,
) -> WeightValidationResult
```

### 2.2 select_weight_plan

```python
def select_weight_plan(
    candidates: list[dict[str, float]],
    baseline: dict[str, float],
    signals: "DataFrameLike",
    prices: "DataFrameLike",
    market_context: dict[str, float] | None = None,
    config: ValidationConfig | None = None,
) -> WeightValidationResult
```

### 2.3 build_dual_wfa_windows

```python
def build_dual_wfa_windows(
    end_date: str,
    config: ValidationConfig | None = None,
) -> dict[str, list[tuple[str, str, str]]]
```

说明：返回 `{"long_cycle": [...], "short_cycle": [...]}` 两套窗口定义。

---

## 3. ValidationGate

### 3.1 decide_gate

```python
from typing import Optional

def decide_gate(
    factor_results: list[FactorValidationResult],
    weight_result: WeightValidationResult,
    stale_days: int = 0,
    previous_gate: Optional[ValidationGateDecision] = None,
    config: ValidationConfig | None = None,
) -> ValidationGateDecision
```

---

## 4. Orchestrator

### 4.1 run_daily_gate

```python
def run_daily_gate(
    trade_date: str,
    use_cached_window: bool = True,
    config: ValidationConfig | None = None,
) -> tuple[ValidationGateDecision, ValidationRunManifest]
```

用途：交易日收盘后快速门禁；持久化写入  
`validation_factor_report` / `validation_weight_report` / `validation_gate_decision` / `validation_weight_plan` / `validation_run_manifest`。

### 4.2 run_spiral_full_validation

```python
def run_spiral_full_validation(
    spiral_id: str,
    start_date: str,
    end_date: str,
    config: ValidationConfig | None = None,
) -> tuple[
    list[FactorValidationResult],
    WeightValidationResult,
    ValidationGateDecision,
    ValidationRunManifest,
]
```

用途：每个 Spiral 收口前完成完整证据闭环。

### 4.3 resolve_weight_plan（Validation -> Integration 桥接）

```python
def resolve_weight_plan(
    trade_date: str,
    selected_weight_plan: str,
) -> WeightPlan
```

说明：按 `(trade_date, selected_weight_plan)` 从 `validation_weight_plan` 解析出 `WeightPlan(plan_id, w_mss, w_irs, w_pas)`。

### 4.4 build_integration_inputs

```python
def build_integration_inputs(trade_date: str) -> tuple[ValidationGateDecision, WeightPlan]
```

说明：先读取 `validation_gate_decision`，再调用 `resolve_weight_plan()` 返回 Integration 直连入参。

### 4.5 get_run_manifest

```python
def get_run_manifest(run_id: str) -> ValidationRunManifest
```

### 4.6 resolve_regime_thresholds

```python
def resolve_regime_thresholds(
    trade_date: str,
    mss_temperature: float,
    market_volatility_20d: float,
    config: ValidationConfig | None = None,
) -> ValidationConfig
```

说明：在 `threshold_mode=regime` 下返回当日动态阈值配置副本。

### 4.7 classify_fallback

```python
def classify_fallback(
    factor_gate: str,
    weight_gate: str,
    stale_days: int,
    config: ValidationConfig | None = None,
) -> tuple[str, str, float]
```

说明：返回 `(failure_class, fallback_plan, position_cap_ratio)`。

---

## 5. CLI 命令约定

```bash
python -m src.validation.run_daily_gate --trade-date 20260207
python -m src.validation.run_spiral_full --spiral s3 --start-date 20240101 --end-date 20260207
pytest tests/validation -q
```

---

## 6. 与上游/下游契约

- 上游输入：Data Layer（L1/L2）+ MSS/IRS/PAS 输出 + Integration 历史输出（`integrated_recommendation`）。
- 下游输出：CP-05（强依赖），CP-06/07（审计依赖）。
- Gate 规则：`final_gate=FAIL` 时阻断 CP-05。
- 权重桥接规则：
  - `ValidationGateDecision.selected_weight_plan` 是业务键；
  - Integration 前必须通过 `resolve_weight_plan()` 转换为 `WeightPlan` 数值对象；
  - 禁止直接从 `.reports/validation/*.parquet` 读取门禁与权重。
- 执行降级规则：
  - Integration/Trading 必须消费 `ValidationGateDecision.position_cap_ratio`；
  - `stale_days > threshold` 时不得仅告警，必须自动降仓。

---

## 7. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v2.2.0 | 2026-02-14 | 修复 review-004：新增 `build_dual_wfa_windows`、`resolve_regime_thresholds`、`classify_fallback` 接口；`decide_gate` 增加 `stale_days` 入参；补齐自动降仓契约 |
| v2.1.0 | 2026-02-09 | 修复 R29：补齐 Validation->Integration 桥接接口（`resolve_weight_plan` / `build_integration_inputs`），并明确运行时仅读 DuckDB `validation_*` |
