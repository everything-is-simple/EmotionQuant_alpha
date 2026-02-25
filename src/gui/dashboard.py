from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import duckdb
import plotly.graph_objects as go
import streamlit as st

from src.db.helpers import table_exists as _table_exists
from src.gui.app import _read_daily_metrics


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--trade-date", default=os.getenv("EQ_GUI_TRADE_DATE", "").strip())
    parser.add_argument("--duckdb-path", default=os.getenv("EQ_GUI_DUCKDB_PATH", "").strip())
    args, _ = parser.parse_known_args()
    return args




def _load_recommendation_sample(*, database_path: Path, trade_date: str, limit: int = 20) -> list[dict[str, Any]]:
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


def main() -> None:
    args = _parse_args()
    trade_date = str(args.trade_date or "").strip()
    database_path = Path(str(args.duckdb_path or "").strip())

    st.set_page_config(page_title="EmotionQuant S5 GUI", layout="wide")
    st.title("EmotionQuant S5 最小闭环看板")
    st.caption("只读展示：不在页面层执行算法计算。")

    if not trade_date:
        st.error("缺少 trade_date，请通过 `eq gui --date YYYYMMDD` 启动。")
        return
    if not str(database_path):
        st.error("缺少 DuckDB 路径。")
        return

    metrics, warnings = _read_daily_metrics(database_path=database_path, trade_date=trade_date)
    quality_status = "WARN" if warnings else "PASS"

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("当日推荐数", int(metrics["integrated_recommendation_count"]))
    col_b.metric("当日买入成交数", int(metrics["filled_buy_trade_count"]))
    col_c.metric("Validation Gate", str(metrics["validation_final_gate"]))

    figure = go.Figure(
        go.Indicator(
            mode="number+gauge",
            value=float(metrics["integrated_recommendation_count"]),
            title={"text": "推荐活跃度"},
            gauge={"axis": {"range": [0, max(10, int(metrics["integrated_recommendation_count"]) + 5)]}},
        )
    )
    st.plotly_chart(figure, use_container_width=True)

    st.subheader("状态")
    st.write(f"- trade_date: `{trade_date}`")
    st.write(f"- duckdb_path: `{database_path}`")
    st.write(f"- quality_status: `{quality_status}`")
    st.write(f"- warnings: `{warnings if warnings else 'none'}`")

    st.subheader("推荐样本（只读）")
    rows = _load_recommendation_sample(database_path=database_path, trade_date=trade_date, limit=20)
    if not rows:
        st.info("当日无推荐样本或数据表尚未就绪。")
    else:
        st.dataframe(rows, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
