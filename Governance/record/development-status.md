# EmotionQuant 开发状态（Spiral 版）

**最后更新**: 2026-02-17  
**当前版本**: v4.4（S2c 执行中：桥接硬门禁稳定，MSS 语义起步与设计溯源门禁已接入）  
**仓库地址**: ${REPO_REMOTE_URL}（定义见 `.env.example`）

---

## 当前阶段

**S2c 执行中：已完成桥接硬门禁与回归，继续完成核心算法 full 语义后进入 S3a（ENH-10）**

- S0a（统一入口与配置注入）: 已完成并补齐 6A 证据链。
- S0b（L1 采集入库闭环）: 已完成并补齐 6A 证据链。
- S0c（L2 快照与失败链路）: 已完成并补齐 6A 证据链。
- S1a（MSS 最小评分可跑）: 已完成并补齐 6A 证据链。
- S1b（MSS 消费验证闭环）: 已完成并补齐 6A 证据链。
- S2a（IRS + PAS + Validation 最小闭环）: 已完成并补齐 6A 证据链。
- S2b（MSS+IRS+PAS 集成推荐闭环）: 已完成并补齐 6A 证据链。
- S2c（核心算法深化闭环）: 已进入实现，已完成桥接硬门禁子步与目标回归，待完成 full 语义收口。

---

## 已完成（2026-02-15）

1. 完成 S2b 开发与验证：`eq recommend --date {trade_date} --mode integrated`，输出 `integrated_recommendation` 与 `quality_gate_report`。
2. 新增 S2b 合同测试：`test_integration_contract.py`、`test_quality_gate_contract.py`；并补 CLI `integrated` 路径回归。
3. 归档 S2b 样例证据到 `Governance/specs/spiral-s2b`。
4. 重跑关键门禁并通过：env baseline、S2b 目标测试、contracts/governance、防跑偏回归测试。

## 本次同步（2026-02-17）

1. 落地 `validation_weight_plan` 桥接硬门禁：
   - Validation 输出新增 `selected_weight_plan` 并持久化 `validation_weight_plan`。
   - Integration 增加 `--with-validation-bridge`，桥接缺失/不一致强制 `FAIL + NO_GO`。
2. 新增 S2c 目标测试并通过：`test_weight_plan_bridge_contract.py`、`test_validation_weight_plan_bridge.py`、`test_algorithm_semantics_regression.py`（6 passed）。
3. 回归 S2a/S2b 合同测试通过：`test_validation_gate_contract.py`、`test_integration_contract.py`、`test_quality_gate_contract.py`（4 passed）。
4. `contracts/governance` 本地门禁通过：`python -m scripts.quality.local_quality_check --contracts --governance`。
5. 新建 `Governance/specs/spiral-s2c/*` 阶段证据（requirements/review/final + 样例产物）。
6. MSS 语义补齐起步完成：新增 `test_mss_full_semantics_contract.py` 与 `mss_factor_intermediate_sample.parquet` 产物。
7. 设计溯源门禁接入：核心模块新增 `DESIGN_TRACE`，`local_quality_check --contracts` 新增 `traceability` 检查。

---

## Spiral 进度看板

| Spiral | 目标 | 状态 | 备注 |
|---|---|---|---|
| S0a | 统一入口与配置注入可用 | ✅ 已完成 | 6A 证据已归档 |
| S0b | L1 采集入库闭环 | ✅ 已完成 | 6A 证据已归档 |
| S0c | L2 快照与失败链路闭环 | ✅ 已完成 | 6A 证据已归档 |
| S1a | MSS 最小评分可跑 | ✅ 已完成 | 6A 证据已归档 |
| S1b | MSS 消费验证闭环 | ✅ 已完成 | 6A 证据已归档 |
| S2a | IRS + PAS + Validation 最小闭环 | ✅ 已完成 | 6A 证据已归档 |
| S2b | MSS+IRS+PAS 集成推荐闭环 | ✅ 已完成 | 6A 证据已归档 |
| S2c | 核心算法深化闭环（权重桥接 + 语义收口） | 🟠 执行中 | 桥接门禁已完成，full 语义补齐中 |
| S3a | ENH-10 数据采集增强闭环 | 📋 未开始 | 依赖 S2c 完成 |
| S3 | 回测闭环 | 📋 未开始 | 依赖 S3a 完成 |
| S4 | 纸上交易闭环 | 📋 未开始 | 依赖 S3 完成 |
| S5 | GUI + 分析闭环 | 📋 未开始 | 依赖 S4 完成 |
| S6 | 稳定化闭环 | 📋 未开始 | 重跑一致性与债务清偿 |
| S7a | ENH-11 自动调度闭环 | 📋 未开始 | 依赖 S6 完成 |

---

## 下一步（S2c 执行中）

1. 继续补齐 IRS/PAS/Validation/Integration 的 full 语义（P0）：把简化映射替换为设计语义实现，并产出 S2c 证据产物；设计入口为 `docs/design/core-algorithms/` 下五模块算法文档（含 `docs/design/core-algorithms/integration/integration-algorithm.md`）。
2. 补齐 Validation 五件套当日产物（P0）：`validation_factor_report`、`validation_weight_report`、`validation_gate_decision`、`validation_weight_plan`、`validation_run_manifest`。
3. 最后做 S2c 收口（P0）：通过 `python -m scripts.quality.local_quality_check --contracts --governance`，完成 `s2c_semantics_traceability_matrix.md` 与 `s2c_algorithm_closeout.md` 后再进入 S3a。

---

## 风险提示

1. S0c 行业快照为“全市场聚合”最小实现，尚未接入 SW 行业粒度聚合。
2. 真实远端采集链路仍需端到端回归，不应在交易路径直接使用当前离线样例口径。
3. 若 `validation_weight_plan` 桥接链路缺失或不可审计，必须阻断 S2c->S3a 迁移。

---

## 版本历史

| 日期 | 版本 | 变更内容 |
|---|---|---|
| 2026-02-17 | v4.4 | S2c 继续推进：新增 MSS full 语义起步测试与中间产物；接入 `DESIGN_TRACE` + traceability 自动检查，降低“实现-设计”漂移风险 |
| 2026-02-17 | v4.3 | S2c 进入执行中：完成 `validation_weight_plan` 桥接硬门禁与目标回归（6 passed）+ S2a/S2b 回归（4 passed）；新增 `Governance/specs/spiral-s2c/*` 阶段证据 |
| 2026-02-16 | v4.2 | 明确 S2c 下一步为三段 P0 顺序；补齐 Integration 为核心算法 full 语义必选模块，并将门禁测试表述升级为 Integration + Validation 联合合同测试 |
| 2026-02-16 | v4.1 | 新增 S2c 算法深化圈并切换当前状态为 S2c 准备；落地 `validation_weight_plan` 桥接硬门禁与核心算法独立 DoD 口径 |
| 2026-02-16 | v4.0 | 同步阶段C执行合同（S5-S7a）入口与状态口径，补齐路线索引 |
| 2026-02-16 | v3.9 | 新建 S3a 执行卡与 `spiral-s3a` 证据骨架，状态从 S3 准备切换为 S3a 准备 |
| 2026-02-15 | v3.8 | 完成 S2b 开发与 6A 收口，状态推进到 S3 准备 |
| 2026-02-15 | v3.7 | 完成 S2a 开发与 6A 收口，状态推进到 S2b 待执行 |
| 2026-02-15 | v3.6 | 完成 S1b 开发与 6A 收口，状态推进到 S2a 待执行 |
| 2026-02-15 | v3.5 | 完成 S1a 开发与 6A 收口，状态推进到 S1b 待执行 |
| 2026-02-15 | v3.4 | 完成 S0c 开发与 6A 收口，状态推进到 S1a 待执行 |
| 2026-02-15 | v3.3 | 回补 S0a/S0b 的 6A 收口证据，并把状态推进到 S0c 待执行 |
| 2026-02-14 | v3.2 | 同步闭环修订：补齐 `contract_version=nc-v1` / `risk_reward_ratio>=1.0` 执行边界与 contracts/governance 门禁口径 |
| 2026-02-07 | v3.1 | 统一 CP 术语与最小同步契约；重写 ROADMAP/Workflow/Steering 关键文档 |
| 2026-02-07 | v3.0 | 切换到 Spiral 状态看板；更新仓库地址为 GitHub；定义 S0 进出门禁 |
| 2026-02-06 | v2.3 | 线性 Phase 状态（归档口径） |
