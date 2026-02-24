# Data repositories
"""数据仓储层（Repository）：封装 DuckDB / Parquet 读写操作。

每个 Repository 对应一张 L1 原始表（raw_*），提供：
- fetch(): 通过 TuShareFetcher 从远端拉取数据
- save_to_database(): 写入 DuckDB（按 trade_date 分区去重）
- save_to_parquet(): 写入 Parquet 文件
"""
