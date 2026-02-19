from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover
    BaseSettings = None
    SettingsConfigDict = None

DEFAULT_DATA_PATH = str(Path.home() / ".emotionquant" / "data")


def _resolve_storage_paths(
    data_path: str, duckdb_dir: str, parquet_path: str, cache_path: str, log_path: str
) -> dict[str, str]:
    def _normalized(value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    normalized_data_path = _normalized(data_path)
    normalized_duckdb_dir = _normalized(duckdb_dir)
    normalized_parquet_path = _normalized(parquet_path)
    normalized_cache_path = _normalized(cache_path)
    normalized_log_path = _normalized(log_path)

    resolved_data_path = normalized_data_path or DEFAULT_DATA_PATH
    base = Path(resolved_data_path)
    return {
        "data_path": str(base),
        "duckdb_dir": normalized_duckdb_dir or str(base / "duckdb"),
        "parquet_path": normalized_parquet_path or str(base / "parquet"),
        "cache_path": normalized_cache_path or str(base / "cache"),
        "log_path": normalized_log_path or str(base / "logs"),
    }


def _resolve_tushare_channels(
    *,
    primary_token: str,
    primary_sdk_provider: str,
    primary_http_url: str,
    fallback_token: str,
    fallback_sdk_provider: str,
    fallback_http_url: str,
    legacy_token: str,
    legacy_sdk_provider: str,
    legacy_http_url: str,
) -> dict[str, str]:
    normalized_primary_token = primary_token.strip()
    normalized_fallback_token = fallback_token.strip()
    normalized_legacy_token = legacy_token.strip()
    normalized_primary_provider = primary_sdk_provider.strip()
    normalized_fallback_provider = fallback_sdk_provider.strip()
    normalized_legacy_provider = legacy_sdk_provider.strip()
    normalized_primary_http_url = primary_http_url.strip()
    normalized_fallback_http_url = fallback_http_url.strip()
    normalized_legacy_http_url = legacy_http_url.strip()

    resolved_primary_token = normalized_primary_token or normalized_legacy_token
    resolved_primary_provider = normalized_primary_provider or normalized_legacy_provider or "tushare"
    resolved_primary_http_url = normalized_primary_http_url or normalized_legacy_http_url

    # Backward-compatible migration path 1:
    # if primary channel is configured and fallback is empty, reuse legacy token as fallback.
    auto_fallback_from_legacy = (
        (not normalized_fallback_token)
        and bool(normalized_primary_token)
        and bool(normalized_legacy_token)
        and normalized_legacy_token != normalized_primary_token
    )
    resolved_fallback_token = normalized_legacy_token if auto_fallback_from_legacy else normalized_fallback_token
    resolved_fallback_provider = (
        (normalized_legacy_provider or "tushare")
        if auto_fallback_from_legacy
        else (normalized_fallback_provider or "tushare")
    )
    resolved_fallback_http_url = (
        normalized_legacy_http_url if auto_fallback_from_legacy else normalized_fallback_http_url
    )

    # Backward-compatible migration path 2:
    # if still no fallback and primary provider is not tushare, add protocol fallback:
    # same token with official tushare SDK provider.
    if (
        not resolved_fallback_token
        and bool(resolved_primary_token)
        and resolved_primary_provider.strip().lower() != "tushare"
    ):
        resolved_fallback_token = resolved_primary_token
        resolved_fallback_provider = "tushare"
        resolved_fallback_http_url = resolved_primary_http_url
    return {
        "tushare_primary_token": resolved_primary_token,
        "tushare_primary_sdk_provider": resolved_primary_provider,
        "tushare_primary_http_url": resolved_primary_http_url,
        "tushare_fallback_token": resolved_fallback_token,
        "tushare_fallback_sdk_provider": resolved_fallback_provider,
        "tushare_fallback_http_url": resolved_fallback_http_url,
        # Backward-compatible aliases.
        "tushare_token": resolved_primary_token,
        "tushare_sdk_provider": resolved_primary_provider,
        "tushare_http_url": resolved_primary_http_url,
    }


if BaseSettings:

    class Config(BaseSettings):
        tushare_token: str = ""
        tushare_sdk_provider: str = "tushare"
        tushare_http_url: str = ""
        tushare_primary_token: str = ""
        tushare_primary_sdk_provider: str = ""
        tushare_primary_http_url: str = ""
        tushare_fallback_token: str = ""
        tushare_fallback_sdk_provider: str = "tushare"
        tushare_fallback_http_url: str = ""
        tushare_rate_limit_per_min: int = 120

        data_path: str = ""
        duckdb_dir: str = ""
        parquet_path: str = ""
        cache_path: str = ""
        log_path: str = ""

        log_level: str = "INFO"
        environment: str = "development"
        streamlit_port: int = 8501
        trading_max_industry_rank: int = 5
        trading_min_irs_score: float = 50.0
        trading_min_pas_score: float = 60.0
        trading_top_n: int = 20
        trading_max_position_pct: float = 0.20
        trading_stop_loss_pct: float = 0.08
        trading_take_profit_pct: float = 0.15
        trading_max_position_ratio: float = 0.20
        trading_max_industry_ratio: float = 0.30
        trading_max_total_position: float = 0.80
        trading_stop_loss_ratio: float = 0.08
        trading_max_drawdown_limit: float = 0.15
        trading_min_quality_score: float = 55.0
        trading_high_risk_reduce_ratio: float = 0.6
        trading_mid_risk_reduce_ratio: float = 0.8
        trading_commission_rate: float = 0.0003
        trading_stamp_duty_rate: float = 0.001
        trading_transfer_fee_rate: float = 0.00002
        trading_min_commission: float = 5.0
        backtest_initial_cash: float = 1_000_000
        backtest_initial_capital: float = 1_000_000
        backtest_commission_rate: float = 0.0003
        backtest_stamp_duty_rate: float = 0.001
        backtest_transfer_fee_rate: float = 0.00002
        backtest_min_commission: float = 5.0
        backtest_risk_free_rate: float = 0.015
        backtest_slippage_value: float = 0.001
        backtest_max_positions: int = 10
        backtest_max_position_pct: float = 0.20
        backtest_stop_loss_pct: float = 0.08
        backtest_take_profit_pct: float = 0.15
        backtest_min_final_score: float = 55.0
        backtest_top_n: int = 20
        backtest_max_holding_days: int = 10

        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

        @classmethod
        def from_env(cls, *, env_file: str | None = ".env") -> Config:
            cfg = cls(_env_file=env_file)
            default_initial_cash = 1_000_000.0
            initial_cash = cfg.backtest_initial_cash
            if (
                initial_cash == default_initial_cash
                and cfg.backtest_initial_capital != default_initial_cash
            ):
                initial_cash = cfg.backtest_initial_capital
            tushare_channels = _resolve_tushare_channels(
                primary_token=cfg.tushare_primary_token,
                primary_sdk_provider=cfg.tushare_primary_sdk_provider,
                primary_http_url=cfg.tushare_primary_http_url,
                fallback_token=cfg.tushare_fallback_token,
                fallback_sdk_provider=cfg.tushare_fallback_sdk_provider,
                fallback_http_url=cfg.tushare_fallback_http_url,
                legacy_token=cfg.tushare_token,
                legacy_sdk_provider=cfg.tushare_sdk_provider,
                legacy_http_url=cfg.tushare_http_url,
            )
            return cfg.model_copy(
                update=_resolve_storage_paths(
                    cfg.data_path,
                    cfg.duckdb_dir,
                    cfg.parquet_path,
                    cfg.cache_path,
                    cfg.log_path,
                )
                | tushare_channels
                | {
                    "backtest_initial_cash": initial_cash,
                    "backtest_initial_capital": initial_cash,
                }
            )

        @classmethod
        def load(cls) -> Config:
            return cls.from_env()

else:

    @dataclass(frozen=True)
    class Config:
        tushare_token: str = ""
        tushare_sdk_provider: str = "tushare"
        tushare_http_url: str = ""
        tushare_primary_token: str = ""
        tushare_primary_sdk_provider: str = ""
        tushare_primary_http_url: str = ""
        tushare_fallback_token: str = ""
        tushare_fallback_sdk_provider: str = "tushare"
        tushare_fallback_http_url: str = ""
        tushare_rate_limit_per_min: int = 120

        data_path: str = ""
        duckdb_dir: str = ""
        parquet_path: str = ""
        cache_path: str = ""
        log_path: str = ""

        log_level: str = "INFO"
        environment: str = "development"
        streamlit_port: int = 8501
        trading_max_industry_rank: int = 5
        trading_min_irs_score: float = 50.0
        trading_min_pas_score: float = 60.0
        trading_top_n: int = 20
        trading_max_position_pct: float = 0.20
        trading_stop_loss_pct: float = 0.08
        trading_take_profit_pct: float = 0.15
        trading_max_position_ratio: float = 0.20
        trading_max_industry_ratio: float = 0.30
        trading_max_total_position: float = 0.80
        trading_stop_loss_ratio: float = 0.08
        trading_max_drawdown_limit: float = 0.15
        trading_min_quality_score: float = 55.0
        trading_high_risk_reduce_ratio: float = 0.6
        trading_mid_risk_reduce_ratio: float = 0.8
        trading_commission_rate: float = 0.0003
        trading_stamp_duty_rate: float = 0.001
        trading_transfer_fee_rate: float = 0.00002
        trading_min_commission: float = 5.0
        backtest_initial_cash: float = 1_000_000
        backtest_initial_capital: float = 1_000_000
        backtest_commission_rate: float = 0.0003
        backtest_stamp_duty_rate: float = 0.001
        backtest_transfer_fee_rate: float = 0.00002
        backtest_min_commission: float = 5.0
        backtest_risk_free_rate: float = 0.015
        backtest_slippage_value: float = 0.001
        backtest_max_positions: int = 10
        backtest_max_position_pct: float = 0.20
        backtest_stop_loss_pct: float = 0.08
        backtest_take_profit_pct: float = 0.15
        backtest_min_final_score: float = 55.0
        backtest_top_n: int = 20
        backtest_max_holding_days: int = 10

        @classmethod
        def from_env(cls, *, env_file: str | None = ".env") -> Config:
            initial_cash_env = os.getenv("BACKTEST_INITIAL_CASH")
            initial_capital_env = os.getenv("BACKTEST_INITIAL_CAPITAL")
            if initial_cash_env is not None:
                initial_cash = float(initial_cash_env)
            elif initial_capital_env is not None:
                initial_cash = float(initial_capital_env)
            else:
                initial_cash = 1_000_000
            storage = _resolve_storage_paths(
                os.getenv("DATA_PATH", ""),
                os.getenv("DUCKDB_DIR", ""),
                os.getenv("PARQUET_PATH", ""),
                os.getenv("CACHE_PATH", ""),
                os.getenv("LOG_PATH", ""),
            )
            tushare_channels = _resolve_tushare_channels(
                primary_token=os.getenv("TUSHARE_PRIMARY_TOKEN", ""),
                primary_sdk_provider=os.getenv("TUSHARE_PRIMARY_SDK_PROVIDER", ""),
                primary_http_url=os.getenv("TUSHARE_PRIMARY_HTTP_URL", ""),
                fallback_token=os.getenv("TUSHARE_FALLBACK_TOKEN", ""),
                fallback_sdk_provider=os.getenv("TUSHARE_FALLBACK_SDK_PROVIDER", "tushare"),
                fallback_http_url=os.getenv("TUSHARE_FALLBACK_HTTP_URL", ""),
                legacy_token=os.getenv("TUSHARE_TOKEN", ""),
                legacy_sdk_provider=os.getenv("TUSHARE_SDK_PROVIDER", "tushare"),
                legacy_http_url=os.getenv("TUSHARE_HTTP_URL", ""),
            )
            return cls(
                tushare_token=tushare_channels["tushare_token"],
                tushare_sdk_provider=tushare_channels["tushare_sdk_provider"],
                tushare_http_url=tushare_channels["tushare_http_url"],
                tushare_primary_token=tushare_channels["tushare_primary_token"],
                tushare_primary_sdk_provider=tushare_channels["tushare_primary_sdk_provider"],
                tushare_primary_http_url=tushare_channels["tushare_primary_http_url"],
                tushare_fallback_token=tushare_channels["tushare_fallback_token"],
                tushare_fallback_sdk_provider=tushare_channels["tushare_fallback_sdk_provider"],
                tushare_fallback_http_url=tushare_channels["tushare_fallback_http_url"],
                tushare_rate_limit_per_min=int(
                    os.getenv("TUSHARE_RATE_LIMIT_PER_MIN", "120")
                ),
                data_path=storage["data_path"],
                duckdb_dir=storage["duckdb_dir"],
                parquet_path=storage["parquet_path"],
                cache_path=storage["cache_path"],
                log_path=storage["log_path"],
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                environment=os.getenv("ENVIRONMENT", "development"),
                streamlit_port=int(os.getenv("STREAMLIT_PORT", "8501")),
                trading_max_industry_rank=int(
                    os.getenv("TRADING_MAX_INDUSTRY_RANK", "5")
                ),
                trading_min_irs_score=float(
                    os.getenv("TRADING_MIN_IRS_SCORE", "50.0")
                ),
                trading_min_pas_score=float(
                    os.getenv("TRADING_MIN_PAS_SCORE", "60.0")
                ),
                trading_top_n=int(os.getenv("TRADING_TOP_N", "20")),
                trading_max_position_pct=float(
                    os.getenv("TRADING_MAX_POSITION_PCT", "0.20")
                ),
                trading_stop_loss_pct=float(
                    os.getenv("TRADING_STOP_LOSS_PCT", "0.08")
                ),
                trading_take_profit_pct=float(
                    os.getenv("TRADING_TAKE_PROFIT_PCT", "0.15")
                ),
                trading_max_position_ratio=float(
                    os.getenv("TRADING_MAX_POSITION_RATIO", "0.20")
                ),
                trading_max_industry_ratio=float(
                    os.getenv("TRADING_MAX_INDUSTRY_RATIO", "0.30")
                ),
                trading_max_total_position=float(
                    os.getenv("TRADING_MAX_TOTAL_POSITION", "0.80")
                ),
                trading_stop_loss_ratio=float(
                    os.getenv("TRADING_STOP_LOSS_RATIO", "0.08")
                ),
                trading_max_drawdown_limit=float(
                    os.getenv("TRADING_MAX_DRAWDOWN_LIMIT", "0.15")
                ),
                trading_min_quality_score=float(
                    os.getenv("TRADING_MIN_QUALITY_SCORE", "55.0")
                ),
                trading_high_risk_reduce_ratio=float(
                    os.getenv("TRADING_HIGH_RISK_REDUCE_RATIO", "0.6")
                ),
                trading_mid_risk_reduce_ratio=float(
                    os.getenv("TRADING_MID_RISK_REDUCE_RATIO", "0.8")
                ),
                trading_commission_rate=float(
                    os.getenv("TRADING_COMMISSION_RATE", "0.0003")
                ),
                trading_stamp_duty_rate=float(
                    os.getenv("TRADING_STAMP_DUTY_RATE", "0.001")
                ),
                trading_transfer_fee_rate=float(
                    os.getenv("TRADING_TRANSFER_FEE_RATE", "0.00002")
                ),
                trading_min_commission=float(
                    os.getenv("TRADING_MIN_COMMISSION", "5.0")
                ),
                backtest_initial_cash=initial_cash,
                backtest_initial_capital=initial_cash,
                backtest_commission_rate=float(
                    os.getenv("BACKTEST_COMMISSION_RATE", "0.0003")
                ),
                backtest_stamp_duty_rate=float(
                    os.getenv("BACKTEST_STAMP_DUTY_RATE", "0.001")
                ),
                backtest_transfer_fee_rate=float(
                    os.getenv("BACKTEST_TRANSFER_FEE_RATE", "0.00002")
                ),
                backtest_min_commission=float(
                    os.getenv("BACKTEST_MIN_COMMISSION", "5.0")
                ),
                backtest_risk_free_rate=float(
                    os.getenv("BACKTEST_RISK_FREE_RATE", "0.015")
                ),
                backtest_slippage_value=float(
                    os.getenv("BACKTEST_SLIPPAGE_VALUE", "0.001")
                ),
                backtest_max_positions=int(
                    os.getenv("BACKTEST_MAX_POSITIONS", "10")
                ),
                backtest_max_position_pct=float(
                    os.getenv("BACKTEST_MAX_POSITION_PCT", "0.20")
                ),
                backtest_stop_loss_pct=float(
                    os.getenv("BACKTEST_STOP_LOSS_PCT", "0.08")
                ),
                backtest_take_profit_pct=float(
                    os.getenv("BACKTEST_TAKE_PROFIT_PCT", "0.15")
                ),
                backtest_min_final_score=float(
                    os.getenv("BACKTEST_MIN_FINAL_SCORE", "55.0")
                ),
                backtest_top_n=int(
                    os.getenv("BACKTEST_TOP_N", "20")
                ),
                backtest_max_holding_days=int(
                    os.getenv("BACKTEST_MAX_HOLDING_DAYS", "10")
                ),
            )

        @classmethod
        def load(cls) -> Config:
            return cls.from_env()
