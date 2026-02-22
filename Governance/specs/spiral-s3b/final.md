# Spiral S3b Final

## 状态
- completed

## 结论
- 已完成跨窗口（非单窗口）稳定性复核并收口，窗口集：
  - `W1: 20260102-20260213`
  - `W2: 20260119-20260213`
  - `W3: 20260210-20260213`
  - `W4: 20260212-20260213`
- 跨窗口运行结论：
  - `all_windows_go=true`，四个窗口均为 `backtest=WARN/GO` + `analysis=WARN/GO`。
  - A/B/C 对照结论稳定：`ab_conclusion_distribution = {'A_not_dominant': 4}`。
  - 三分解主导项稳定：`dominant_component_distribution = {'none': 4}`（当前窗口样本属于无可比成交或样本不足语义，按 S3b 规则降级为 `WARN/GO`，不构成阻断）。
  - 窗口分层：`with_trade_window_count=2`，`no_trade_window_count=2`；有/无交易窗口均满足契约并可审计。
- 既有口径保持成立：
  - `remaining_failures=0`、`integrated_days=20`（证据：`artifacts/spiral-s3b/20260213/s3e_targeted_clearance_summary.json`）。
  - S3a 缩窗游标在本地 L1 覆盖场景下已降级 WARN，不再误阻断 S3/S3b 主链。

## 收口证据
1. 跨窗口总览：
   - `artifacts/spiral-s3b/20260213/s3b_cross_window_stability_summary.json`
   - `artifacts/spiral-s3b/20260213/s3b_cross_window_stability_summary.md`
2. 窗口级快照（防覆盖）：
   - `artifacts/spiral-s3b/20260213/cross_window/W1_20260102_20260213/*`
   - `artifacts/spiral-s3b/20260213/cross_window/W2_20260119_20260213/*`
   - `artifacts/spiral-s3b/20260213/cross_window/W3_20260210_20260213/*`
   - `artifacts/spiral-s3b/20260213/cross_window/W4_20260212_20260213/*`
3. 契约与治理：
   - `pytest -q` => `174 passed, 0 failed`
   - `python -m scripts.quality.local_quality_check --contracts --governance` => 全 PASS

## 边界说明（用于 S4b 输入）
1. 当前跨窗口 `dominant_component=none` 表示“可比成交样本不足/无成交样本”语义稳定，不等价于 `signal/execution/cost` 已出现可分离主导项。
2. S4b 可消费的稳定输入是：
   - A/B/C 方向稳定（`A_not_dominant`）。
   - S3/S3b 持续 `GO`，且无 P0/P1 阻断。
3. 若后续引入新的 live filled 样本，应复跑同一跨窗口框架，验证三分解主导项是否从 `none` 转为稳定非空主导分量。
