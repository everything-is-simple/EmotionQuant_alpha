from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from src.config.exceptions import DataNotReadyError
from src.models.enums import MssCycle, Trend

# DESIGN_TRACE:
# - docs/design/core-algorithms/mss/mss-algorithm.md (§3 因子公式, §4 温度公式, §5 周期状态机)
# - Governance/SpiralRoadmap/execution-cards/S1A-EXECUTION-CARD.md (§2 run, §3 test, §4 artifact)
# - Governance/SpiralRoadmap/execution-cards/S2C-EXECUTION-CARD.md (§3 MSS)
DESIGN_TRACE = {
    "mss_algorithm": "docs/design/core-algorithms/mss/mss-algorithm.md",
    "s1a_execution_card": "Governance/SpiralRoadmap/execution-cards/S1A-EXECUTION-CARD.md",
    "s2c_execution_card": "Governance/SpiralRoadmap/execution-cards/S2C-EXECUTION-CARD.md",
}

VALID_TRENDS: set[str] = {item.value for item in Trend}
VALID_TREND_QUALITIES = {"normal", "cold_start", "degraded"}
VALID_THRESHOLD_MODES = {"fixed", "adaptive"}
VALID_CYCLES: set[str] = {item.value for item in MssCycle}

ADAPTIVE_LOOKBACK = 252
ADAPTIVE_MIN_SAMPLES = 120
DEFAULT_CYCLE_THRESHOLDS = {"t30": 30.0, "t45": 45.0, "t60": 60.0, "t75": 75.0}

DEFAULT_FACTOR_BASELINES: dict[str, tuple[float, float]] = {
    "market_coefficient": (0.50, 0.20),
    "profit_effect": (0.08, 0.05),
    "loss_effect": (0.08, 0.05),
    "continuity_factor": (0.35, 0.20),
    "extreme_factor": (0.05, 0.03),
    "volatility_factor": (0.08, 0.05),
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _to_int(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, float) and math.isnan(value):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _to_float(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, float) and math.isnan(value):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _zscore_normalize(raw_value: float, mean: float, std: float) -> float:
    """Z-Score 归一化：映射 [-3σ, +3σ] → [0, 100]。

    与 docs/design/core-algorithms/mss/mss-algorithm.md §7 对齐。
    """
    if not math.isfinite(raw_value):
        return 50.0
    if not math.isfinite(mean):
        return 50.0
    if not math.isfinite(std) or std <= 0:
        return 50.0
    z_value = (raw_value - mean) / std
    score = (z_value + 3.0) / 6.0 * 100.0
    return float(round(_clamp(score, 0.0, 100.0), 4))


def _amount_volatility_ratio(amount_volatility: float) -> float:
    value = max(0.0, amount_volatility)
    return value / (value + 1_000_000.0)


def _quantile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    normalized_values: list[float] = []
    for item in values:
        try:
            parsed = float(item)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed):
            normalized_values.append(parsed)
    sorted_values = sorted(normalized_values)
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    pos = (len(sorted_values) - 1) * q
    lower = int(math.floor(pos))
    upper = int(math.ceil(pos))
    if lower == upper:
        return float(sorted_values[lower])
    weight = pos - lower
    return float(sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * weight)


def _resolve_adaptive_cycle_thresholds(temperature_history: Sequence[float]) -> dict[str, float]:
    history: list[float] = []
    for item in temperature_history[-ADAPTIVE_LOOKBACK:]:
        try:
            parsed = float(item)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed):
            history.append(parsed)
    if len(history) < ADAPTIVE_MIN_SAMPLES:
        return dict(DEFAULT_CYCLE_THRESHOLDS)

    t30 = _quantile(history, 0.30)
    t45 = _quantile(history, 0.45)
    t60 = _quantile(history, 0.60)
    t75 = _quantile(history, 0.75)
    if not (t30 <= t45 <= t60 <= t75):
        return dict(DEFAULT_CYCLE_THRESHOLDS)
    return {"t30": t30, "t45": t45, "t60": t60, "t75": t75}


def resolve_cycle_thresholds(
    temperature_history: Sequence[float],
    *,
    threshold_mode: str = "adaptive",
) -> dict[str, float]:
    normalized_mode = str(threshold_mode or "adaptive").strip().lower() or "adaptive"
    if normalized_mode not in VALID_THRESHOLD_MODES:
        raise ValueError(
            f"unsupported threshold_mode: {threshold_mode}; allowed={sorted(VALID_THRESHOLD_MODES)}"
        )
    if normalized_mode == "fixed":
        return dict(DEFAULT_CYCLE_THRESHOLDS)
    return _resolve_adaptive_cycle_thresholds(temperature_history)


@dataclass(frozen=True)
class MssInputSnapshot:
    trade_date: str
    total_stocks: int
    rise_count: int
    limit_up_count: int
    limit_down_count: int
    touched_limit_up: int
    strong_up_count: int
    strong_down_count: int
    new_100d_high_count: int
    new_100d_low_count: int
    continuous_limit_up_2d: int
    continuous_limit_up_3d_plus: int
    continuous_new_high_2d_plus: int
    high_open_low_close_count: int
    low_open_high_close_count: int
    pct_chg_std: float
    amount_volatility: float
    fall_count: int = 0
    flat_count: int = 0
    data_quality: str = "normal"
    stale_days: int = 0
    source_trade_date: str = ""

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> MssInputSnapshot:
        trade_date = str(record.get("trade_date", "")).strip()
        if len(trade_date) != 8 or not trade_date.isdigit():
            raise ValueError(f"invalid trade_date: {trade_date}")

        return cls(
            trade_date=trade_date,
            total_stocks=_to_int(record.get("total_stocks", 0)),
            rise_count=_to_int(record.get("rise_count", 0)),
            limit_up_count=_to_int(record.get("limit_up_count", 0)),
            limit_down_count=_to_int(record.get("limit_down_count", 0)),
            touched_limit_up=_to_int(record.get("touched_limit_up", 0)),
            strong_up_count=_to_int(record.get("strong_up_count", 0)),
            strong_down_count=_to_int(record.get("strong_down_count", 0)),
            new_100d_high_count=_to_int(record.get("new_100d_high_count", 0)),
            new_100d_low_count=_to_int(record.get("new_100d_low_count", 0)),
            continuous_limit_up_2d=_to_int(record.get("continuous_limit_up_2d", 0)),
            continuous_limit_up_3d_plus=_to_int(
                record.get("continuous_limit_up_3d_plus", 0)
            ),
            continuous_new_high_2d_plus=_to_int(
                record.get("continuous_new_high_2d_plus", 0)
            ),
            high_open_low_close_count=_to_int(
                record.get("high_open_low_close_count", 0)
            ),
            low_open_high_close_count=_to_int(
                record.get("low_open_high_close_count", 0)
            ),
            pct_chg_std=_to_float(record.get("pct_chg_std", 0.0)),
            amount_volatility=_to_float(record.get("amount_volatility", 0.0)),
            fall_count=_to_int(record.get("fall_count", 0)),
            flat_count=_to_int(record.get("flat_count", 0)),
            data_quality=str(record.get("data_quality", "normal") or "normal"),
            stale_days=_to_int(record.get("stale_days", 0)),
            source_trade_date=str(record.get("source_trade_date", "") or trade_date),
        )


@dataclass(frozen=True)
class MssPanorama:
    """MSS 全景输出。

    .. deprecated:: nc-v1
        ``mss_score`` 字段保留以兼容旧存储，语义已由 ``mss_temperature`` 替代。
        新代码请使用 ``mss_temperature``。
    """
    trade_date: str
    mss_score: float  # deprecated: 使用 mss_temperature
    mss_temperature: float
    mss_cycle: str
    trend: str
    trend_quality: str
    mss_rank: int
    mss_percentile: float
    position_advice: str
    neutrality: float
    mss_market_coefficient: float
    mss_profit_effect: float
    mss_loss_effect: float
    mss_continuity_factor: float
    mss_extreme_factor: float
    mss_volatility_factor: float
    mss_extreme_direction_bias: float
    data_quality: str
    stale_days: int
    source_trade_date: str
    contract_version: str = "nc-v1"
    created_at: str = ""

    def to_storage_record(self) -> dict[str, object]:
        timestamp = self.created_at or datetime.utcnow().isoformat()
        return {
            "trade_date": self.trade_date,
            "mss_score": self.mss_score,  # deprecated: 保留兼容，新消费方用 mss_temperature
            "mss_temperature": self.mss_temperature,
            "mss_cycle": self.mss_cycle,
            "mss_trend": self.trend,
            "mss_trend_quality": self.trend_quality,
            "mss_rank": self.mss_rank,
            "mss_percentile": self.mss_percentile,
            "mss_position_advice": self.position_advice,
            "temperature": self.mss_temperature,
            "cycle": self.mss_cycle,
            "trend": self.trend,
            "trend_quality": self.trend_quality,
            "rank": self.mss_rank,
            "percentile": self.mss_percentile,
            "position_advice": self.position_advice,
            "neutrality": self.neutrality,
            "mss_market_coefficient": self.mss_market_coefficient,
            "mss_profit_effect": self.mss_profit_effect,
            "mss_loss_effect": self.mss_loss_effect,
            "mss_continuity_factor": self.mss_continuity_factor,
            "mss_extreme_factor": self.mss_extreme_factor,
            "mss_volatility_factor": self.mss_volatility_factor,
            "mss_extreme_direction_bias": self.mss_extreme_direction_bias,
            "data_quality": self.data_quality,
            "stale_days": self.stale_days,
            "source_trade_date": self.source_trade_date,
            "contract_version": self.contract_version,
            "created_at": timestamp,
        }


def _ema(values: Sequence[float], span: int) -> float:
    if not values:
        return 0.0
    alpha = 2.0 / (float(span) + 1.0)
    ema = float(values[0])
    for item in values[1:]:
        ema = alpha * float(item) + (1.0 - alpha) * ema
    return float(ema)


def _std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(float(item) for item in values) / float(len(values))
    variance = sum((float(item) - mean) ** 2 for item in values) / float(len(values))
    return float(math.sqrt(max(variance, 0.0)))


def _trend_from_monotonic(history: Sequence[float]) -> str:
    if len(history) < 3:
        return "sideways"
    recent = [float(value) for value in history[-3:]]
    if recent[0] < recent[1] < recent[2]:
        return "up"
    if recent[0] > recent[1] > recent[2]:
        return "down"
    return "sideways"


def _detect_trend_and_quality(temperature_history: Sequence[float]) -> tuple[str, str]:
    normalized: list[float] = []
    for item in temperature_history:
        try:
            parsed = float(item)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed):
            normalized.append(parsed)

    if len(normalized) < 3:
        return ("sideways", "degraded")
    if len(normalized) < 8:
        return (_trend_from_monotonic(normalized), "cold_start")

    ema_short = _ema(normalized[-20:], span=3)
    ema_long = _ema(normalized[-20:], span=8)
    if len(normalized) >= 6:
        slope_5d = (normalized[-1] - normalized[-6]) / 5.0
    else:
        slope_5d = (normalized[-1] - normalized[0]) / max(float(len(normalized) - 1), 1.0)
    std_20 = _std(normalized[-20:])
    trend_band = max(0.8, 0.15 * std_20)

    trend = "sideways"
    if ema_short > ema_long and slope_5d >= trend_band:
        trend = "up"
    elif ema_short < ema_long and slope_5d <= -trend_band:
        trend = "down"

    quality = "normal" if len(normalized) >= 20 else "degraded"
    return (trend, quality)


def detect_trend(temperature_history: Sequence[float]) -> str:
    trend, _ = _detect_trend_and_quality(temperature_history)
    return trend


def detect_cycle(
    temperature: float,
    trend: str,
    thresholds: Mapping[str, float] | None = None,
) -> str:
    if trend not in VALID_TRENDS:
        return "unknown"

    resolved = dict(DEFAULT_CYCLE_THRESHOLDS)
    if thresholds is not None:
        try:
            candidate = {
                "t30": float(thresholds.get("t30", 30.0)),
                "t45": float(thresholds.get("t45", 45.0)),
                "t60": float(thresholds.get("t60", 60.0)),
                "t75": float(thresholds.get("t75", 75.0)),
            }
            if candidate["t30"] <= candidate["t45"] <= candidate["t60"] <= candidate["t75"]:
                resolved = candidate
        except (TypeError, ValueError):
            resolved = dict(DEFAULT_CYCLE_THRESHOLDS)

    t30 = resolved["t30"]
    t45 = resolved["t45"]
    t60 = resolved["t60"]
    t75 = resolved["t75"]

    if temperature >= t75:
        return "climax"

    if trend == "up":
        if temperature < t30:
            return "emergence"
        if temperature < t45:
            return "fermentation"
        if temperature < t60:
            return "acceleration"
        return "divergence"

    if trend == "sideways":
        if temperature >= t60:
            return "divergence"
        return "recession"

    if trend == "down":
        if temperature >= t60:
            return "diffusion"
        return "recession"

    return "unknown"


def _position_advice_for_cycle(cycle: str) -> str:
    mapping = {
        "emergence": "80%-100%",
        "fermentation": "60%-80%",
        "acceleration": "50%-70%",
        "divergence": "40%-60%",
        "climax": "20%-40%",
        "diffusion": "30%-50%",
        "recession": "0%-20%",
        "unknown": "0%-20%",
    }
    return mapping.get(cycle, "0%-20%")


def _compute_rank_percentile(
    *,
    temperature: float,
    temperature_history: Sequence[float],
) -> tuple[int, float]:
    history: list[float] = []
    for item in temperature_history:
        try:
            parsed = float(item)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed):
            history.append(parsed)
    history.append(float(temperature))
    if not history:
        return (1, 100.0)
    rank = 1 + sum(1 for item in history if item > float(temperature))
    percentile = 100.0 * sum(1 for item in history if item <= float(temperature)) / float(len(history))
    return (int(rank), float(round(_clamp(percentile, 0.0, 100.0), 4)))


def calculate_mss_score(
    snapshot: MssInputSnapshot,
    *,
    temperature_history: Sequence[float] | None = None,
    threshold_mode: str = "adaptive",
    stale_hard_limit_days: int = 3,
) -> MssScoreResult:
    # 数据新鲜度阻断：stale_days 超过阈值时拒绝计算。
    if snapshot.stale_days > stale_hard_limit_days:
        raise DataNotReadyError(
            f"market_snapshot stale_days={snapshot.stale_days} "
            f"exceeds hard limit={stale_hard_limit_days}",
            stale_days=snapshot.stale_days,
        )

    total_stocks = max(snapshot.total_stocks, 1)

    if snapshot.total_stocks <= 0:
        # 输入基线缺失时回退到中性分，避免伪方向性。
        market_coefficient = 50.0
        profit_effect = 50.0
        loss_effect = 50.0
        continuity_factor = 50.0
        extreme_factor = 50.0
        volatility_factor = 50.0
        extreme_direction_bias = 0.0
    else:
        market_coefficient_raw = _safe_ratio(snapshot.rise_count, total_stocks)
        market_coefficient = _zscore_normalize(
            market_coefficient_raw,
            *DEFAULT_FACTOR_BASELINES["market_coefficient"],
        )

        limit_up_ratio = _safe_ratio(snapshot.limit_up_count, total_stocks)
        new_high_ratio = _safe_ratio(snapshot.new_100d_high_count, total_stocks)
        strong_up_ratio = _safe_ratio(snapshot.strong_up_count, total_stocks)
        profit_effect_raw = (
            0.4 * limit_up_ratio + 0.3 * new_high_ratio + 0.3 * strong_up_ratio
        )
        profit_effect = _zscore_normalize(
            profit_effect_raw,
            *DEFAULT_FACTOR_BASELINES["profit_effect"],
        )

        broken_rate = _safe_ratio(
            max(snapshot.touched_limit_up - snapshot.limit_up_count, 0),
            max(snapshot.touched_limit_up, 1),
        )
        limit_down_ratio = _safe_ratio(snapshot.limit_down_count, total_stocks)
        strong_down_ratio = _safe_ratio(snapshot.strong_down_count, total_stocks)
        new_low_ratio = _safe_ratio(snapshot.new_100d_low_count, total_stocks)
        loss_effect_raw = (
            0.3 * broken_rate
            + 0.2 * limit_down_ratio
            + 0.3 * strong_down_ratio
            + 0.2 * new_low_ratio
        )
        loss_effect = _zscore_normalize(
            loss_effect_raw,
            *DEFAULT_FACTOR_BASELINES["loss_effect"],
        )

        continuity_limit_ratio = _safe_ratio(
            snapshot.continuous_limit_up_2d + 2 * snapshot.continuous_limit_up_3d_plus,
            max(snapshot.limit_up_count, 1),
        )
        continuity_new_high_ratio = _safe_ratio(
            snapshot.continuous_new_high_2d_plus,
            max(snapshot.new_100d_high_count, 1),
        )
        continuity_factor_raw = (
            0.5 * continuity_limit_ratio + 0.5 * continuity_new_high_ratio
        )
        continuity_factor = _zscore_normalize(
            continuity_factor_raw,
            *DEFAULT_FACTOR_BASELINES["continuity_factor"],
        )

        panic_tail_ratio = _safe_ratio(snapshot.high_open_low_close_count, total_stocks)
        squeeze_tail_ratio = _safe_ratio(snapshot.low_open_high_close_count, total_stocks)
        extreme_factor_raw = panic_tail_ratio + squeeze_tail_ratio
        extreme_factor = _zscore_normalize(
            extreme_factor_raw,
            *DEFAULT_FACTOR_BASELINES["extreme_factor"],
        )
        if extreme_factor_raw <= 1e-12:
            extreme_direction_bias = 0.0
        else:
            extreme_direction_bias = _clamp(
                (squeeze_tail_ratio - panic_tail_ratio) / extreme_factor_raw,
                -1.0,
                1.0,
            )

        volatility_factor_raw = (
            0.5 * max(snapshot.pct_chg_std, 0.0)
            + 0.5 * _amount_volatility_ratio(snapshot.amount_volatility)
        )
        volatility_factor = _zscore_normalize(
            volatility_factor_raw,
            *DEFAULT_FACTOR_BASELINES["volatility_factor"],
        )

    temperature = _clamp(
        market_coefficient * 0.17
        + profit_effect * 0.34
        + (100.0 - loss_effect) * 0.34
        + continuity_factor * 0.05
        + extreme_factor * 0.05
        + volatility_factor * 0.05,
        0.0,
        100.0,
    )
    temperature = float(round(temperature, 4))

    history = [float(value) for value in (temperature_history or [])]
    trend, trend_quality = _detect_trend_and_quality([*history, temperature])
    cycle = detect_cycle(
        temperature,
        trend,
        thresholds=resolve_cycle_thresholds(history, threshold_mode=threshold_mode),
    )
    if cycle not in VALID_CYCLES:
        cycle = "unknown"

    neutrality = _clamp(1.0 - abs(temperature - 50.0) / 50.0, 0.0, 1.0)
    mss_rank, mss_percentile = _compute_rank_percentile(
        temperature=temperature,
        temperature_history=history,
    )

    return MssPanorama(
        trade_date=snapshot.trade_date,
        mss_score=temperature,
        mss_temperature=temperature,
        mss_cycle=cycle,
        trend=trend,
        trend_quality=trend_quality if trend_quality in VALID_TREND_QUALITIES else "degraded",
        mss_rank=mss_rank,
        mss_percentile=mss_percentile,
        position_advice=_position_advice_for_cycle(cycle),
        neutrality=float(round(neutrality, 4)),
        mss_market_coefficient=float(round(market_coefficient, 4)),
        mss_profit_effect=float(round(profit_effect, 4)),
        mss_loss_effect=float(round(loss_effect, 4)),
        mss_continuity_factor=float(round(continuity_factor, 4)),
        mss_extreme_factor=float(round(extreme_factor, 4)),
        mss_volatility_factor=float(round(volatility_factor, 4)),
        mss_extreme_direction_bias=float(round(extreme_direction_bias, 4)),
        data_quality=snapshot.data_quality,
        stale_days=snapshot.stale_days,
        source_trade_date=snapshot.source_trade_date or snapshot.trade_date,
    )
