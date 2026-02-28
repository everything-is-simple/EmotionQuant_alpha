from __future__ import annotations

import pandas as pd

from src.data.l2_pipeline import _build_industry_snapshot_sw31, _build_market_snapshot


def test_market_snapshot_uses_pct_chg_and_counts_touched_limit_up_with_z() -> None:
    daily = pd.DataFrame.from_records(
        [
            {"stock_code": "000001", "open": 10.0, "close": 10.3, "pct_chg": 3.0, "amount": 100.0},
            {"stock_code": "000002", "open": 10.5, "close": 10.3, "pct_chg": 3.0, "amount": 200.0},
            {"stock_code": "000003", "open": 10.0, "close": 9.4, "pct_chg": -6.0, "amount": 150.0},
        ]
    )
    limit_list = pd.DataFrame.from_records(
        [
            {"stock_code": "000001", "limit_type": "U"},
            {"stock_code": "000002", "limit_type": "Z"},
            {"stock_code": "000003", "limit_type": "D"},
        ]
    )

    snapshot = _build_market_snapshot(
        trade_date="20260213",
        daily=daily,
        limit_list=limit_list,
        flat_threshold_ratio=0.01,
        recent_market_amounts=[],
    )

    assert snapshot.rise_count == 2
    assert snapshot.fall_count == 1
    assert snapshot.strong_up_count == 0
    assert snapshot.strong_down_count == 1
    assert snapshot.touched_limit_up == 2
    assert snapshot.amount_volatility == 0.0
    assert snapshot.data_quality == "cold_start"


def test_industry_snapshot_sw31_falls_back_to_previous_valuation_when_sample_small() -> None:
    daily = pd.DataFrame.from_records(
        [
            {"stock_code": "000001", "open": 11.0, "close": 10.8, "pct_chg": 8.0, "amount": 1000.0, "vol": 100.0},
            {"stock_code": "000002", "open": 9.8, "close": 9.6, "pct_chg": -4.0, "amount": 800.0, "vol": 80.0},
        ]
    )
    limit_list = pd.DataFrame.from_records(
        [
            {"stock_code": "000001", "limit_type": "U"},
        ]
    )
    daily_basic = pd.DataFrame.from_records(
        [
            {"stock_code": "000001", "pe_ttm": 0.0, "pb": 0.0},
            {"stock_code": "000002", "pe_ttm": -5.0, "pb": -0.5},
        ]
    )
    sw31_classify = pd.DataFrame.from_records(
        [{"index_code": "801001", "industry_code": "801001", "industry_name": "行业A"}]
    )
    sw31_member = pd.DataFrame.from_records(
        [
            {"index_code": "801001", "stock_code": "000001", "in_date": "20100101", "out_date": ""},
            {"index_code": "801001", "stock_code": "000002", "in_date": "20100101", "out_date": ""},
        ]
    )

    snapshots, audit = _build_industry_snapshot_sw31(
        trade_date="20260213",
        daily=daily,
        limit_list=limit_list,
        daily_basic=daily_basic,
        sw31_classify=sw31_classify,
        sw31_member=sw31_member,
        classify_snapshot_trade_date="20260213",
        member_snapshot_trade_date="20260213",
        flat_threshold_ratio=0.01,
        previous_valuation_by_industry={"801001": (15.0, 1.8)},
    )

    assert audit["uses_sw31"] is True
    assert len(snapshots) == 1
    row = snapshots[0]
    assert row.industry_code == "801001"
    assert row.rise_count == 1
    assert row.fall_count == 1
    assert row.industry_pct_chg == 2.0
    assert row.industry_pe_ttm == 15.0
    assert row.industry_pb == 1.8
    assert row.top5_pct_chg[0] == 8.0
