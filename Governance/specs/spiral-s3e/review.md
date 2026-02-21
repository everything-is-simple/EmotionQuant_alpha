# S3e Review（6A A4/A5）

**Spiral**: S3e  
**状态**: in_progress  
**复盘日期**: 2026-02-21（A4 阶段）

- 当前状态: CLI 阻断已解除，进入窗口级证据收口。
- 本轮完成:
  - `eq validation` 独立入口与参数契约已落地。
  - 合同测试：future_returns 对齐 / dual-window WFA / OOS 指标三条测试通过。
- 本轮新增修复（核心算法）:
  - 修复 Validation `decay_5d` 代理公式反向问题：由“|IC| 越高 decay 越低”改为单调正向映射。
  - 新增合同测试：`tests/unit/algorithms/validation/test_decay_proxy_contract.py`。
  - 回归：`pytest tests/unit/algorithms/validation -q` 通过（9 passed）。
- 实跑结果:
  - `eq validation --trade-date 20260219 --threshold-mode regime --wfa dual-window --export-run-manifest`
    输出 `final_gate=WARN`、`go_nogo=GO`、`selected_weight_plan=vp_balanced_v1`。
