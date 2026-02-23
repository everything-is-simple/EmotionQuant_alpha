# Spiral S3b Review

## 状态
- completed

## 当前进展
- 已落地 S3b 最小执行入口：`eq analysis`（A/B/C 对照、实盘-回测偏差、归因摘要）。
- 已补齐并通过 S3b 目标测试：
  - `pytest tests/unit/analysis/test_ab_benchmark_contract.py -q`
  - `pytest tests/unit/analysis/test_live_backtest_deviation_contract.py -q`
  - `pytest tests/unit/analysis/test_attribution_summary_contract.py -q`
- 已形成跨窗口稳定性证据（W1~W4）：
  - `artifacts/spiral-s3b/20260213/s3b_cross_window_stability_summary.json`
  - `artifacts/spiral-s3b/20260213/s3b_cross_window_stability_summary.md`
  - `artifacts/spiral-s3b/20260213/cross_window/W1_20260102_20260213/*`
  - `artifacts/spiral-s3b/20260213/cross_window/W2_20260119_20260213/*`
  - `artifacts/spiral-s3b/20260213/cross_window/W3_20260210_20260213/*`
  - `artifacts/spiral-s3b/20260213/cross_window/W4_20260212_20260213/*`
- 关键结论（跨窗口）：
  - `all_windows_go=true`，四窗均 `backtest=WARN/GO` + `analysis=WARN/GO`
  - A/B/C 结论稳定为 `A_not_dominant`
  - 三分解主导项稳定为 `none`
  - `remaining_failures=0`、`integrated_days=20`

## 关键风险
- 固定窗口 `20260210-20260213` 已从阻断改为可审计降级：`S3 backtest` 输出 `no_long_entry_signal_in_window`（WARN/GO），`S3b` 在无成交样本场景输出 N/A 警告（WARN/GO）。
- 当前 `dominant_component=none` 语义稳定，但仍受“可比成交样本不足/无成交样本”边界约束；新增 live filled 样本后需按同一框架复跑复核。

## 复盘点
- A/B/C 对照是否齐备且口径一致。
- `signal/execution/cost` 三分解是否完整且可追溯。
- 结论是否可直接映射为 S4b 防御参数输入。
- `consumption.md` 与 `gate_report.md` 是否给出可执行的 go/no-go 结论。
