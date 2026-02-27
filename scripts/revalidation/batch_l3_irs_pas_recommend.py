"""
批量生成 IRS + PAS + recommend（2020-2024 窗口）

用途：
- 为已有 L2+MSS 数据的交易日批量生成 IRS、PAS、integrated_recommendation
- 串行执行（DuckDB 单写者限制）
- 支持断点续传

执行：
    python scripts/revalidation/batch_l3_irs_pas_recommend.py
"""

import sys
from pathlib import Path

# 添加 src 到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

import duckdb
from datetime import datetime

# 导入 config
from src.utils.config import Config

def get_missing_dates(db_path: str) -> list[str]:
    """获取已有 MSS 但缺失 integrated_recommendation 的日期"""
    conn = duckdb.connect(str(db_path), read_only=True)
    
    query = """
    SELECT DISTINCT m.trade_date
    FROM mss_panorama m
    WHERE m.trade_date >= '20200101' AND m.trade_date <= '20241231'
      AND NOT EXISTS (
          SELECT 1 FROM integrated_recommendation ir
          WHERE ir.trade_date = m.trade_date
      )
    ORDER BY m.trade_date
    """
    
    result = conn.execute(query).fetchall()
    conn.close()
    
    return [row[0] for row in result]


def run_irs_pas_recommend(trade_date: str) -> dict:
    """为单个交易日执行 IRS -> PAS -> recommend"""
    import subprocess
    
    results = {
        "trade_date": trade_date,
        "irs_success": False,
        "pas_success": False,
        "recommend_success": False,
        "error": None
    }
    
    try:
        # 1. IRS
        print(f"  [{trade_date}] Running IRS...")
        result = subprocess.run(
            ["python", "-m", "src.pipeline.main", "irs", "--date", trade_date, "--require-sw31"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            results["error"] = f"IRS failed: {result.stderr[:200]}"
            return results
        
        results["irs_success"] = True
        
        # 2. PAS
        print(f"  [{trade_date}] Running PAS...")
        result = subprocess.run(
            ["python", "-m", "src.pipeline.main", "pas", "--date", trade_date],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            results["error"] = f"PAS failed: {result.stderr[:200]}"
            return results
        
        results["pas_success"] = True
        
        # 3. recommend (integrated mode with validation bridge)
        print(f"  [{trade_date}] Running recommend...")
        result = subprocess.run(
            ["python", "-m", "src.pipeline.main", "recommend", 
             "--date", trade_date, 
             "--mode", "mss_irs_pas",
             "--with-validation"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            results["error"] = f"recommend failed: {result.stderr[:200]}"
            return results
        
        results["recommend_success"] = True
        
    except subprocess.TimeoutExpired:
        results["error"] = "Timeout (>120s)"
    except Exception as e:
        results["error"] = str(e)
    
    return results


def main():
    config = Config.from_env()
    db_path = config.database_path
    
    print(f"Database: {db_path}")
    print(f"Checking missing dates (2020-2024)...")
    
    missing_dates = get_missing_dates(db_path)
    
    if not missing_dates:
        print("✅ All dates already have integrated_recommendation. Nothing to do.")
        return
    
    total = len(missing_dates)
    print(f"Found {total} dates missing L3 data.")
    print(f"Date range: {missing_dates[0]} ~ {missing_dates[-1]}")
    print(f"Starting batch generation (serial mode)...\n")
    
    start_time = datetime.now()
    success_count = 0
    failed_dates = []
    
    for i, trade_date in enumerate(missing_dates, 1):
        print(f"[{i}/{total}] Processing {trade_date}...")
        
        result = run_irs_pas_recommend(trade_date)
        
        if result["recommend_success"]:
            success_count += 1
            print(f"  ✅ {trade_date} completed")
        else:
            failed_dates.append((trade_date, result["error"]))
            print(f"  ❌ {trade_date} failed: {result['error']}")
        
        # 每 50 日输出进度
        if i % 50 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            avg_time = elapsed / i
            remaining = (total - i) * avg_time
            print(f"\n  Progress: {i}/{total} ({i/total*100:.1f}%)")
            print(f"  Elapsed: {elapsed/60:.1f}m, ETA: {remaining/60:.1f}m\n")
    
    # 最终汇总
    elapsed_total = (datetime.now() - start_time).total_seconds()
    
    print("\n" + "="*60)
    print("Batch L3 Generation Complete")
    print("="*60)
    print(f"Total dates: {total}")
    print(f"Success: {success_count}")
    print(f"Failed: {len(failed_dates)}")
    print(f"Total time: {elapsed_total/60:.1f} minutes")
    print(f"Avg time per date: {elapsed_total/total:.1f}s")
    
    if failed_dates:
        print("\nFailed dates:")
        for date, error in failed_dates[:10]:  # 只显示前 10 个
            print(f"  {date}: {error}")
        if len(failed_dates) > 10:
            print(f"  ... and {len(failed_dates)-10} more")


if __name__ == "__main__":
    main()
