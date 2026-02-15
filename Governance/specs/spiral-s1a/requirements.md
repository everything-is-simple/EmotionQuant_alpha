# S1a Requirements（6A A1/A2）

**Spiral**: S1a  
**状态**: completed  
**最后更新**: 2026-02-15

## 1. A1 Align

- 主目标: 完成 MSS 最小评分闭环，支持 `eq mss --date {trade_date}`。
- In Scope:
  - 实现 `eq mss --date {trade_date}` 可执行路径
  - 从 L2 `market_snapshot` 读取并计算 MSS 最小评分
  - 落库 `mss_panorama`，且字段包含 `mss_score/mss_temperature/mss_cycle`
  - 产出 `mss_panorama_sample.parquet` 与 `mss_factor_trace.md`
  - 补齐 `tests/unit/algorithms/mss/test_mss_contract.py` 与 `tests/unit/algorithms/mss/test_mss_engine.py`
- Out Scope:
  - MSS 回溯探针（`mss-probe`，S1b 范围）
  - IRS/PAS/Validation/Integration 计算
  - MSS 自适应分位阈值与完整历史基线文件

## 2. A2 Architect

- CP Slice: `CP-02`（1 个 Slice）
- 跨模块契约:
  - 输入: L2 表 `market_snapshot`
  - 输出: L3 表 `mss_panorama`
  - 必需字段: `mss_score`, `mss_temperature`, `mss_cycle`
  - 契约版本: `contract_version = "nc-v1"`（最小兼容写入）
- 失败策略:
  - `market_snapshot` 缺失或当日数据缺失判定 `P0`，阻断收口
  - 输出必需字段缺失判定 `P0`，阻断收口

## 3. 本圈最小证据定义

- run:
  - `python -m src.pipeline.main --env-file none run --date 20260215 --source tushare --l1-only`
  - `python -m src.pipeline.main --env-file none run --date 20260215 --source tushare --to-l2`
  - `python -m src.pipeline.main --env-file none mss --date 20260215`
- test:
  - `python -m pytest -q tests/unit/data/models/test_snapshots.py`
  - `python -m pytest -q tests/unit/algorithms/mss/test_mss_contract.py tests/unit/algorithms/mss/test_mss_engine.py`
- artifact:
  - `Governance/specs/spiral-s1a/mss_panorama_sample.parquet`
  - `Governance/specs/spiral-s1a/mss_factor_trace.md`
  - `Governance/specs/spiral-s1a/error_manifest_sample.json`
- review/final:
  - `Governance/specs/spiral-s1a/review.md`
  - `Governance/specs/spiral-s1a/final.md`
