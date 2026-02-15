from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

VALID_TRENDS = {"up", "down", "sideways"}
VALID_CYCLES = {
    "emergence",
    "fermentation",
    "acceleration",
    "divergence",
    "climax",
    "diffusion",
    "recession",
    "unknown",
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
            data_quality=str(record.get("data_quality", "normal") or "normal"),
            stale_days=_to_int(record.get("stale_days", 0)),
            source_trade_date=str(record.get("source_trade_date", "") or trade_date),
        )


@dataclass(frozen=True)
class MssScoreResult:
    trade_date: str
    mss_score: float
    mss_temperature: float
    mss_cycle: str
    trend: str
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
            "mss_score": self.mss_score,
            "mss_temperature": self.mss_temperature,
            "mss_cycle": self.mss_cycle,
            "mss_trend": self.trend,
            "mss_position_advice": self.position_advice,
            "temperature": self.mss_temperature,
            "cycle": self.mss_cycle,
            "trend": self.trend,
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


def detect_trend(temperature_history: Sequence[float]) -> str:
    if len(temperature_history) < 3:
        return "sideways"

    recent = [float(value) for value in temperature_history[-3:]]
    if recent[0] < recent[1] < recent[2]:
        return "up"
    if recent[0] > recent[1] > recent[2]:
        return "down"
    return "sideways"


def detect_cycle(temperature: float, trend: str) -> str:
    if trend not in VALID_TRENDS:
        return "unknown"

    if temperature >= 75.0:
        return "climax"

    if trend == "up":
        if temperature < 30.0:
            return "emergence"
        if temperature < 45.0:
            return "fermentation"
        if temperature < 60.0:
            return "acceleration"
        return "divergence"

    if trend == "sideways":
        if temperature >= 60.0:
            return "divergence"
        return "recession"

    if trend == "down":
        if temperature >= 60.0:
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


def calculate_mss_score(
    snapshot: MssInputSnapshot,
    *,
    temperature_history: Sequence[float] | None = None,
) -> MssScoreResult:
    total_stocks = max(snapshot.total_stocks, 1)

    market_coefficient = _clamp(_safe_ratio(snapshot.rise_count, total_stocks) * 100.0, 0.0, 100.0)

    limit_up_ratio = _safe_ratio(snapshot.limit_up_count, total_stocks)
    new_high_ratio = _safe_ratio(snapshot.new_100d_high_count, total_stocks)
    strong_up_ratio = _safe_ratio(snapshot.strong_up_count, total_stocks)
    profit_effect_raw = 0.4 * limit_up_ratio + 0.3 * new_high_ratio + 0.3 * strong_up_ratio
    profit_effect = _clamp(profit_effect_raw * 100.0, 0.0, 100.0)

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
    loss_effect = _clamp(loss_effect_raw * 100.0, 0.0, 100.0)

    continuity_limit_ratio = _safe_ratio(
        snapshot.continuous_limit_up_2d + 2 * snapshot.continuous_limit_up_3d_plus,
        max(snapshot.limit_up_count, 1),
    )
    continuity_new_high_ratio = _safe_ratio(
        snapshot.continuous_new_high_2d_plus,
        max(snapshot.new_100d_high_count, 1),
    )
    continuity_factor = _clamp(
        (0.5 * continuity_limit_ratio + 0.5 * continuity_new_high_ratio) * 100.0,
        0.0,
        100.0,
    )

    panic_tail_ratio = _safe_ratio(snapshot.high_open_low_close_count, total_stocks)
    squeeze_tail_ratio = _safe_ratio(snapshot.low_open_high_close_count, total_stocks)
    extreme_factor = _clamp((panic_tail_ratio + squeeze_tail_ratio) * 100.0, 0.0, 100.0)
    if panic_tail_ratio + squeeze_tail_ratio <= 1e-12:
        extreme_direction_bias = 0.0
    else:
        extreme_direction_bias = _clamp(
            (squeeze_tail_ratio - panic_tail_ratio)
            / (panic_tail_ratio + squeeze_tail_ratio),
            -1.0,
            1.0,
        )

    normalized_pct_chg_std = _clamp(snapshot.pct_chg_std / 0.1, 0.0, 1.0)
    normalized_amount_volatility = _clamp(
        snapshot.amount_volatility / (snapshot.amount_volatility + 1_000_000.0),
        0.0,
        1.0,
    )
    volatility_factor = _clamp(
        (0.5 * normalized_pct_chg_std + 0.5 * normalized_amount_volatility) * 100.0,
        0.0,
        100.0,
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
    trend = detect_trend([*history, temperature])
    cycle = detect_cycle(temperature, trend)
    if cycle not in VALID_CYCLES:
        cycle = "unknown"

    neutrality = _clamp(1.0 - abs(temperature - 50.0) / 50.0, 0.0, 1.0)

    return MssScoreResult(
        trade_date=snapshot.trade_date,
        mss_score=temperature,
        mss_temperature=temperature,
        mss_cycle=cycle,
        trend=trend,
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
