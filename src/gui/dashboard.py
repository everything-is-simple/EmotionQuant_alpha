"""EmotionQuant S5 Streamlit 仪表盘（7 页面 Tab 布局）。

只读展示：不在页面层执行任何算法计算。
所有数据来自 L3/L4 层预计算结果（DuckDB read_only）。
色彩约定：A 股红涨绿跌。
"""

from __future__ import annotations

import argparse
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from src.gui import formatter as fmt
from src.gui.data_service import DataService

# DESIGN_TRACE:
# - docs/design/core-infrastructure/gui/gui-algorithm.md (§1.1 最小闭环, §3 仪表盘只读展示)
# - docs/design/core-infrastructure/gui/gui-api.md (§1 模块结构 — 7 页面)
# - Governance/SpiralRoadmap/execution-cards/S5-EXECUTION-CARD.md (§3 模块级补齐任务)
DESIGN_TRACE = {
    "gui_algorithm": "docs/design/core-infrastructure/gui/gui-algorithm.md",
    "gui_api": "docs/design/core-infrastructure/gui/gui-api.md",
    "s5_execution_card": "Governance/SpiralRoadmap/execution-cards/S5-EXECUTION-CARD.md",
}

PAGE_NAMES: list[str] = [
    "Dashboard", "MSS", "IRS", "PAS", "Integrated", "Trading", "Analysis",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--trade-date", default=os.getenv("EQ_GUI_TRADE_DATE", "").strip())
    parser.add_argument("--duckdb-path", default=os.getenv("EQ_GUI_DUCKDB_PATH", "").strip())
    args, _ = parser.parse_known_args()
    return args


# ---------------------------------------------------------------------------
# 7 页面渲染函数
# ---------------------------------------------------------------------------

def _render_dashboard(svc: DataService, trade_date: str) -> None:
    """Dashboard 总览页。"""
    data = svc.get_dashboard_data(trade_date)
    temp_card = fmt.format_temperature(data.temperature, data.trend)
    cycle_badge = fmt.format_cycle(data.cycle)

    # 新鲜度徽标
    freshness = data.freshness
    if freshness.freshness_level == "stale":
        st.warning(f"数据可能已过期（cache_age={freshness.cache_age_sec}s）")

    # 温度 + 周期 + 趋势
    col_t, col_c, col_tr = st.columns(3)
    col_t.metric("市场温度", f"{temp_card.value:.1f}°C", delta=temp_card.label)
    col_c.metric("情绪周期", cycle_badge.label)
    trend_icon, _ = fmt.format_trend(data.trend)
    col_tr.metric("趋势", f"{data.trend} {trend_icon}")

    # 过滤阈值
    if data.active_filter_badges:
        st.caption("当前过滤阈值：" + " | ".join(data.active_filter_badges))

    # 推荐列表
    st.subheader("Top 推荐（只读）")
    if data.top_recommendations:
        rows = [asdict(r) for r in data.top_recommendations]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("当日无推荐数据。")

    # 行业热点
    st.subheader("行业热点 Top 5")
    if data.top_industries:
        rows = [asdict(i) for i in data.top_industries]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("当日无行业数据。")


def _render_mss(svc: DataService, trade_date: str) -> None:
    """MSS 市场情绪页。"""
    data = svc.get_mss_page_data(trade_date)

    if data.current:
        c = data.current
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("温度", f"{c.temperature:.1f}°C")
        col_b.metric("周期", f"{c.cycle_label}")
        col_c.metric("趋势", f"{c.trend} {c.trend_icon}")
        if c.position_advice:
            st.info(f"仓位建议：{c.position_advice}")
    else:
        st.info("当日无 MSS 数据。")

    # 温度曲线
    if data.chart_data.x_axis:
        fig = go.Figure(go.Scatter(
            x=data.chart_data.x_axis,
            y=data.chart_data.y_axis,
            mode="lines+markers",
            name="温度",
        ))
        fig.update_layout(title="温度曲线（近60日）", yaxis_title="温度°C")
        st.plotly_chart(fig, use_container_width=True)


def _render_irs(svc: DataService, trade_date: str) -> None:
    """IRS 行业轮动页。"""
    data = svc.get_irs_page_data(trade_date)

    if data.industries:
        rows = [asdict(i) for i in data.industries]
        st.dataframe(rows, use_container_width=True, hide_index=True)

        # 柱状图
        if data.chart_data.x_axis:
            fig = go.Figure(go.Bar(
                x=data.chart_data.x_axis,
                y=data.chart_data.y_axis,
                marker_color=data.chart_data.colors,
            ))
            fig.update_layout(title="行业评分排名", yaxis_title="评分")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("当日无 IRS 行业数据。")


def _render_pas(svc: DataService, trade_date: str) -> None:
    """PAS 个股评级页。"""
    data = svc.get_pas_page_data(trade_date)

    st.caption(f"共 {data.pagination.total_items} 只，第 {data.pagination.current_page}/{data.pagination.total_pages} 页")
    if data.stocks:
        rows = [asdict(s) for s in data.stocks]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("当日无 PAS 数据。")


def _render_integrated(svc: DataService, trade_date: str) -> None:
    """集成推荐页。"""
    data = svc.get_integrated_page_data(trade_date)

    # 新鲜度
    freshness = data.freshness
    if freshness.freshness_level == "stale":
        st.warning(f"数据可能已过期（cache_age={freshness.cache_age_sec}s）")

    # 过滤阈值
    if data.active_filter_badges:
        st.caption("当前过滤阈值：" + " | ".join(data.active_filter_badges))

    st.caption(f"共 {data.pagination.total_items} 条，第 {data.pagination.current_page}/{data.pagination.total_pages} 页")
    if data.recommendations:
        rows = [asdict(r) for r in data.recommendations]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("当日无集成推荐数据。")


def _render_trading(svc: DataService, trade_date: str) -> None:
    """交易执行页。"""
    data = svc.get_trading_page_data(trade_date)

    # 持仓概览
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("总市值", f"{data.total_market_value:,.2f}")
    pnl_c = fmt.pnl_color(data.total_unrealized_pnl)
    col_b.metric("未实现盈亏", f"{data.total_unrealized_pnl:+,.2f}")
    col_c.metric("盈亏比例", fmt.format_percent(data.total_unrealized_pnl_pct, with_sign=True))

    st.subheader("持仓")
    if data.positions:
        rows = [asdict(p) for p in data.positions]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("当日无持仓。")

    st.subheader("交易记录")
    if data.trades:
        rows = [asdict(t) for t in data.trades]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("当日无交易记录。")


def _render_analysis(svc: DataService, trade_date: str) -> None:
    """分析报告页。"""
    data = svc.get_analysis_page_data(trade_date)

    # KPI 卡片
    m = data.metrics
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("总收益", m.total_return_pct)
    col_b.metric("年化收益", m.annual_return_pct)
    col_c.metric("最大回撤", m.max_drawdown_pct)
    col_d.metric("夏普比率", f"{m.sharpe_ratio:.2f}")

    col_e, col_f, col_g = st.columns(3)
    col_e.metric("胜率", m.win_rate_pct)
    col_f.metric("Sortino", f"{m.sortino_ratio:.2f}")
    col_g.metric("盈亏比", f"{m.profit_factor:.2f}")

    # 回测摘要
    b = data.backtest_summary
    if b.backtest_name:
        st.subheader(f"回测摘要：{b.backtest_name}")
        st.write(f"- 区间：{b.start_date} ~ {b.end_date}")
        st.write(f"- 总收益 {b.total_return_pct} | 年化 {b.annual_return_pct} | 回撤 {b.max_drawdown_pct}")
        st.write(f"- 夏普 {b.sharpe_ratio:.2f} | 交易 {b.total_trades} 笔 | 胜率 {b.win_rate_pct}")

    # 日报
    if data.daily_report:
        st.subheader("日报")
        st.markdown(data.daily_report)


# ---------------------------------------------------------------------------
# 兼容旧调用入口
# ---------------------------------------------------------------------------

def _load_recommendation_sample(*, database_path: Path, trade_date: str, limit: int = 20) -> list[dict[str, Any]]:
    """保留旧接口兼容性。"""
    import duckdb
    from src.db.helpers import table_exists as _table_exists

    if not database_path.exists():
        return []
    with duckdb.connect(str(database_path), read_only=True) as connection:
        if not _table_exists(connection, "integrated_recommendation"):
            return []
        frame = connection.execute(
            "SELECT * FROM integrated_recommendation "
            "WHERE CAST(trade_date AS VARCHAR) = ? "
            "ORDER BY stock_code LIMIT ?",
            [trade_date, int(limit)],
        ).df()
    return frame.to_dict(orient="records")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()
    trade_date = str(args.trade_date or "").strip()
    database_path = Path(str(args.duckdb_path or "").strip())

    st.set_page_config(page_title="EmotionQuant S5 GUI", layout="wide")
    st.title("EmotionQuant S5 看板")
    st.caption("只读展示：不在页面层执行算法计算。色彩约定：A 股红涨绿跌。")

    if not trade_date:
        st.error("缺少 trade_date，请通过 `eq gui --date YYYYMMDD` 启动。")
        return
    if not str(database_path):
        st.error("缺少 DuckDB 路径。")
        return

    svc = DataService(database_path)

    tabs = st.tabs(PAGE_NAMES)

    with tabs[0]:  # Dashboard
        _render_dashboard(svc, trade_date)
    with tabs[1]:  # MSS
        _render_mss(svc, trade_date)
    with tabs[2]:  # IRS
        _render_irs(svc, trade_date)
    with tabs[3]:  # PAS
        _render_pas(svc, trade_date)
    with tabs[4]:  # Integrated
        _render_integrated(svc, trade_date)
    with tabs[5]:  # Trading
        _render_trading(svc, trade_date)
    with tabs[6]:  # Analysis
        _render_analysis(svc, trade_date)


if __name__ == "__main__":
    main()
