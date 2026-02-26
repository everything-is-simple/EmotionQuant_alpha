#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高性能历史数据批量下载脚本。

解决现有 l1_pipeline / fetch_batch_pipeline 的性能瓶颈：
- 单一持久 DuckDB 连接（避免连接风暴）
- 双 Token 交替调用（有效吞吐翻倍）
- 按 API 维度批量拉取（非逐日逐表）
- 跳过 Quality Gate（批量补采阶段不执行质量检查）
- 断点续传（检查已存在的 trade_date 自动跳过）

用法：
    python scripts/data/bulk_download.py --start 20250101 --end 20260224
    python scripts/data/bulk_download.py --start 20250101 --end 20260224 --skip-existing
    python scripts/data/bulk_download.py --start 20250101 --end 20260224 --tables raw_daily,raw_daily_basic
    python scripts/data/bulk_download.py --help
    python scripts/data/bulk_download.py --dry-run --start 20250101 --end 20260224
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# 兼容直接脚本运行：将仓库根目录加入 sys.path。
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import duckdb
import pandas as pd

from src.config.config import Config

# --------------------------------------------------------------------------- #
#  常量定义
# --------------------------------------------------------------------------- #

# 高频表：每个开市日都需要拉取
HIGH_FREQ_TABLES: dict[str, str] = {
    "raw_daily": "daily",
    "raw_daily_basic": "daily_basic",
    "raw_index_daily": "index_daily",
    "raw_limit_list": "limit_list",
}

# 低频表：整个范围只需拉取一次
LOW_FREQ_TABLES: dict[str, str] = {
    "raw_stock_basic": "stock_basic",
    "raw_index_member": "index_member",
    "raw_index_classify": "index_classify",
}

# 交易日历表
TRADE_CAL_TABLE = "raw_trade_cal"

# index_daily 需要逐指数查询的主要指数列表
MAJOR_INDEX_CODES = [
    "000001.SH",  # 上证指数
    "399001.SZ",  # 深证成指
    "399006.SZ",  # 创业板指
    "000688.SH",  # 科创50
    "000300.SH",  # 沪深300
    "000905.SH",  # 中证500
    "000852.SH",  # 中证1000
]

ALL_TABLE_NAMES = (
    [TRADE_CAL_TABLE]
    + list(HIGH_FREQ_TABLES.keys())
    + list(LOW_FREQ_TABLES.keys())
)


# --------------------------------------------------------------------------- #
#  TuShare 客户端管理
# --------------------------------------------------------------------------- #


@dataclass
class ChannelStats:
    """单通道统计信息。"""
    name: str
    calls: int = 0
    errors: int = 0
    last_call_at: float = 0.0
    min_interval: float = 0.0  # 秒


class DualTokenClient:
    """双 Token 交替调用客户端。

    创建 primary + fallback 两个 TuShare pro_api 实例，
    交替分发 API 调用以充分利用两个 Token 的配额。
    单通道失败时自动切换到另一通道重试。
    """

    def __init__(self, config: Config) -> None:
        self._channels: list[tuple[str, Any]] = []  # (name, pro_api)
        self._stats: dict[str, ChannelStats] = {}
        self._current_index = 0

        # 构建主通道
        primary_token = str(
            config.tushare_primary_token or config.tushare_token
        ).strip()
        primary_provider = str(
            config.tushare_primary_sdk_provider
            or config.tushare_sdk_provider
            or "tushare"
        ).strip()
        primary_http_url = str(
            config.tushare_primary_http_url or config.tushare_http_url
        ).strip()

        if primary_token:
            pro = self._make_pro(primary_token, primary_provider, primary_http_url)
            self._channels.append(("primary", pro))
            rate = max(0, config.tushare_primary_rate_limit_per_min) or max(
                0, config.tushare_rate_limit_per_min
            )
            self._stats["primary"] = ChannelStats(
                name="primary",
                min_interval=60.0 / rate if rate > 0 else 0.2,
            )

        # 构建兜底通道
        fallback_token = str(config.tushare_fallback_token).strip()
        fallback_provider = str(
            config.tushare_fallback_sdk_provider or "tushare"
        ).strip()
        fallback_http_url = str(config.tushare_fallback_http_url).strip()

        if fallback_token and (
            fallback_token != primary_token
            or fallback_provider != primary_provider
        ):
            pro = self._make_pro(fallback_token, fallback_provider, fallback_http_url)
            self._channels.append(("fallback", pro))
            rate = max(0, config.tushare_fallback_rate_limit_per_min) or max(
                0, config.tushare_rate_limit_per_min
            )
            self._stats["fallback"] = ChannelStats(
                name="fallback",
                min_interval=60.0 / rate if rate > 0 else 0.2,
            )

        if not self._channels:
            raise RuntimeError(
                "未找到任何 TuShare Token。请检查 .env 中的 "
                "TUSHARE_PRIMARY_TOKEN / TUSHARE_FALLBACK_TOKEN 配置。"
            )

    @staticmethod
    def _make_pro(token: str, provider: str, http_url: str) -> Any:
        """创建 TuShare pro_api 实例。"""
        module_name = "tinyshare" if provider.lower() == "tinyshare" else "tushare"
        ts = importlib.import_module(module_name)
        pro = ts.pro_api(token)
        # 注入 Token 和网关地址（兼容第三方网关）
        if hasattr(pro, "_DataApi__token"):
            setattr(pro, "_DataApi__token", token)
        if http_url and hasattr(pro, "_DataApi__http_url"):
            setattr(pro, "_DataApi__http_url", http_url)
        return pro

    def _respect_rate_limit(self, channel_name: str) -> None:
        """按通道独立限流。"""
        stats = self._stats.get(channel_name)
        if not stats or stats.min_interval <= 0:
            return
        elapsed = time.monotonic() - stats.last_call_at
        if elapsed < stats.min_interval:
            time.sleep(stats.min_interval - elapsed)

    def call(self, api_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """调用 TuShare API，自动交替通道和限流。

        先尝试当前通道，失败后切换到另一通道重试。
        """
        # API 名称到 TuShare 方法名的映射
        method_map = {
            "daily": "daily",
            "daily_basic": "daily_basic",
            "trade_cal": "trade_cal",
            "limit_list": "limit_list_d",
            "index_daily": "index_daily",
            "index_member": "index_member",
            "index_classify": "index_classify",
            "stock_basic": "stock_basic",
        }
        method_name = method_map.get(api_name)
        if not method_name:
            raise ValueError(f"不支持的 API: {api_name}")

        last_error: Exception | None = None

        # 尝试所有通道（从当前通道开始）
        for offset in range(len(self._channels)):
            idx = (self._current_index + offset) % len(self._channels)
            channel_name, pro = self._channels[idx]

            self._respect_rate_limit(channel_name)
            stats = self._stats[channel_name]

            try:
                method = getattr(pro, method_name, None)
                # limit_list 的方法名在不同 SDK 版本可能不同
                if method is None and api_name == "limit_list":
                    method = getattr(pro, "limit_list", None)
                if method is None:
                    raise RuntimeError(f"TuShare API 方法不可用: {method_name}")

                payload = method(**params)
                stats.last_call_at = time.monotonic()
                stats.calls += 1

                # 成功后推进到下一个通道（交替使用）
                self._current_index = (idx + 1) % len(self._channels)
                return self._to_records(payload)

            except Exception as exc:
                stats.last_call_at = time.monotonic()
                stats.errors += 1
                last_error = exc
                continue

        raise RuntimeError(
            f"所有通道调用失败 [{api_name}]: {last_error}"
        ) from last_error

    @staticmethod
    def _to_records(payload: Any) -> list[dict[str, Any]]:
        """将 TuShare 返回值转为 list[dict]。"""
        if payload is None:
            return []
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if hasattr(payload, "to_dict"):
            return payload.to_dict(orient="records")
        return []

    def print_stats(self) -> None:
        """打印各通道统计信息。"""
        for name, stats in self._stats.items():
            print(
                f"  [{name}] 调用: {stats.calls}, 错误: {stats.errors}, "
                f"限速间隔: {stats.min_interval:.3f}s"
            )


# --------------------------------------------------------------------------- #
#  字段规范化
# --------------------------------------------------------------------------- #

def normalize_rows(
    api_name: str,
    rows: list[dict[str, Any]],
    *,
    trade_date: str = "",
) -> list[dict[str, Any]]:
    """规范化 TuShare 返回的原始数据。

    - 补全 stock_code（从 ts_code 提取前 6 位）
    - 补全 trade_date（从请求参数回填）
    - trade_cal 的 cal_date → trade_date
    """
    normalized: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        # trade_cal: cal_date → trade_date
        if api_name == "trade_cal" and not item.get("trade_date"):
            cal_date = str(item.get("cal_date", "")).strip()
            if cal_date:
                item["trade_date"] = cal_date

        # 补全 trade_date
        if (
            api_name in {"daily", "daily_basic", "index_daily", "limit_list"}
            and not str(item.get("trade_date", "")).strip()
            and trade_date
        ):
            item["trade_date"] = trade_date

        # 补全 stock_code
        ts_code = str(item.get("ts_code", ""))
        if (
            api_name in {"daily", "daily_basic", "limit_list", "stock_basic"}
            and not item.get("stock_code")
            and len(ts_code) >= 6
        ):
            item["stock_code"] = ts_code[:6]

        # index_member: con_code → ts_code / stock_code
        if api_name == "index_member":
            con_code = str(item.get("con_code", "")).strip()
            if not ts_code and con_code:
                item["ts_code"] = con_code
                ts_code = con_code
            if not item.get("stock_code") and len(ts_code) >= 6:
                item["stock_code"] = ts_code[:6]

        normalized.append(item)
    return normalized


# --------------------------------------------------------------------------- #
#  DuckDB 持久连接管理
# --------------------------------------------------------------------------- #

class PersistentDuckDBWriter:
    """持久化 DuckDB 写入器。

    全程保持单一连接，避免频繁 open/close 导致的锁竞争。
    支持按 trade_date 分区去重写入。
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(str(db_path))
        self._known_tables: set[str] = set()
        self._total_written = 0

    def close(self) -> None:
        """关闭连接。"""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def write_batch(
        self,
        table_name: str,
        records: list[dict[str, Any]],
    ) -> int:
        """批量写入一批记录到指定表。

        自动建表、同步 schema、按 trade_date 分区去重。
        返回写入行数。
        """
        if not records:
            return 0

        df = pd.DataFrame.from_records(records)
        conn = self._conn

        conn.register("incoming_df", df)
        try:
            # 用事务包裹删分区 + 插入，避免中途失败导致数据不一致。
            conn.execute("BEGIN TRANSACTION")
            try:
                # 建表（首次）
                if table_name not in self._known_tables:
                    conn.execute(
                        f"CREATE TABLE IF NOT EXISTS {table_name} "
                        "AS SELECT * FROM incoming_df WHERE 1=0"
                    )
                    self._known_tables.add(table_name)

                # 同步 schema：自动添加缺失列
                self._sync_schema(table_name)

                # 按 trade_date 分区去重
                self._replace_partition(table_name)

                # 插入数据
                conn.execute(
                    f"INSERT INTO {table_name} BY NAME SELECT * FROM incoming_df"
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        finally:
            conn.unregister("incoming_df")

        count = len(df)
        self._total_written += count
        return count

    def _sync_schema(self, table_name: str) -> None:
        """自动补齐表缺少的列。"""
        existing = self._conn.execute(
            "SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = '{table_name}'"
        ).fetchall()
        existing_cols = {str(r[0]) for r in existing}

        incoming = self._conn.execute("DESCRIBE incoming_df").fetchall()
        for col_name, col_type, *_ in incoming:
            name = str(col_name)
            if name not in existing_cols:
                escaped = name.replace('"', '""')
                self._conn.execute(
                    f'ALTER TABLE {table_name} ADD COLUMN "{escaped}" {col_type}'
                )
                existing_cols.add(name)

    def _replace_partition(self, table_name: str) -> None:
        """删除 incoming 中已有 trade_date 对应的旧数据（幂等写入）。"""
        # 检查表和 incoming 是否都有 trade_date 列
        has_td = self._conn.execute(
            "SELECT COUNT(*) FROM information_schema.columns "
            f"WHERE table_name = '{table_name}' AND column_name = 'trade_date'"
        ).fetchone()
        if not has_td or int(has_td[0]) == 0:
            return

        incoming_cols = {
            str(r[0])
            for r in self._conn.execute("DESCRIBE incoming_df").fetchall()
        }
        if "trade_date" not in incoming_cols:
            return

        self._conn.execute(
            f"DELETE FROM {table_name} "
            "WHERE CAST(trade_date AS VARCHAR) IN ("
            "SELECT DISTINCT CAST(trade_date AS VARCHAR) FROM incoming_df "
            "WHERE trade_date IS NOT NULL)"
        )

    def get_existing_trade_dates(self, table_name: str) -> set[str]:
        """查询指定表已存在的 trade_date 集合（用于断点续传）。"""
        try:
            rows = self._conn.execute(
                f"SELECT DISTINCT CAST(trade_date AS VARCHAR) FROM {table_name}"
            ).fetchall()
            return {str(r[0]) for r in rows}
        except Exception:
            return set()

    @property
    def total_written(self) -> int:
        return self._total_written


# --------------------------------------------------------------------------- #
#  Parquet 写入
# --------------------------------------------------------------------------- #

def write_parquet(
    parquet_root: Path,
    table_name: str,
    records: list[dict[str, Any]],
) -> None:
    """写入 Parquet 文件（追加模式，按表名分文件）。"""
    if not records:
        return
    output_path = parquet_root / f"{table_name}.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame.from_records(records)
    # 追加模式：如果文件已存在则合并
    if output_path.exists():
        try:
            existing = pd.read_parquet(output_path)
            df = pd.concat([existing, df], ignore_index=True)
            # 按 trade_date 去重（保留新数据）
            if "trade_date" in df.columns:
                df = df.drop_duplicates(
                    subset=["trade_date"] + (["stock_code"] if "stock_code" in df.columns else []),
                    keep="last",
                )
        except Exception as exc:
            # 已有文件损坏（如之前下载中断），删掉重写
            print(f"    [警告] Parquet 文件损坏，将重建: {output_path.name} ({exc})")
            output_path.unlink(missing_ok=True)
    df.to_parquet(output_path, index=False)


def resolve_l1_parquet_root(parquet_path: Path) -> Path:
    """解析 L1 Parquet 根目录，兼容两种配置口径。

    - 若 PARQUET_PATH 已指向 .../l1，则直接使用
    - 若 PARQUET_PATH 指向 .../parquet，则自动拼接 /l1
    """
    if parquet_path.name.lower() == "l1":
        return parquet_path
    return parquet_path / "l1"


# --------------------------------------------------------------------------- #
#  进度管理
# --------------------------------------------------------------------------- #

@dataclass
class DownloadProgress:
    """下载进度追踪。"""
    start_date: str = ""
    end_date: str = ""
    total_open_days: int = 0
    completed_days: int = 0
    skipped_days: int = 0
    failed_days: int = 0
    total_rows: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    elapsed_seconds: float = 0.0

    def save(self, path: Path) -> None:
        """保存进度到 JSON 文件。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                    "total_open_days": self.total_open_days,
                    "completed_days": self.completed_days,
                    "skipped_days": self.skipped_days,
                    "failed_days": self.failed_days,
                    "total_rows": self.total_rows,
                    "errors": self.errors[-50:],  # 只保留最近 50 条
                    "started_at": self.started_at,
                    "elapsed_seconds": round(self.elapsed_seconds, 2),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


# --------------------------------------------------------------------------- #
#  核心下载逻辑
# --------------------------------------------------------------------------- #

def fetch_trade_calendar(
    client: DualTokenClient,
    start_date: str,
    end_date: str,
) -> list[str]:
    """拉取交易日历，返回开市日列表（已排序）。"""
    print(f"[1/4] 拉取交易日历 {start_date} ~ {end_date} ...")
    rows = client.call("trade_cal", {
        "start_date": start_date,
        "end_date": end_date,
        "exchange": "SSE",
    })
    normalized = normalize_rows("trade_cal", rows)

    # 筛选开市日
    open_days = sorted(
        str(r["trade_date"])
        for r in normalized
        if int(r.get("is_open", 0)) == 1
    )
    print(f"  日历范围: {len(normalized)} 天, 开市日: {len(open_days)} 天")
    return open_days


def fetch_low_frequency_tables(
    client: DualTokenClient,
    writer: PersistentDuckDBWriter,
    parquet_root: Path,
    tables_filter: set[str] | None,
) -> int:
    """拉取低频数据集（stock_basic / index_member / index_classify）。"""
    print("[2/4] 拉取低频数据集 ...")
    total = 0

    for table_name, api_name in LOW_FREQ_TABLES.items():
        if tables_filter and table_name not in tables_filter:
            continue

        try:
            if api_name == "stock_basic":
                rows = client.call("stock_basic", {"list_status": "L"})
            elif api_name == "index_classify":
                rows = client.call("index_classify", {"src": "SW2021"})
            elif api_name == "index_member":
                rows = client.call("index_member", {
                    "start_date": "20100101",
                    "end_date": datetime.now().strftime("%Y%m%d"),
                })
            else:
                continue

            normalized = normalize_rows(api_name, rows)
            count = writer.write_batch(table_name, normalized)
            write_parquet(parquet_root, table_name, normalized)
            print(f"  {table_name}: {count} 行")
            total += count
        except Exception as exc:
            print(f"  [警告] {table_name} 拉取失败: {exc}")

    return total


def fetch_high_frequency_day(
    client: DualTokenClient,
    trade_date: str,
    tables_filter: set[str] | None,
) -> dict[str, list[dict[str, Any]]]:
    """拉取单个交易日的高频数据。

    返回 {table_name: normalized_rows} 映射。
    """
    result: dict[str, list[dict[str, Any]]] = {}

    for table_name, api_name in HIGH_FREQ_TABLES.items():
        if tables_filter and table_name not in tables_filter:
            continue

        try:
            if api_name == "index_daily":
                # index_daily 需要逐指数查询
                all_rows: list[dict[str, Any]] = []
                for ts_code in MAJOR_INDEX_CODES:
                    rows = client.call("index_daily", {
                        "ts_code": ts_code,
                        "trade_date": trade_date,
                    })
                    all_rows.extend(rows)
                normalized = normalize_rows(api_name, all_rows, trade_date=trade_date)
            else:
                rows = client.call(api_name, {"trade_date": trade_date})
                normalized = normalize_rows(api_name, rows, trade_date=trade_date)

            result[table_name] = normalized
        except Exception as exc:
            print(f"    [警告] {table_name} @ {trade_date}: {exc}")
            result[table_name] = []

    return result


def run_bulk_download(
    config: Config,
    start_date: str,
    end_date: str,
    *,
    skip_existing: bool = False,
    tables_filter: set[str] | None = None,
    dry_run: bool = False,
    batch_size: int = 10,
) -> DownloadProgress:
    """执行批量下载主流程。"""
    progress = DownloadProgress(
        start_date=start_date,
        end_date=end_date,
        started_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    t0 = time.monotonic()

    # 初始化客户端
    print("=" * 60)
    print("EmotionQuant 高性能数据批量下载")
    print("=" * 60)
    client = DualTokenClient(config)
    print(f"通道数: {len(client._channels)}")
    client.print_stats()

    # 初始化 DuckDB 写入器
    db_path = Path(config.duckdb_dir) / "emotionquant.duckdb"
    parquet_root = resolve_l1_parquet_root(Path(config.parquet_path))
    print(f"DuckDB: {db_path}")
    print(f"Parquet: {parquet_root}")
    print(f"日期范围: {start_date} ~ {end_date}")
    if tables_filter:
        print(f"指定表: {', '.join(sorted(tables_filter))}")
    if skip_existing:
        print("模式: 断点续传（跳过已存在的交易日）")
    if dry_run:
        print("模式: 试运行（不实际写入）")
    print("-" * 60)

    # 1. 拉取交易日历
    open_days = fetch_trade_calendar(client, start_date, end_date)
    progress.total_open_days = len(open_days)

    if dry_run:
        print(f"\n[试运行] 将下载 {len(open_days)} 个开市日的数据")
        print(f"[试运行] 预计 API 调用: ~{len(open_days) * 10} 次")
        print(f"[试运行] 预计耗时: ~{len(open_days) * 1.0:.0f} 秒")
        progress.elapsed_seconds = time.monotonic() - t0
        return progress

    writer = PersistentDuckDBWriter(db_path)
    progress_path = Path("artifacts") / "bulk_download_progress.json"

    try:
        # 写入交易日历
        if not tables_filter or TRADE_CAL_TABLE in tables_filter:
            print("  写入交易日历 ...")
            cal_rows = client.call("trade_cal", {
                "start_date": start_date,
                "end_date": end_date,
                "exchange": "SSE",
            })
            cal_normalized = normalize_rows("trade_cal", cal_rows)
            count = writer.write_batch(TRADE_CAL_TABLE, cal_normalized)
            write_parquet(parquet_root, TRADE_CAL_TABLE, cal_normalized)
            print(f"  {TRADE_CAL_TABLE}: {count} 行")
            progress.total_rows += count

        # 2. 拉取低频数据
        lf_count = fetch_low_frequency_tables(
            client, writer, parquet_root, tables_filter
        )
        progress.total_rows += lf_count

        # 3. 确定需要下载的交易日
        if skip_existing and not tables_filter:
            # 找所有高频表中都已存在的 trade_date
            existing_sets = []
            for table_name in HIGH_FREQ_TABLES:
                existing_sets.append(writer.get_existing_trade_dates(table_name))
            if existing_sets:
                already_done = set.intersection(*existing_sets) if existing_sets else set()
            else:
                already_done = set()
        elif skip_existing and tables_filter:
            # 只检查指定表
            hf_tables = [t for t in tables_filter if t in HIGH_FREQ_TABLES]
            existing_sets = [writer.get_existing_trade_dates(t) for t in hf_tables]
            already_done = set.intersection(*existing_sets) if existing_sets else set()
        else:
            already_done = set()

        days_to_fetch = [d for d in open_days if d not in already_done]
        progress.skipped_days = len(open_days) - len(days_to_fetch)

        if progress.skipped_days > 0:
            print(f"  跳过已存在: {progress.skipped_days} 天")

        print(f"\n[3/4] 拉取高频数据: {len(days_to_fetch)} 个交易日 ...")

        # 4. 逐日拉取高频数据（累积后批量写入）
        batch_buffer: dict[str, list[dict[str, Any]]] = {}
        batch_count = 0

        for idx, trade_date in enumerate(days_to_fetch, 1):
            try:
                day_data = fetch_high_frequency_day(
                    client, trade_date, tables_filter
                )

                # 累积到 buffer
                for table_name, rows in day_data.items():
                    if table_name not in batch_buffer:
                        batch_buffer[table_name] = []
                    batch_buffer[table_name].extend(rows)

                batch_count += 1
                progress.completed_days += 1

                # 每 batch_size 天刷写一次
                if batch_count >= batch_size or idx == len(days_to_fetch):
                    for table_name, buffered_rows in batch_buffer.items():
                        if buffered_rows:
                            count = writer.write_batch(table_name, buffered_rows)
                            progress.total_rows += count
                            try:
                                write_parquet(parquet_root, table_name, buffered_rows)
                            except Exception as pq_exc:
                                print(f"    [警告] Parquet 写入失败({table_name}): {pq_exc}")
                    batch_buffer.clear()
                    batch_count = 0

                    # 打印进度
                    elapsed = time.monotonic() - t0
                    speed = progress.completed_days / elapsed if elapsed > 0 else 0
                    eta = (len(days_to_fetch) - idx) / speed if speed > 0 else 0
                    print(
                        f"  [{idx}/{len(days_to_fetch)}] {trade_date} "
                        f"| 速度: {speed:.1f} 天/秒 "
                        f"| 剩余: {eta:.0f}s "
                        f"| 总行数: {writer.total_written}"
                    )

                    # 保存进度
                    progress.elapsed_seconds = elapsed
                    progress.save(progress_path)

            except Exception as exc:
                progress.failed_days += 1
                error_msg = f"{trade_date}: {exc}"
                progress.errors.append(error_msg)
                print(f"  [错误] {error_msg}")

        # 刷写剩余 buffer
        for table_name, buffered_rows in batch_buffer.items():
            if buffered_rows:
                count = writer.write_batch(table_name, buffered_rows)
                progress.total_rows += count
                try:
                    write_parquet(parquet_root, table_name, buffered_rows)
                except Exception as pq_exc:
                    print(f"    [警告] Parquet 写入失败({table_name}): {pq_exc}")

    finally:
        writer.close()

    # 4. 汇总
    progress.elapsed_seconds = time.monotonic() - t0
    progress.save(progress_path)

    print("\n" + "=" * 60)
    print("[4/4] 下载完成")
    print(f"  总开市日: {progress.total_open_days}")
    print(f"  已完成: {progress.completed_days}")
    print(f"  已跳过: {progress.skipped_days}")
    print(f"  失败: {progress.failed_days}")
    print(f"  总行数: {progress.total_rows}")
    print(f"  耗时: {progress.elapsed_seconds:.1f}s")
    if progress.completed_days > 0:
        avg = progress.elapsed_seconds / progress.completed_days
        print(f"  平均: {avg:.2f}s/天")
    print("  通道统计:")
    client.print_stats()
    print(f"  进度文件: {progress_path}")
    print("=" * 60)

    return progress


# --------------------------------------------------------------------------- #
#  CLI 入口
# --------------------------------------------------------------------------- #

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="EmotionQuant 高性能历史数据批量下载",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 下载 2025 全年数据
  python scripts/data/bulk_download.py --start 20250101 --end 20251231

  # 断点续传（跳过已下载的交易日）
  python scripts/data/bulk_download.py --start 20250101 --end 20251231 --skip-existing

  # 只下载日线和日线基本面
  python scripts/data/bulk_download.py --start 20250101 --end 20251231 --tables raw_daily,raw_daily_basic

  # 试运行（不实际下载）
  python scripts/data/bulk_download.py --start 20250101 --end 20251231 --dry-run
""",
    )
    parser.add_argument(
        "--start",
        required=True,
        help="起始日期 (YYYYMMDD)",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="结束日期 (YYYYMMDD)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=False,
        help="跳过已存在的交易日（断点续传）",
    )
    parser.add_argument(
        "--tables",
        default="",
        help=f"指定表名（逗号分隔），可选: {', '.join(ALL_TABLE_NAMES)}",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="每多少个交易日刷写一次 DuckDB（默认 10）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="试运行：只查询交易日历，不实际下载数据",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help=".env 文件路径（默认 .env）",
    )
    return parser


def main() -> int:
    # 确保 stdout 使用 UTF-8
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = _build_parser()
    args = parser.parse_args()

    # 验证日期格式
    for label, value in [("start", args.start), ("end", args.end)]:
        if len(value) != 8 or not value.isdigit():
            print(f"[错误] --{label} 格式错误: {value}（应为 YYYYMMDD）")
            return 1

    if args.start > args.end:
        print(f"[错误] --start ({args.start}) 不能大于 --end ({args.end})")
        return 1

    # 解析表过滤
    tables_filter: set[str] | None = None
    if args.tables:
        tables_filter = {t.strip() for t in args.tables.split(",") if t.strip()}
        unknown = tables_filter - set(ALL_TABLE_NAMES)
        if unknown:
            print(f"[错误] 未知表名: {', '.join(sorted(unknown))}")
            print(f"可选: {', '.join(ALL_TABLE_NAMES)}")
            return 1

    # 加载配置
    config = Config.from_env(env_file=args.env_file)

    # 执行下载
    try:
        progress = run_bulk_download(
            config,
            args.start,
            args.end,
            skip_existing=args.skip_existing,
            tables_filter=tables_filter,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )
    except Exception as exc:
        print(f"\n[致命错误] {exc}")
        return 1

    return 1 if progress.failed_days > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
