# S3e Review（6A A4/A5）

**Spiral**: S3e  
**状态**: completed  
**复盘日期**: 2026-02-21（A4 阶段）

- 当前状态: 已完成窗口级证据收口并闭环。
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

## 跨窗口补证（2026-02-22）

- 窗口：`20260210`、`20260211`、`20260212`、`20260213`
- 统一命令：
  - `eq validation --trade-date {trade_date} --threshold-mode regime --wfa dual-window --export-run-manifest`
- 窗口级结果：
  - 四窗全部 `status=ok`、`final_gate=WARN`、`go_nogo=GO`
  - `selected_weight_plan` 稳定为 `vp_balanced_v1`（4/4）
  - `vote_detail` 显示 `factor_gate_raw=FAIL` 在中性状态软化后进入 `factor_gate=WARN`，与 S3e 软门语义一致
- 汇总证据：
  - `artifacts/spiral-s3e/20260213/s3e_cross_window_summary.json`
  - `artifacts/spiral-s3e/20260213/s3e_cross_window_summary.md`
  - `artifacts/spiral-s3e/20260213/cross_window/*`

## 结论

- S3e 生产口径（future_returns + dual-window WFA + run_manifest）已完成跨窗口 run/test/artifact/review/sync 五件套，圈位可标记 completed。
