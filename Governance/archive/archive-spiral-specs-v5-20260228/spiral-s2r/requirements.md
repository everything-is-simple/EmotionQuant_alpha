# S2r Requirements（6A A1/A2）

**Spiral**: S2r  
**状态**: completed  
**最后更新**: 2026-02-21

## 1. A1 Align

- 主目标: 固化 S2 失败修复子圈合同，保证 `--repair s2r` 触发时“只修不扩、可追溯、可回放”。
- In Scope:
  - 支持 `eq recommend --mode integrated --repair s2r` 运行路径
  - 产出修复证据：`s2r_patch_note.md`、`s2r_delta_report.md`
  - 修复后保留关键审计字段：`integration_mode`、`weight_plan_id`、`quality_gate_status`
  - 允许 `--integration-mode {top_down|bottom_up|dual_verify|complementary}` 与修复链路联动
- Out Scope:
  - 新增策略能力或扩展推荐逻辑
  - 修改 S2 以外圈层的业务语义

## 2. A2 Architect

- CP Slice: `CP-05`（质量门失败修复子圈）
- 跨模块契约:
  - 输入:
    - `integrated_recommendation`
    - `quality_gate_report`
    - `validation_gate_decision`
  - 输出:
    - `s2r_patch_note.md`
    - `s2r_delta_report.md`
    - 修复后 `quality_gate_report.md` / `s2_go_nogo_decision.md`
  - 命名/边界约束:
    - `contract_version = "nc-v1"`
    - `repair_scope = quality_gate_only`
    - 不允许绕过 `final_gate=FAIL` 的阻断语义

## 3. 本圈最小证据定义

- run:
  - `python -m src.pipeline.main --env-file .tmp/.env.s2b.artifacts recommend --date 20260218 --mode integrated --repair s2r`
- test:
  - `python -m pytest -q tests/unit/integration/test_quality_gate_contract.py`
  - `python -m pytest -q tests/unit/integration/test_validation_gate_contract.py`
  - `python -m scripts.quality.local_quality_check --contracts --governance`
- artifact:
  - `artifacts/spiral-s2r/{trade_date}/s2r_patch_note.md`
  - `artifacts/spiral-s2r/{trade_date}/s2r_delta_report.md`
  - `artifacts/spiral-s2r/{trade_date}/quality_gate_report.md`
  - `artifacts/spiral-s2r/{trade_date}/s2_go_nogo_decision.md`
- review/final:
  - `Governance/specs/spiral-s2r/review.md`
  - `Governance/specs/spiral-s2r/final.md`
