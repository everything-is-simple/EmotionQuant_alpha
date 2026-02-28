# S1b Review（6A A4/A5）

**Spiral**: S1b  
**状态**: completed  
**复盘日期**: 2026-02-15

## 1. A3 交付结果

- 新增 MSS 消费验证流程：
  - `src/algorithms/mss/probe.py`
  - `src/integration/mss_consumer.py`
- 统一入口新增 `mss-probe` 子命令：`src/pipeline/main.py`
- 新增 S1b 合同测试：
  - `tests/unit/algorithms/mss/test_mss_probe_contract.py`
  - `tests/unit/integration/test_mss_integration_contract.py`
- 补充 CLI 回归：`tests/unit/pipeline/test_cli_entrypoint.py` 增加 `mss-probe` 路径

## 2. A4 验证记录

### run

- `python -m src.pipeline.main --env-file none mss-probe --start 20260210 --end 20260217`  
  结果: PASS（`status=ok`, `top_bottom_spread_5d=0.0`, `conclusion=WARN_FLAT_SPREAD`）

### test

- `python -m pytest -q tests/unit/config/test_config_defaults.py`  
  结果: PASS（2 passed）
- `python -m pytest -q tests/unit/algorithms/mss/test_mss_probe_contract.py tests/unit/integration/test_mss_integration_contract.py`  
  结果: PASS（2 passed）

### contracts/governance

- `python -m scripts.quality.local_quality_check --contracts --governance`  
  结果: PASS（contracts/behavior/governance 全通过）

### 防跑偏门禁

- `python -m pytest -q tests/unit/scripts/test_contract_behavior_regression.py tests/unit/scripts/test_governance_consistency_check.py`  
  结果: PASS（11 passed）

## 3. A5 证据链

- requirements: `Governance/specs/spiral-s1b/requirements.md`
- probe report: `Governance/specs/spiral-s1b/mss_only_probe_report.md`
- consumption case: `Governance/specs/spiral-s1b/mss_consumption_case.md`
- error sample: `Governance/specs/spiral-s1b/error_manifest_sample.json`
- 核心实现:
  - `src/algorithms/mss/probe.py`
  - `src/integration/mss_consumer.py`
  - `src/pipeline/main.py`

## 4. 偏差与风险

- 偏差: 当前探针以 `mss_temperature` 的 5 日前后变化计算 `top_bottom_spread_5d`，未接入真实收益序列。
- 风险: 中。可满足 S1b“消费闭环”目标，但 S2a 前建议替换为收益口径验证并扩展样本期。

## 5. 消费记录

- 下游消费方: S2a（IRS/PAS 叠加前验证）。
- 消费方式: Integration 侧通过 `load_mss_panorama_for_integration` 读取 `mss_panorama` 必需字段。
- 消费结论: `mss_only_probe_report` 已包含 `top_bottom_spread_5d` 与结论，`mss_consumption_case` 已记录消费字段与窗口结论，可作为 S2a 输入前置证据。

## 6. 跨文档联动

- 本圈未引入命名契约破坏性变更，不触发 `docs/naming-contracts.schema.json` 与 CP 文档强制联动。
