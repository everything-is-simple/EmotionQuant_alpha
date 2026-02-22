# Spiral S3b Final

## 状态
- in_progress

## 结论
- 固定窗口 `20260210-20260213` 已完成软门修复收口：`recommend` 从 `factor_validation_fail` 转为 `WARN/GO`，并保留 `factor_gate_raw=FAIL` 审计字段。
- Option2 扩窗 `20260119-20260213` 已完成：`backtest= WARN/GO`（`total_trades=36`，`consumed_signal_rows=288`），`analysis= PASS/GO`，A/B/C 结论为 `A_not_dominant`。
- 当前剩余缺口为 2 天（`20260126`、`20260202`）仍触发 `factor_validation_fail`，导致 20 日窗口 `integrated_recommendation` 覆盖为 `18/20`，S3b 继续保持 `in_progress` 并转入 S3e 精准校准收口。

## 收口前必备
1. 逐日清零剩余 2 个 `factor_validation_fail`（`20260126`、`20260202`），确保扩窗覆盖达到 `20/20`。
2. 复跑 `20` 日窗口 A/B/C，并确认 `signal/execution/cost` 三分解结论稳定可复核。
3. 完成 run/test/artifact/review/sync 五件套，并通过 `local_quality_check --contracts --governance`。
4. 在 `Governance/specs/spiral-s3b/review.md` 固化“软门适用边界 + 残留 FAIL 日期 + 降级策略”。
5. 完成最小同步：
   - `Governance/specs/spiral-s3b/final.md`
   - `Governance/record/development-status.md`
   - `Governance/record/debts.md`
   - `Governance/record/reusable-assets.md`
   - `Governance/Capability/SPIRAL-CP-OVERVIEW.md`
