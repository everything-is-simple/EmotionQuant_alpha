# S0a Requirements（6A A1/A2）

**Spiral**: S0a  
**状态**: completed  
**最后更新**: 2026-02-15

## 1. A1 Align

- 主目标: 建立统一入口 `eq` 与配置注入最小闭环。
- In Scope:
  - `pyproject.toml` 增加 `project.scripts.eq`
  - `src.pipeline.main` 支持 `run/version`、`--env-file`、`--print-config`、`--dry-run`
  - 补齐入口合同测试 `tests/unit/pipeline/test_cli_entrypoint.py`
- Out Scope:
  - L1-L4 业务链路实现
  - MSS/IRS/PAS 计算逻辑

## 2. A2 Architect

- CP Slice: `CP-01`（1 个 Slice）
- 跨模块契约:
  - CLI 层仅通过 `Config.from_env()` 注入配置
  - `eq run --dry-run` 不触发业务写入
- 失败策略:
  - 参数错误返回非 0
  - 配置注入失败阻断收口

## 3. 本圈最小证据定义

- run:
  - `C:\miniconda3\python.exe -m src.pipeline.main --help`
  - `C:\miniconda3\python.exe -m src.pipeline.main --print-config run --date 20260215 --source tushare --dry-run`
- test:
  - `C:\miniconda3\python.exe -m pytest -q tests/unit/pipeline/test_cli_entrypoint.py`
- artifact:
  - `Governance/specs/spiral-s0a/cli_contract.md`
  - `Governance/specs/spiral-s0a/config_effective_values.sample.json`
- review/final:
  - `Governance/specs/spiral-s0a/review.md`
  - `Governance/specs/spiral-s0a/final.md`
