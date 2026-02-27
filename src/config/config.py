"""全局配置模块 —— 整个 EmotionQuant 系统的唯一配置来源。

设计要点：
  1. 优先使用 pydantic-settings（自动读取 .env + 环境变量）；
     如果 pydantic-settings 未安装，则回退到 dataclass + os.getenv 的纯标准库方案。
  2. Config.from_env() 是全系统唯一的配置注入入口（对应执行卡 S0A）。
  3. 存储路径统一由 _resolve_storage_paths() 解析，支持环境变量覆盖或自动按 data_path 派生。
  4. TuShare 双通道（primary / fallback）由 _resolve_tushare_channels() 解析，
     提供向后兼容的 legacy → primary/fallback 自动迁移路径（对应执行卡 S3AR）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover
    BaseSettings = None
    SettingsConfigDict = None

# 默认数据根目录：~/.emotionquant/data
DEFAULT_DATA_PATH = str(Path.home() / ".emotionquant" / "data")


def _resolve_storage_paths(
    data_path: str, duckdb_dir: str, parquet_path: str, cache_path: str, log_path: str
) -> dict[str, str]:
    """解析并归一化存储路径。

    规则：如果单独的子路径（duckdb_dir / parquet_path / cache_path / log_path）
    未显式配置，则自动从 data_path（或 DEFAULT_DATA_PATH）下派生子目录。
    """
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
    """解析 TuShare 双通道配置（对应执行卡 S3AR）。

    解析优先级:
      primary > legacy（向后兼容）
    自动迁移规则:
      迁移路径1: primary 已配、fallback 空、legacy 不同于 primary → legacy 自动成为 fallback。
      迁移路径2: 仍无 fallback 且 primary 非官方 SDK → 用相同 token + 官方 SDK 作为 fallback。
    返回值中保留 tushare_token / tushare_sdk_provider / tushare_http_url 作为向后兼容别名。
    """
    normalized_primary_token = primary_token.strip()
    normalized_fallback_token = fallback_token.strip()
    normalized_legacy_token = legacy_token.strip()
    normalized_primary_provider = primary_sdk_provider.strip()
    normalized_fallback_provider = fallback_sdk_provider.strip()
    normalized_legacy_provider = legacy_sdk_provider.strip()
    normalized_primary_http_url = primary_http_url.strip()
    normalized_fallback_http_url = fallback_http_url.strip()
    normalized_legacy_http_url = legacy_http_url.strip()

    # 主通道: 优先使用 primary，若未配置则回退到 legacy
    resolved_primary_token = normalized_primary_token or normalized_legacy_token
    resolved_primary_provider = normalized_primary_provider or normalized_legacy_provider or "tushare"
    resolved_primary_http_url = normalized_primary_http_url or normalized_legacy_http_url

    # --- 迁移路径 1 ---
    # primary 和 legacy 均已配置且 token 不同，且 fallback 为空 → legacy 自动充当 fallback
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

    # --- 迁移路径 2 ---
    # 仍无 fallback 且 primary 使用非官方 SDK → 同 token + 官方 SDK 作为协议级 fallback
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
        # 向后兼容别名 —— 旧代码可继续用 tushare_token 访问
        "tushare_token": resolved_primary_token,
        "tushare_sdk_provider": resolved_primary_provider,
        "tushare_http_url": resolved_primary_http_url,
    }


if BaseSettings:

    class Config(BaseSettings):
        """全局配置（pydantic-settings 版本）。

        字段分组：
          - tushare_*          : TuShare 数据源凭证与限速
          - data_path / duckdb_dir / parquet_path / cache_path / log_path : 存储路径
          - flat_threshold / min_coverage_ratio / stale_hard_limit_days    : 数据质量门禁阈值
          - trading_*          : 实盘 / 模拟交易参数
          - backtest_*         : 回测引擎参数
        """

        # ---- TuShare 数据源 ----
        tushare_token: str = ""                          # 旧版单通道 token（向后兼容）
        tushare_sdk_provider: str = "tushare"            # SDK 提供者
        tushare_http_url: str = ""                       # HTTP 接口 URL
        tushare_primary_token: str = ""                  # 主通道 token
        tushare_primary_sdk_provider: str = ""
        tushare_primary_http_url: str = ""
        tushare_fallback_token: str = ""                 # 备用通道 token
        tushare_fallback_sdk_provider: str = "tushare"
        tushare_fallback_http_url: str = ""
        tushare_rate_limit_per_min: int = 120             # 全局限速（次/分钟）
        tushare_primary_rate_limit_per_min: int = 0       # 主通道限速（0=使用全局值）
        tushare_fallback_rate_limit_per_min: int = 0      # 备用通道限速

        # ---- 存储路径 ----
        data_path: str = ""           # 数据根目录（为空时使用 DEFAULT_DATA_PATH）
        duckdb_dir: str = ""          # DuckDB 数据库目录
        parquet_path: str = ""        # Parquet 文件目录
        cache_path: str = ""          # 缓存目录
        log_path: str = ""            # 日志目录

        # ---- 运行环境 & 数据质量门禁 ----
        log_level: str = "INFO"
        environment: str = "development"
        flat_threshold: float = 0.5              # 横盘判定阈值（MSS 算法用）
        min_coverage_ratio: float = 0.95         # 最低数据覆盖率要求
        stale_hard_limit_days: int = 3           # 数据过期硬限（天）
        enable_intraday_incremental: bool = False # 是否启用日内增量采集
        streamlit_port: int = 8501               # GUI 端口

        # ---- 交易参数 ----
        trading_max_industry_rank: int = 5       # 行业排名上限
        trading_min_irs_score: float = 50.0           # IRS 最低分
        trading_min_pas_score: float = 60.0           # PAS 最低分
        trading_top_n: int = 20                       # 每日最多推荐标的数（硬约束）
        trading_max_position_pct: float = 0.20        # 单只最大仓位占比
        trading_stop_loss_pct: float = 0.08           # 止损比例
        trading_take_profit_pct: float = 0.15         # 止盈比例
        trading_max_position_ratio: float = 0.20      # 单持仓占总资产上限
        trading_max_industry_ratio: float = 0.30      # 单行业占总仓位上限
        trading_max_total_position: float = 0.80      # 总仓位上限
        trading_stop_loss_ratio: float = 0.08         # 组合级止损
        trading_max_drawdown_limit: float = 0.15      # 最大回撤限制
        trading_min_quality_score: float = 55.0       # 最低质量分
        trading_high_risk_reduce_ratio: float = 0.6   # 高风险减仓比例
        trading_mid_risk_reduce_ratio: float = 0.8    # 中风险减仓比例
        trading_commission_rate: float = 0.0003       # 佣金费率
        trading_stamp_duty_rate: float = 0.001        # 印花税率（仅卖出）
        trading_transfer_fee_rate: float = 0.00002    # 过户费率
        trading_min_commission: float = 5.0           # 最低佣金（元）

        # ---- 回测参数 ----
        backtest_initial_cash: float = 1_000_000      # 初始资金
        backtest_initial_capital: float = 1_000_000   # 初始资金（别名，向后兼容）
        backtest_commission_rate: float = 0.0003      # 回测佣金费率
        backtest_stamp_duty_rate: float = 0.001       # 回测印花税率
        backtest_transfer_fee_rate: float = 0.00002   # 回测过户费率
        backtest_min_commission: float = 5.0          # 回测最低佣金
        backtest_risk_free_rate: float = 0.015        # 无风险利率（Sharpe 计算用）
        backtest_slippage_value: float = 0.001        # 滑点
        backtest_max_positions: int = 10              # 最大持仓数
        backtest_max_position_pct: float = 0.20       # 单只最大仓位
        backtest_stop_loss_pct: float = 0.08          # 回测止损
        backtest_take_profit_pct: float = 0.15        # 回测止盈
        backtest_min_final_score: float = 55.0        # 选股最低综合分
        backtest_top_n: int = 20                      # 候选池大小
        backtest_max_holding_days: int = 10            # 最大持仓天数

        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

        @classmethod
        def from_env(cls, *, env_file: str | None = ".env") -> Config:
            """从 .env 文件和环境变量构建配置实例（全系统唯一入口）。

            流程：
              1. pydantic-settings 自动加载 .env + 环境变量
              2. 向后兼容: backtest_initial_capital → backtest_initial_cash
              3. 解析双 TuShare 通道
              4. 解析存储路径
            """
            cfg = cls(_env_file=env_file)
            # 向后兼容：如果 initial_cash 是默认值但 initial_capital 被用户改过，以后者为准
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
        """全局配置（dataclass 回退版本，用于 pydantic-settings 未安装时）。

        字段与 pydantic-settings 版本完全一致，只是从 os.getenv() 手动读取。
        """
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
        tushare_primary_rate_limit_per_min: int = 0
        tushare_fallback_rate_limit_per_min: int = 0

        data_path: str = ""
        duckdb_dir: str = ""
        parquet_path: str = ""
        cache_path: str = ""
        log_path: str = ""

        log_level: str = "INFO"
        environment: str = "development"
        flat_threshold: float = 0.5
        min_coverage_ratio: float = 0.95
        stale_hard_limit_days: int = 3
        enable_intraday_incremental: bool = False
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
                tushare_primary_rate_limit_per_min=int(
                    os.getenv("TUSHARE_PRIMARY_RATE_LIMIT_PER_MIN", "0")
                ),
                tushare_fallback_rate_limit_per_min=int(
                    os.getenv("TUSHARE_FALLBACK_RATE_LIMIT_PER_MIN", "0")
                ),
                data_path=storage["data_path"],
                duckdb_dir=storage["duckdb_dir"],
                parquet_path=storage["parquet_path"],
                cache_path=storage["cache_path"],
                log_path=storage["log_path"],
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                environment=os.getenv("ENVIRONMENT", "development"),
                flat_threshold=float(os.getenv("FLAT_THRESHOLD", "0.5")),
                min_coverage_ratio=float(os.getenv("MIN_COVERAGE_RATIO", "0.95")),
                stale_hard_limit_days=int(os.getenv("STALE_HARD_LIMIT_DAYS", "3")),
                enable_intraday_incremental=os.getenv(
                    "ENABLE_INTRADAY_INCREMENTAL",
                    "false",
                ).strip().lower()
                in {"1", "true", "y", "yes"},
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
