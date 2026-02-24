# Data layer module
"""数据访问层：仓储（Repository）模式实现 + 数据模型。

本模块是系统八层架构中 Data Layer 的核心实现，负责：
- L1 原始数据采集与落盘（TuShare → DuckDB / Parquet）
- L2 特征快照生成（市场快照 / 行业快照）
- 数据质量门禁（Quality Gate）评估与持久化
- 批量历史数据下载与断点续传
"""
