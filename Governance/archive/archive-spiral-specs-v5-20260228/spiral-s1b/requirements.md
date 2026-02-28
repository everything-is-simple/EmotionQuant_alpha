# S1b Requirements（6A A1/A2）

**Spiral**: S1b  
**状态**: completed  
**最后更新**: 2026-02-15

## 1. A1 Align

- 主目标: 完成 MSS 消费验证闭环，支持 `eq mss-probe --start {start} --end {end}`。
- In Scope:
  - 实现 `eq mss-probe --start {start} --end {end}` 可执行路径
  - 基于 `mss_panorama` 计算并输出 `top_bottom_spread_5d`
  - 产出 `mss_only_probe_report.md` 与 `mss_consumption_case.md`
  - 补齐 `tests/unit/algorithms/mss/test_mss_probe_contract.py`
  - 补齐 `tests/unit/integration/test_mss_integration_contract.py`
- Out Scope:
  - IRS/PAS/Validation 实际计算
  - Integration 最终推荐产出
  - MSS 自适应阈值与历史基线重建

## 2. A2 Architect

- CP Slice: `CP-02`, `CP-05`（2 个 Slice）
- 跨模块契约:
  - 输入: L3 表 `mss_panorama`
  - 消费模块: `src/integration/mss_consumer.py`
  - 输出产物:
    - `mss_only_probe_report.md`（含 `top_bottom_spread_5d` 与结论）
    - `mss_consumption_case.md`（记录消费字段与结论）
  - 命名约束:
    - `mss_cycle` 必须来自枚举集合
    - `trend` 使用 `up/down/sideways`
    - `contract_version = "nc-v1"`
- 失败策略:
  - `mss_panorama` 缺失或窗口无数据判定 `P0`，阻断收口
  - 日期窗口非法判定参数错误（退出码 2）

## 3. 本圈最小证据定义

- run:
  - `python -m src.pipeline.main --env-file none mss-probe --start 20260210 --end 20260217`
- test:
  - `python -m pytest -q tests/unit/config/test_config_defaults.py`
  - `python -m pytest -q tests/unit/algorithms/mss/test_mss_probe_contract.py tests/unit/integration/test_mss_integration_contract.py`
- artifact:
  - `Governance/specs/spiral-s1b/mss_only_probe_report.md`
  - `Governance/specs/spiral-s1b/mss_consumption_case.md`
  - `Governance/specs/spiral-s1b/error_manifest_sample.json`
- review/final:
  - `Governance/specs/spiral-s1b/review.md`
  - `Governance/specs/spiral-s1b/final.md`
