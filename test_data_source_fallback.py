#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试三层数据源兜底方案

测试顺序：
1. TuShare (主数据源)
2. AKShare (第一兜底)
3. BaoStock (第二兜底)
"""

import sys
from datetime import datetime

# 测试日期
TEST_DATE = "20250109"
TEST_SYMBOL = "000001"  # 平安银行


def test_tushare():
    """测试 TuShare"""
    print("\n" + "=" * 60)
    print("Layer 1: TuShare (主数据源)")
    print("=" * 60)
    
    try:
        import tushare as ts
        TOKEN = "31e5536e4d0ffbfb47a74e9832fd35c711fdaa2405bec6559b62d22d"
        pro = ts.pro_api(TOKEN)
        
        # 测试 daily
        df = pro.daily(trade_date=TEST_DATE)
        print(f"[OK] daily: {len(df)} rows")
        
        return True, "TuShare"
    except Exception as e:
        print(f"[FAIL] TuShare: {str(e)[:100]}")
        return False, None


def test_akshare():
    """测试 AKShare"""
    print("\n" + "=" * 60)
    print("Layer 2: AKShare (第一兜底)")
    print("=" * 60)
    
    try:
        import akshare as ak
        
        # 1. 股票日线
        df = ak.stock_zh_a_hist(symbol=TEST_SYMBOL, start_date=TEST_DATE, end_date=TEST_DATE)
        print(f"[OK] stock_zh_a_hist: {len(df)} rows")
        
        # 2. 指数日线
        df = ak.index_zh_a_hist(symbol="000001", start_date=TEST_DATE, end_date=TEST_DATE)
        print(f"[OK] index_zh_a_hist: {len(df)} rows")
        
        # 3. 行业成分
        df = ak.stock_board_industry_name_em()
        print(f"[OK] stock_board_industry_name_em: {len(df)} rows")
        
        # 4. 股票信息
        df = ak.stock_info_a_code_name()
        print(f"[OK] stock_info_a_code_name: {len(df)} rows")
        
        # 5. 交易日历
        df = ak.tool_trade_date_hist_sina()
        print(f"[OK] tool_trade_date_hist_sina: {len(df)} rows")
        
        return True, "AKShare"
    except Exception as e:
        print(f"[FAIL] AKShare: {str(e)[:100]}")
        return False, None


def test_baostock():
    """测试 BaoStock"""
    print("\n" + "=" * 60)
    print("Layer 3: BaoStock (第二兜底)")
    print("=" * 60)
    
    try:
        import baostock as bs
        
        # 登录
        lg = bs.login()
        if lg.error_code != '0':
            print(f"[FAIL] BaoStock login: {lg.error_msg}")
            return False, None
        
        print("[OK] BaoStock login successful")
        
        # 1. 股票日线
        rs = bs.query_history_k_data_plus(
            f"sz.{TEST_SYMBOL}",
            "date,code,open,high,low,close,volume,amount",
            start_date=TEST_DATE,
            end_date=TEST_DATE,
            frequency="d"
        )
        
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        print(f"[OK] query_history_k_data_plus: {len(data_list)} rows")
        
        # 2. 交易日历
        rs = bs.query_trade_dates(start_date="2025-01-01", end_date="2025-01-31")
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        print(f"[OK] query_trade_dates: {len(data_list)} rows")
        
        # 3. 股票基本信息
        rs = bs.query_stock_basic()
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        print(f"[OK] query_stock_basic: {len(data_list)} rows")
        
        # 登出
        bs.logout()
        
        return True, "BaoStock"
    except Exception as e:
        print(f"[FAIL] BaoStock: {str(e)[:100]}")
        return False, None


def main():
    """主测试流程"""
    print("=" * 60)
    print("数据源兜底方案测试")
    print(f"测试日期: {TEST_DATE}")
    print(f"测试股票: {TEST_SYMBOL}")
    print("=" * 60)
    
    # 测试三层数据源
    results = []
    
    # Layer 1: TuShare
    success, source = test_tushare()
    results.append(("TuShare", success, source))
    
    # Layer 2: AKShare
    success, source = test_akshare()
    results.append(("AKShare", success, source))
    
    # Layer 3: BaoStock
    success, source = test_baostock()
    results.append(("BaoStock", success, source))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    available_sources = []
    for name, success, _ in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {name}")
        if success:
            available_sources.append(name)
    
    print("\n" + "=" * 60)
    print("可用数据源")
    print("=" * 60)
    
    if available_sources:
        print(f"可用: {', '.join(available_sources)}")
        print(f"\n推荐使用: {available_sources[0]}")
        return 0
    else:
        print("所有数据源均不可用")
        return 1


if __name__ == "__main__":
    sys.exit(main())
