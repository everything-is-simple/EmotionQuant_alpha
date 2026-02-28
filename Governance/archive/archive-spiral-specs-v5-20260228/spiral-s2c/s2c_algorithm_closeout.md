# S2c 算法收口结论（release）

- Spiral: S2c
- trade_date: 20260218
- evidence_lane: release
- run_command: `python -m src.pipeline.main --env-file artifacts/spiral-s2c/20260218/.env.s2c.demo recommend --date 20260218 --mode integrated --with-validation-bridge --evidence-lane release`

## 1. 运行结论

- quality_gate_status: PASS
- go_nogo: GO
- integrated_count: 1
- final_gate: PASS

## 2. 门禁与契约

- `selected_weight_plan -> validation_weight_plan.plan_id -> integrated_recommendation.weight_plan_id`：PASS
- `final_gate=FAIL` 阻断语义：已由合同测试覆盖，语义保持有效。
- `contract_version=nc-v1` 与 `risk_reward_ratio>=1.0`：一致生效。

## 3. 本轮修复项

1. 修复 S2c 正式证据与调试证据混写风险：引入 `evidence_lane`。
2. 新增 `release/debug` 双目录：
   - `release`: `artifacts/spiral-s2c/{trade_date}`
   - `debug`: `artifacts/spiral-s2c-debug/{trade_date}`
3. 新增发布证据同步脚本：`scripts/quality/sync_s2c_release_artifacts.py`，同步前强校验 PASS/GO 与样例行数。

## 4. 冲突处置结论

- 已处置问题：同日 PASS/FAIL 双口径冲突。
- 处置方式：以 release 场景重建证据 + 同步脚本前置校验 + lane 隔离防污染。
- 当前口径：`release` 为唯一正式收口证据来源。

## 5. 下一步入口

- S2c 收口完成后，按路线推进到 S3a（ENH-10 数据采集增强），并保持阶段A->B门禁不放松。
