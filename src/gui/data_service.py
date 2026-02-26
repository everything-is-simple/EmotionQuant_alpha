"""GUI 数据服务层（只读消费 DuckDB）。

与 docs/design/core-infrastructure/gui/gui-api.md v3.2.0 §2 DataService 对齐。
所有查询以 read_only=True 打开连接，不执行任何写操作或算法计算。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from src.db.helpers import table_exists as _table_exists
from src.gui import formatter as fmt
from src.gui.models import (
    AnalysisPageData,
    BacktestSummaryDisplay,
    DashboardData,
    FilterConfig,
    FreshnessMeta,
    IndustryChartData,
    IndustryRankItem,
    IntegratedPageData,
    IrsPageData,
    MssPageData,
    MssPanoramaDisplay,
    PaginationInfo,
    PasPageData,
    PerformanceMetricsDisplay,
    PositionDisplay,
    RecommendationItem,
    StockPasDisplay,
    TemperatureChartData,
    TradeRecordDisplay,
    TradingPageData,
)

# DESIGN_TRACE:
# - docs/design/core-infrastructure/gui/gui-api.md (§2 DataService)
# - docs/design/core-infrastructure/gui/gui-algorithm.md (§6 缓存策略, §1.1 最小闭环)
# - Governance/SpiralRoadmap/execution-cards/S5-EXECUTION-CARD.md
DESIGN_TRACE = {
    "gui_api": "docs/design/core-infrastructure/gui/gui-api.md",
    "gui_algorithm": "docs/design/core-infrastructure/gui/gui-algorithm.md",
    "s5_execution_card": "Governance/SpiralRoadmap/execution-cards/S5-EXECUTION-CARD.md",
}

# 新鲜度 TTL（秒）
_FRESHNESS_TTL: dict[str, int] = {
    "l3_daily": 86400,       # 24h
    "trade_execution": 60,   # 1min
    "analysis_report": 86400,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _build_freshness(data_asof: str, ttl_key: str = "l3_daily") -> FreshnessMeta:
    """根据 data_asof 时间戳计算新鲜度等级。"""
    now = _utc_now()
    cache_created = now.isoformat()
    try:
        asof_dt = datetime.fromisoformat(data_asof)
        age_sec = max(0, int((now - asof_dt).total_seconds()))
    except (ValueError, TypeError):
        age_sec = 999999

    ttl = _FRESHNESS_TTL.get(ttl_key, 86400)
    if age_sec <= 0.5 * ttl:
        level = "fresh"
    elif age_sec <= ttl:
        level = "stale_soon"
    else:
        level = "stale"

    return FreshnessMeta(
        data_asof=data_asof,
        cache_created_at=cache_created,
        cache_age_sec=age_sec,
        freshness_level=level,
    )


def _paginate(total: int, page: int, page_size: int) -> PaginationInfo:
    total_pages = max(1, (total + page_size - 1) // page_size)
    return PaginationInfo(
        current_page=page,
        page_size=page_size,
        total_items=total,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
    )


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _safe_str(val: Any, default: str = "") -> str:
    if val is None:
        return default
    return str(val)


class DataService:
    """GUI 数据服务（只读）。"""

    def __init__(self, database_path: Path) -> None:
        self._db_path = database_path

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self._db_path), read_only=True)

    def _has_table(self, conn: duckdb.DuckDBPyConnection, name: str) -> bool:
        return _table_exists(conn, name)

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def get_dashboard_data(
        self, trade_date: str, *, top_n: int = 10, filters: FilterConfig | None = None
    ) -> DashboardData:
        fc = filters or FilterConfig()
        now_iso = _utc_now().isoformat()
        temperature = 0.0
        cycle = "unknown"
        trend = "sideways"
        position_advice = ""
        data_asof = now_iso
        recommendations: list[RecommendationItem] = []
        industries: list[IndustryRankItem] = []
        mode_badge = ""

        if self._db_path.exists():
            with self._connect() as conn:
                # MSS
                if self._has_table(conn, "mss_panorama"):
                    row = conn.execute(
                        "SELECT temperature, cycle, trend, position_advice "
                        "FROM mss_panorama WHERE CAST(trade_date AS VARCHAR) = ? LIMIT 1",
                        [trade_date],
                    ).fetchone()
                    if row:
                        temperature = _safe_float(row[0])
                        cycle = _safe_str(row[1], "unknown")
                        trend = _safe_str(row[2], "sideways")
                        position_advice = _safe_str(row[3])

                # Recommendations
                if self._has_table(conn, "integrated_recommendation"):
                    rows = conn.execute(
                        "SELECT * FROM integrated_recommendation "
                        "WHERE CAST(trade_date AS VARCHAR) = ? "
                        "ORDER BY final_score DESC LIMIT ?",
                        [trade_date, top_n],
                    ).fetchall()
                    col_names = [d[0] for d in conn.description] if conn.description else []
                    recommendations = self._map_recommendations(rows, col_names)
                    if recommendations:
                        mode_badge = recommendations[0].integration_mode_badge

                # Industries
                if self._has_table(conn, "irs_industry_daily"):
                    rows = conn.execute(
                        "SELECT * FROM irs_industry_daily "
                        "WHERE CAST(trade_date AS VARCHAR) = ? "
                        "ORDER BY industry_score DESC LIMIT 5",
                        [trade_date],
                    ).fetchall()
                    col_names = [d[0] for d in conn.description] if conn.description else []
                    industries = self._map_industries(rows, col_names)

        freshness = _build_freshness(data_asof)
        badges = fmt.build_filter_preset_badges("dashboard", fc)

        return DashboardData(
            temperature=temperature,
            temperature_color=fmt.temperature_color(temperature),
            cycle=cycle,
            trend=trend,
            position_advice=position_advice,
            trade_date=trade_date,
            data_asof=data_asof,
            freshness=freshness,
            active_filter_badges=badges,
            top_recommendations=recommendations,
            integration_mode_badge=mode_badge,
            top_industries=industries,
        )

    # ------------------------------------------------------------------
    # MSS Page
    # ------------------------------------------------------------------

    def get_mss_page_data(self, trade_date: str, *, history_days: int = 60) -> MssPageData:
        history: list[MssPanoramaDisplay] = []
        current: MssPanoramaDisplay | None = None

        if self._db_path.exists():
            with self._connect() as conn:
                if self._has_table(conn, "mss_panorama"):
                    rows = conn.execute(
                        "SELECT trade_date, temperature, cycle, trend, position_advice "
                        "FROM mss_panorama "
                        "WHERE CAST(trade_date AS VARCHAR) <= ? "
                        "ORDER BY trade_date DESC LIMIT ?",
                        [trade_date, history_days],
                    ).fetchall()
                    for r in rows:
                        td = _safe_str(r[0])
                        temp = _safe_float(r[1])
                        cyc = _safe_str(r[2], "unknown")
                        tr = _safe_str(r[3], "sideways")
                        adv = _safe_str(r[4])
                        icon, _ = fmt.format_trend(tr)
                        display = MssPanoramaDisplay(
                            trade_date=td,
                            temperature=temp,
                            temperature_color=fmt.temperature_color(temp),
                            cycle=cyc,
                            cycle_label=fmt.cycle_label(cyc),
                            trend=tr,
                            trend_icon=icon,
                            position_advice=adv,
                        )
                        history.append(display)
                    if history:
                        current = history[0]  # 最新一条

        chart = TemperatureChartData(
            x_axis=[h.trade_date for h in reversed(history)],
            y_axis=[h.temperature for h in reversed(history)],
        )
        return MssPageData(current=current, history=history, chart_data=chart)

    # ------------------------------------------------------------------
    # IRS Page
    # ------------------------------------------------------------------

    def get_irs_page_data(
        self, trade_date: str, *, filters: FilterConfig | None = None
    ) -> IrsPageData:
        industries: list[IndustryRankItem] = []

        if self._db_path.exists():
            with self._connect() as conn:
                if self._has_table(conn, "irs_industry_daily"):
                    rows = conn.execute(
                        "SELECT * FROM irs_industry_daily "
                        "WHERE CAST(trade_date AS VARCHAR) = ? "
                        "ORDER BY industry_score DESC",
                        [trade_date],
                    ).fetchall()
                    col_names = [d[0] for d in conn.description] if conn.description else []
                    industries = self._map_industries(rows, col_names)

        chart = IndustryChartData(
            x_axis=[i.industry_name for i in industries],
            y_axis=[i.industry_score for i in industries],
            colors=[i.status_color for i in industries],
        )
        return IrsPageData(trade_date=trade_date, industries=industries, chart_data=chart)

    # ------------------------------------------------------------------
    # PAS Page
    # ------------------------------------------------------------------

    def get_pas_page_data(
        self,
        trade_date: str,
        *,
        filters: FilterConfig | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PasPageData:
        stocks: list[StockPasDisplay] = []

        if self._db_path.exists():
            with self._connect() as conn:
                if self._has_table(conn, "stock_pas_daily"):
                    rows = conn.execute(
                        "SELECT * FROM stock_pas_daily "
                        "WHERE CAST(trade_date AS VARCHAR) = ? "
                        "ORDER BY opportunity_score DESC",
                        [trade_date],
                    ).fetchall()
                    col_names = [d[0] for d in conn.description] if conn.description else []
                    stocks = self._map_pas_stocks(rows, col_names)

        total = len(stocks)
        start = (page - 1) * page_size
        end = min(start + page_size, total)
        paged = stocks[start:end]
        pagination = _paginate(total, page, page_size)
        return PasPageData(trade_date=trade_date, stocks=paged, pagination=pagination)

    # ------------------------------------------------------------------
    # Integrated Page
    # ------------------------------------------------------------------

    def get_integrated_page_data(
        self,
        trade_date: str,
        *,
        filters: FilterConfig | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> IntegratedPageData:
        fc = filters or FilterConfig()
        now_iso = _utc_now().isoformat()
        recommendations: list[RecommendationItem] = []

        if self._db_path.exists():
            with self._connect() as conn:
                if self._has_table(conn, "integrated_recommendation"):
                    rows = conn.execute(
                        "SELECT * FROM integrated_recommendation "
                        "WHERE CAST(trade_date AS VARCHAR) = ? "
                        "ORDER BY final_score DESC",
                        [trade_date],
                    ).fetchall()
                    col_names = [d[0] for d in conn.description] if conn.description else []
                    recommendations = self._map_recommendations(rows, col_names)

        total = len(recommendations)
        start = (page - 1) * page_size
        end = min(start + page_size, total)
        paged = recommendations[start:end]
        pagination = _paginate(total, page, page_size)
        freshness = _build_freshness(now_iso)
        badges = fmt.build_filter_preset_badges("integrated", fc)

        return IntegratedPageData(
            trade_date=trade_date,
            recommendations=paged,
            pagination=pagination,
            data_asof=now_iso,
            freshness=freshness,
            active_filter_badges=badges,
        )

    # ------------------------------------------------------------------
    # Trading Page
    # ------------------------------------------------------------------

    def get_trading_page_data(
        self, trade_date: str, *, page: int = 1, page_size: int = 50
    ) -> TradingPageData:
        positions: list[PositionDisplay] = []
        trades: list[TradeRecordDisplay] = []

        if self._db_path.exists():
            with self._connect() as conn:
                if self._has_table(conn, "positions"):
                    rows = conn.execute(
                        "SELECT * FROM positions "
                        "WHERE CAST(trade_date AS VARCHAR) = ? "
                        "ORDER BY market_value DESC",
                        [trade_date],
                    ).fetchall()
                    col_names = [d[0] for d in conn.description] if conn.description else []
                    positions = self._map_positions(rows, col_names)

                if self._has_table(conn, "trade_records"):
                    rows = conn.execute(
                        "SELECT * FROM trade_records "
                        "WHERE CAST(trade_date AS VARCHAR) = ? "
                        "ORDER BY trade_id DESC",
                        [trade_date],
                    ).fetchall()
                    col_names = [d[0] for d in conn.description] if conn.description else []
                    trades = self._map_trades(rows, col_names)

        total_mv = sum(p.market_value for p in positions)
        total_pnl = sum(p.unrealized_pnl for p in positions)
        total_pnl_pct = total_pnl / total_mv if total_mv else 0.0

        total_trades = len(trades)
        start = (page - 1) * page_size
        end = min(start + page_size, total_trades)
        paged_trades = trades[start:end]
        pagination = _paginate(total_trades, page, page_size)

        return TradingPageData(
            trade_date=trade_date,
            positions=positions,
            total_market_value=total_mv,
            total_unrealized_pnl=total_pnl,
            total_unrealized_pnl_pct=total_pnl_pct,
            trades=paged_trades,
            pagination=pagination,
        )

    # ------------------------------------------------------------------
    # Analysis Page
    # ------------------------------------------------------------------

    def get_analysis_page_data(self, report_date: str) -> AnalysisPageData:
        metrics = PerformanceMetricsDisplay(
            total_return=0.0, total_return_pct="0.0%",
            annual_return=0.0, annual_return_pct="0.0%",
            max_drawdown=0.0, max_drawdown_pct="0.0%",
            sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0,
            win_rate=0.0, win_rate_pct="0.0%", profit_factor=0.0,
        )
        backtest = BacktestSummaryDisplay(
            backtest_name="", start_date="", end_date="",
            total_return_pct="0.0%", annual_return_pct="0.0%",
            max_drawdown_pct="0.0%", sharpe_ratio=0.0,
            total_trades=0, win_rate_pct="0.0%",
        )
        daily_report = ""

        if self._db_path.exists():
            with self._connect() as conn:
                if self._has_table(conn, "performance_metrics"):
                    row = conn.execute(
                        "SELECT * FROM performance_metrics "
                        "WHERE CAST(trade_date AS VARCHAR) = ? LIMIT 1",
                        [report_date],
                    ).fetchone()
                    if row:
                        col_names = [d[0] for d in conn.description] if conn.description else []
                        metrics = self._map_performance(row, col_names)

                if self._has_table(conn, "backtest_results"):
                    row = conn.execute(
                        "SELECT * FROM backtest_results "
                        "ORDER BY end_date DESC LIMIT 1",
                    ).fetchone()
                    if row:
                        col_names = [d[0] for d in conn.description] if conn.description else []
                        backtest = self._map_backtest(row, col_names)

                if self._has_table(conn, "daily_report"):
                    row = conn.execute(
                        "SELECT content FROM daily_report "
                        "WHERE CAST(report_date AS VARCHAR) = ? LIMIT 1",
                        [report_date],
                    ).fetchone()
                    if row:
                        daily_report = _safe_str(row[0])

        return AnalysisPageData(
            report_date=report_date,
            metrics=metrics,
            daily_report=daily_report,
            backtest_summary=backtest,
        )

    # ------------------------------------------------------------------
    # Row mappers (private)
    # ------------------------------------------------------------------

    def _col(self, col_names: list[str], row: tuple, name: str, default: Any = None) -> Any:
        try:
            idx = col_names.index(name)
            return row[idx]
        except (ValueError, IndexError):
            return default

    def _map_recommendations(
        self, rows: list[tuple], col_names: list[str]
    ) -> list[RecommendationItem]:
        result: list[RecommendationItem] = []
        for rank_idx, row in enumerate(rows, 1):
            score = _safe_float(self._col(col_names, row, "final_score"))
            rec = _safe_str(self._col(col_names, row, "recommendation"), "HOLD")
            mode = _safe_str(self._col(col_names, row, "integration_mode"), "")
            result.append(RecommendationItem(
                rank=rank_idx,
                stock_code=_safe_str(self._col(col_names, row, "stock_code")),
                stock_name=_safe_str(self._col(col_names, row, "stock_name")),
                industry_name=_safe_str(self._col(col_names, row, "industry_name")),
                final_score=score,
                recommendation=rec,
                recommendation_color=fmt.recommendation_color(rec),
                integration_mode=mode,
                integration_mode_badge=fmt.integration_mode_badge(mode),
                position_size=_safe_float(self._col(col_names, row, "position_size")),
                direction=_safe_str(self._col(col_names, row, "direction"), "neutral"),
                entry=_safe_float(self._col(col_names, row, "entry")),
                stop=_safe_float(self._col(col_names, row, "stop")),
                target=_safe_float(self._col(col_names, row, "target")),
                irs_score=_safe_float(self._col(col_names, row, "irs_score")),
                pas_score=_safe_float(self._col(col_names, row, "pas_score")),
            ))
        return result

    def _map_industries(
        self, rows: list[tuple], col_names: list[str]
    ) -> list[IndustryRankItem]:
        result: list[IndustryRankItem] = []
        for rank_idx, row in enumerate(rows, 1):
            status = _safe_str(self._col(col_names, row, "rotation_status"), "HOLD")
            result.append(IndustryRankItem(
                rank=rank_idx,
                industry_code=_safe_str(self._col(col_names, row, "industry_code")),
                industry_name=_safe_str(self._col(col_names, row, "industry_name")),
                industry_score=_safe_float(self._col(col_names, row, "industry_score")),
                rotation_status=status,
                status_color=fmt.rotation_status_color(status),
                allocation_advice=_safe_str(self._col(col_names, row, "allocation_advice")),
            ))
        return result

    def _map_pas_stocks(
        self, rows: list[tuple], col_names: list[str]
    ) -> list[StockPasDisplay]:
        result: list[StockPasDisplay] = []
        for row in rows:
            direction = _safe_str(self._col(col_names, row, "direction"), "neutral")
            grade = _safe_str(self._col(col_names, row, "opportunity_grade"), "C")
            neutrality = _safe_float(self._col(col_names, row, "neutrality"))
            icon, _ = fmt.format_trend(
                {"bullish": "up", "bearish": "down"}.get(direction, "sideways")
            )
            result.append(StockPasDisplay(
                stock_code=_safe_str(self._col(col_names, row, "stock_code")),
                stock_name=_safe_str(self._col(col_names, row, "stock_name")),
                industry_name=_safe_str(self._col(col_names, row, "industry_name")),
                opportunity_score=_safe_float(self._col(col_names, row, "opportunity_score")),
                opportunity_grade=grade,
                level_color=fmt.opportunity_level_color(grade),
                direction=direction,
                direction_icon=icon,
                neutrality=neutrality,
                neutrality_percent=int(neutrality * 100),
                risk_reward_ratio=_safe_float(self._col(col_names, row, "risk_reward_ratio")),
                suggested_entry=_safe_float(self._col(col_names, row, "suggested_entry")),
                suggested_stop=_safe_float(self._col(col_names, row, "suggested_stop")),
                suggested_target=_safe_float(self._col(col_names, row, "suggested_target")),
            ))
        return result

    def _map_positions(
        self, rows: list[tuple], col_names: list[str]
    ) -> list[PositionDisplay]:
        result: list[PositionDisplay] = []
        for row in rows:
            pnl = _safe_float(self._col(col_names, row, "unrealized_pnl"))
            mv = _safe_float(self._col(col_names, row, "market_value"))
            cost = _safe_float(self._col(col_names, row, "cost_price"))
            mp = _safe_float(self._col(col_names, row, "market_price"))
            pnl_pct = pnl / (cost * _safe_int(self._col(col_names, row, "shares"), 1)) if cost else 0.0
            is_frozen = bool(self._col(col_names, row, "is_frozen"))
            result.append(PositionDisplay(
                stock_code=_safe_str(self._col(col_names, row, "stock_code")),
                stock_name=_safe_str(self._col(col_names, row, "stock_name")),
                shares=_safe_int(self._col(col_names, row, "shares")),
                cost_price=cost,
                market_price=mp,
                market_value=mv,
                unrealized_pnl=pnl,
                unrealized_pnl_pct=pnl_pct,
                pnl_color=fmt.pnl_color(pnl),
                is_frozen=is_frozen,
                frozen_label="T+1冻结" if is_frozen else "",
                stop_price=_safe_float(self._col(col_names, row, "stop_price")),
                target_price=_safe_float(self._col(col_names, row, "target_price")),
            ))
        return result

    def _map_trades(
        self, rows: list[tuple], col_names: list[str]
    ) -> list[TradeRecordDisplay]:
        result: list[TradeRecordDisplay] = []
        for row in rows:
            direction = _safe_str(self._col(col_names, row, "direction"))
            status = _safe_str(self._col(col_names, row, "status"))
            result.append(TradeRecordDisplay(
                trade_id=_safe_str(self._col(col_names, row, "trade_id")),
                trade_date=_safe_str(self._col(col_names, row, "trade_date")),
                stock_code=_safe_str(self._col(col_names, row, "stock_code")),
                stock_name=_safe_str(self._col(col_names, row, "stock_name")),
                direction=direction,
                direction_label=fmt.direction_label(direction),
                direction_color=fmt.direction_color(direction),
                price=_safe_float(self._col(col_names, row, "price")),
                shares=_safe_int(self._col(col_names, row, "shares")),
                amount=_safe_float(self._col(col_names, row, "amount")),
                total_fee=_safe_float(self._col(col_names, row, "total_fee")),
                status=status,
                status_label=fmt.status_label(status),
            ))
        return result

    def _map_performance(
        self, row: tuple, col_names: list[str]
    ) -> PerformanceMetricsDisplay:
        tr = _safe_float(self._col(col_names, row, "total_return"))
        ar = _safe_float(self._col(col_names, row, "annual_return"))
        md = _safe_float(self._col(col_names, row, "max_drawdown"))
        wr = _safe_float(self._col(col_names, row, "win_rate"))
        return PerformanceMetricsDisplay(
            total_return=tr,
            total_return_pct=fmt.format_percent(tr, with_sign=True),
            annual_return=ar,
            annual_return_pct=fmt.format_percent(ar, with_sign=True),
            max_drawdown=md,
            max_drawdown_pct=fmt.format_percent(md, with_sign=True),
            sharpe_ratio=_safe_float(self._col(col_names, row, "sharpe_ratio")),
            sortino_ratio=_safe_float(self._col(col_names, row, "sortino_ratio")),
            calmar_ratio=_safe_float(self._col(col_names, row, "calmar_ratio")),
            win_rate=wr,
            win_rate_pct=fmt.format_percent(wr),
            profit_factor=_safe_float(self._col(col_names, row, "profit_factor")),
        )

    def _map_backtest(
        self, row: tuple, col_names: list[str]
    ) -> BacktestSummaryDisplay:
        tr = _safe_float(self._col(col_names, row, "total_return"))
        ar = _safe_float(self._col(col_names, row, "annual_return"))
        md = _safe_float(self._col(col_names, row, "max_drawdown"))
        wr = _safe_float(self._col(col_names, row, "win_rate"))
        return BacktestSummaryDisplay(
            backtest_name=_safe_str(self._col(col_names, row, "backtest_name")),
            start_date=_safe_str(self._col(col_names, row, "start_date")),
            end_date=_safe_str(self._col(col_names, row, "end_date")),
            total_return_pct=fmt.format_percent(tr, with_sign=True),
            annual_return_pct=fmt.format_percent(ar, with_sign=True),
            max_drawdown_pct=fmt.format_percent(md, with_sign=True),
            sharpe_ratio=_safe_float(self._col(col_names, row, "sharpe_ratio")),
            total_trades=_safe_int(self._col(col_names, row, "total_trades")),
            win_rate_pct=fmt.format_percent(wr),
        )
