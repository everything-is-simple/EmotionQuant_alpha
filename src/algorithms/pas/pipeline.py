from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from src.config.config import Config

# DESIGN_TRACE:
# - docs/design/core-algorithms/pas/pas-algorithm.md (3 三因子, 5 方向, 6 RR)
# - docs/design/core-algorithms/pas/pas-data-models.md (3 输出模型, 4 中间表)
# - Governance/SpiralRoadmap/S2C-EXECUTION-CARD.md (3 PAS, 6 artifact)
DESIGN_TRACE = {
    "pas_algorithm": "docs/design/core-algorithms/pas/pas-algorithm.md",
    "pas_data_models": "docs/design/core-algorithms/pas/pas-data-models.md",
    "s2c_execution_card": "Governance/SpiralRoadmap/S2C-EXECUTION-CARD.md",
}

SUPPORTED_CONTRACT_VERSION = "nc-v1"
EPS = 1e-9


@dataclass(frozen=True)
class PasRunResult:
    trade_date: str
    count: int
    frame: pd.DataFrame
    factor_intermediate_frame: pd.DataFrame
    factor_intermediate_sample_path: Path


def _table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _duckdb_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "BOOLEAN"
    if pd.api.types.is_integer_dtype(series):
        return "BIGINT"
    if pd.api.types.is_float_dtype(series):
        return "DOUBLE"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "TIMESTAMP"
    return "VARCHAR"


def _ensure_columns(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    frame: pd.DataFrame,
) -> list[str]:
    if not _table_exists(connection, table_name):
        connection.register("schema_df", frame)
        connection.execute(
            f"CREATE TABLE {table_name} AS SELECT * FROM schema_df WHERE 1=0"
        )
        connection.unregister("schema_df")
    else:
        existing = {
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        }
        for column in frame.columns:
            if column in existing:
                continue
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column} {_duckdb_type(frame[column])}"
            )

    return [
        str(row[1]) for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    ]


def _persist(
    *,
    database_path: Path,
    table_name: str,
    frame: pd.DataFrame,
    trade_date: str,
) -> int:
    with duckdb.connect(str(database_path)) as connection:
        table_columns = _ensure_columns(connection, table_name, frame)
        aligned = frame.copy()
        for column in table_columns:
            if column not in aligned.columns:
                aligned[column] = pd.NA
        aligned = aligned[table_columns]
        connection.register("incoming_df", aligned)
        connection.execute(f"DELETE FROM {table_name} WHERE trade_date = ?", [trade_date])
        connection.execute(f"INSERT INTO {table_name} SELECT * FROM incoming_df")
        connection.unregister("incoming_df")
    return int(len(aligned))


def _clip(value: float, low: float, high: float) -> float:
    return float(max(low, min(high, value)))


def _to_opportunity_grade(score: float) -> str:
    if score >= 85.0:
        return "S"
    if score >= 70.0:
        return "A"
    if score >= 55.0:
        return "B"
    if score >= 40.0:
        return "C"
    return "D"


def _choose_adaptive_window(volatility_20d: float, turnover_rate: float, window_mode: str) -> int:
    if window_mode == "fixed":
        return 60
    if volatility_20d >= 0.045 or turnover_rate >= 8.0:
        return 20
    if volatility_20d <= 0.020 and turnover_rate <= 3.0:
        return 120
    return 60


def _consecutive_count(flags: pd.Series) -> int:
    count = 0
    for value in reversed(flags.tolist()):
        if not bool(value):
            break
        count += 1
    return count


def _score_from_history(value: float, series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return 50.0
    mean = float(values.tail(120).mean())
    std = float(values.tail(120).std(ddof=0))
    if abs(std) <= EPS:
        return 50.0
    z = (float(value) - mean) / std
    return _clip(((z + 3.0) / 6.0) * 100.0, 0.0, 100.0)


def _coalesce_float(value: float | int | None, fallback: float) -> float:
    if value is None:
        return float(fallback)
    number = float(value)
    if pd.isna(number):
        return float(fallback)
    return number


def run_pas_daily(
    *,
    trade_date: str,
    config: Config,
    artifacts_dir: Path | None = None,
) -> PasRunResult:
    database_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    if not database_path.exists():
        raise FileNotFoundError("duckdb_not_found")

    with duckdb.connect(str(database_path), read_only=True) as connection:
        if not _table_exists(connection, "raw_daily"):
            raise ValueError("raw_daily_table_missing")

        source = connection.execute(
            "SELECT * FROM raw_daily WHERE trade_date = ? ORDER BY stock_code",
            [trade_date],
        ).df()
        history = connection.execute(
            "SELECT * FROM raw_daily WHERE trade_date <= ? ORDER BY trade_date, stock_code",
            [trade_date],
        ).df()

    if source.empty:
        raise ValueError("raw_daily_empty_for_trade_date")

    for column in ("open", "high", "low", "close", "vol", "amount"):
        if column not in source.columns:
            source[column] = 0.0
        source[column] = pd.to_numeric(source[column], errors="coerce").fillna(0.0)

        if column not in history.columns:
            history[column] = 0.0
        history[column] = pd.to_numeric(history[column], errors="coerce").fillna(0.0)

    output_rows: list[dict[str, object]] = []
    factor_rows: list[dict[str, object]] = []
    created_at = pd.Timestamp.utcnow().isoformat()

    for _, row in source.iterrows():
        item = row.to_dict()
        stock_code = str(item.get("stock_code", "")).strip()
        ts_code = str(item.get("ts_code", "")).strip()

        stock_hist = history[
            (history["stock_code"].astype(str) == stock_code)
            | (history["ts_code"].astype(str) == ts_code)
        ].copy()
        if stock_hist.empty:
            stock_hist = source[source["stock_code"].astype(str) == stock_code].copy()
        stock_hist = stock_hist.sort_values("trade_date")

        close_series = pd.to_numeric(stock_hist["close"], errors="coerce").fillna(0.0)
        open_series = pd.to_numeric(stock_hist["open"], errors="coerce").fillna(0.0)
        high_series = pd.to_numeric(stock_hist["high"], errors="coerce").fillna(0.0)
        low_series = pd.to_numeric(stock_hist["low"], errors="coerce").fillna(0.0)
        vol_series = pd.to_numeric(stock_hist["vol"], errors="coerce").fillna(0.0)
        amount_series = pd.to_numeric(stock_hist["amount"], errors="coerce").fillna(0.0)

        return_ratio_series = (close_series - open_series) / open_series.replace(0.0, pd.NA)
        return_ratio_series = return_ratio_series.fillna(0.0)
        pct_chg_series = close_series.pct_change().fillna(0.0)

        close = float(close_series.iloc[-1])
        high = float(high_series.iloc[-1])
        low = float(low_series.iloc[-1])
        vol = float(vol_series.iloc[-1])
        amount = float(amount_series.iloc[-1])
        pct_today = float(return_ratio_series.iloc[-1])

        volatility_20d = float(pct_chg_series.tail(20).std(ddof=0) or 0.0)
        turnover_rate = float(amount / max(close * 10000.0, 1.0))
        window_mode = "adaptive"
        adaptive_window = _choose_adaptive_window(volatility_20d, turnover_rate, window_mode)
        trend_window = int(_clip(round(adaptive_window / 3), 10, 40))

        history_days = int(len(stock_hist))
        sample_days = min(history_days, adaptive_window)
        stale_days = int(float(item.get("stale_days", 0) or 0))
        if stale_days > 0:
            quality_flag = "stale"
        elif sample_days < adaptive_window:
            quality_flag = "cold_start"
        else:
            quality_flag = "normal"

        high_20d_prev = _coalesce_float(high_series.shift(1).tail(20).max(), high)
        high_60d_prev = _coalesce_float(high_series.shift(1).tail(60).max(), high)
        low_20d_prev = _coalesce_float(low_series.shift(1).tail(20).min(), low)
        low_20d = _coalesce_float(low_series.tail(20).min(), low)

        up_flags = pct_chg_series > 0.0
        down_flags = pct_chg_series < 0.0
        consecutive_up_days = _consecutive_count(up_flags)
        consecutive_down_days = _consecutive_count(down_flags)

        if close > high_20d_prev and consecutive_up_days >= 3:
            direction = "bullish"
        elif close < low_20d_prev and consecutive_down_days >= 3:
            direction = "bearish"
        else:
            direction = "neutral"

        limit_up_ratio_120d = float((pct_chg_series.tail(120) >= 0.095).sum()) / max(
            float(min(len(stock_hist), 120)),
            1.0,
        )
        rolling_high_60 = close_series.rolling(window=60, min_periods=1).max()
        new_high_count_60d = float((close_series.tail(60) >= rolling_high_60.tail(60)).sum())
        new_high_ratio_60d = new_high_count_60d / max(float(min(len(stock_hist), 60)), 1.0)
        max_pct_chg_history = float(max(pct_chg_series.tail(120).max(), 0.0))
        max_pct_norm = _clip(max_pct_chg_history / 0.30, 0.0, 1.0)
        bull_gene_raw_series = pd.Series(
            [0.4 * limit_up_ratio_120d + 0.4 * new_high_ratio_60d + 0.2 * max_pct_norm]
        )
        bull_gene_raw = float(bull_gene_raw_series.iloc[-1])

        window_high = _coalesce_float(high_series.tail(adaptive_window).max(), high)
        window_low = _coalesce_float(low_series.tail(adaptive_window).min(), low)
        range_span = max(window_high - window_low, EPS)
        position = _clip((close - window_low) / range_span, 0.0, 1.0)
        breakout_ref = max(high_20d_prev, high_60d_prev)
        breakout_strength = _clip((close - breakout_ref) / max(abs(breakout_ref), EPS), -0.2, 0.2)
        breakout_strength_norm = _clip((breakout_strength + 0.2) / 0.4, 0.0, 1.0)
        structure_raw = 0.7 * position + 0.3 * breakout_strength_norm
        structure_raw_series = pd.Series([structure_raw])

        volume_avg_20d = float(vol_series.tail(20).mean() or 0.0)
        volume_quality = _clip(vol / max(volume_avg_20d, EPS), 0.0, 2.0) / 2.0
        pct_component = _clip((pct_today + 0.1) / 0.2, 0.0, 1.0)
        trend_component = _clip(
            consecutive_up_days / max(float(trend_window), 1.0),
            0.0,
            1.0,
        )
        behavior_raw = 0.4 * volume_quality + 0.4 * pct_component + 0.2 * trend_component
        behavior_raw_series = pd.Series([behavior_raw])

        bull_gene_score = _score_from_history(bull_gene_raw, bull_gene_raw_series)
        structure_score = _score_from_history(structure_raw, structure_raw_series)
        behavior_score = _score_from_history(behavior_raw, behavior_raw_series)

        opportunity_score = round(
            0.20 * bull_gene_score + 0.50 * structure_score + 0.30 * behavior_score,
            4,
        )

        entry = close if close > 0.0 else float(open_series.iloc[-1] or 1.0)
        stop = min(low_20d, entry * (1.0 - 0.08))
        risk = max(entry - stop, EPS)
        target_ref = max(high_20d_prev, high_60d_prev)
        breakout_floor = entry + risk
        if close > target_ref:
            target = max(target_ref, breakout_floor, entry * (1.0 + 0.08))
        else:
            target = max(target_ref, entry * 1.03)
        reward = max(target - entry, 0.0)
        risk_reward_ratio = max(reward / risk, 1.0)

        is_limit_up = bool(pct_today >= 0.095)
        is_touched_limit_up = bool(high >= entry * 1.095 and close < high)
        liquidity_discount = _clip(volume_quality, 0.50, 1.00)
        tradability_discount = 0.60 if is_limit_up else (0.80 if is_touched_limit_up else 1.00)
        effective_risk_reward_ratio = max(
            risk_reward_ratio * liquidity_discount * tradability_discount,
            0.0,
        )

        output_rows.append(
            {
                "trade_date": trade_date,
                "ts_code": ts_code,
                "stock_code": stock_code,
                "opportunity_score": opportunity_score,
                "pas_score": opportunity_score,
                "opportunity_grade": _to_opportunity_grade(opportunity_score),
                "direction": direction,
                "pas_direction": direction,
                "risk_reward_ratio": round(float(risk_reward_ratio), 6),
                "effective_risk_reward_ratio": round(float(effective_risk_reward_ratio), 6),
                "quality_flag": quality_flag,
                "sample_days": int(sample_days),
                "neutrality": round(_clip(1.0 - abs(opportunity_score - 50.0) / 50.0, 0.0, 1.0), 4),
                "window_mode": window_mode,
                "adaptive_window": int(adaptive_window),
                "trend_window": int(trend_window),
                "volatility_20d": round(float(volatility_20d), 6),
                "turnover_rate": round(float(turnover_rate), 6),
                "bull_gene_score": round(float(bull_gene_score), 4),
                "structure_score": round(float(structure_score), 4),
                "behavior_score": round(float(behavior_score), 4),
                "contract_version": SUPPORTED_CONTRACT_VERSION,
                "created_at": created_at,
            }
        )

        factor_rows.append(
            {
                "trade_date": trade_date,
                "stock_code": stock_code,
                "ts_code": ts_code,
                "bull_gene_raw": round(float(bull_gene_raw), 6),
                "structure_raw": round(float(structure_raw), 6),
                "behavior_raw": round(float(behavior_raw), 6),
                "volatility_20d": round(float(volatility_20d), 6),
                "turnover_rate": round(float(turnover_rate), 6),
                "adaptive_window": int(adaptive_window),
                "created_at": created_at,
            }
        )

    frame = pd.DataFrame.from_records(output_rows)
    frame = frame[
        [
            "trade_date",
            "ts_code",
            "stock_code",
            "opportunity_score",
            "pas_score",
            "opportunity_grade",
            "direction",
            "pas_direction",
            "risk_reward_ratio",
            "effective_risk_reward_ratio",
            "quality_flag",
            "sample_days",
            "neutrality",
            "window_mode",
            "adaptive_window",
            "trend_window",
            "volatility_20d",
            "turnover_rate",
            "bull_gene_score",
            "structure_score",
            "behavior_score",
            "contract_version",
            "created_at",
        ]
    ]

    count = _persist(
        database_path=database_path,
        table_name="stock_pas_daily",
        frame=frame,
        trade_date=trade_date,
    )

    factor_frame = pd.DataFrame.from_records(factor_rows)
    _persist(
        database_path=database_path,
        table_name="pas_factor_intermediate",
        frame=factor_frame,
        trade_date=trade_date,
    )

    target_artifacts_dir = artifacts_dir or (Path("artifacts") / "spiral-s2c" / trade_date)
    artifact_path = target_artifacts_dir / "pas_factor_intermediate_sample.parquet"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    factor_frame.to_parquet(artifact_path, index=False)

    return PasRunResult(
        trade_date=trade_date,
        count=count,
        frame=frame,
        factor_intermediate_frame=factor_frame,
        factor_intermediate_sample_path=artifact_path,
    )
