# EmotionQuant 开发状态（Spiral 版）

**最后更新**: 2026-02-15  
**当前版本**: v3.6（S1b 已按 6A 收口，进入 S2a）  
**仓库地址**: ${REPO_REMOTE_URL}（定义见 `.env.example`）

---

## 当前阶段

**S2：IRS + PAS + Validation 最小闭环**（S1 已完成，进入 S2a）

- S0a（统一入口与配置注入）: 已完成并补齐 6A 证据链。
- S0b（L1 采集入库闭环）: 已完成并补齐 6A 证据链。
- S0c（L2 快照与失败链路）: 已完成并补齐 6A 证据链。
- S1a（MSS 最小评分可跑）: 已完成并补齐 6A 证据链。
- S1b（MSS 消费验证闭环）: 已完成并补齐 6A 证据链。

---

## 已完成（2026-02-15）

1. 完成 S1b 开发与验证：`eq mss-probe --start {start} --end {end}`，产出 `mss_only_probe_report` 与消费样例。
2. 新增 S1b 合同测试：`test_mss_probe_contract.py`、`test_mss_integration_contract.py`；并补 CLI `mss-probe` 路径回归。
3. 归档 S1b 样例证据到 `Governance/specs/spiral-s1b`。
4. 重跑关键门禁并通过：config baseline、S1b 目标测试、contracts/governance、防跑偏回归测试。

---

## Spiral 进度看板

| Spiral | 目标 | 状态 | 备注 |
|---|---|---|---|
| S0a | 统一入口与配置注入可用 | ✅ 已完成 | 6A 证据已归档 |
| S0b | L1 采集入库闭环 | ✅ 已完成 | 6A 证据已归档 |
| S0c | L2 快照与失败链路闭环 | ✅ 已完成 | 6A 证据已归档 |
| S1a | MSS 最小评分可跑 | ✅ 已完成 | 6A 证据已归档 |
| S1b | MSS 消费验证闭环 | ✅ 已完成 | 6A 证据已归档 |
| S2a | IRS + PAS + Validation 最小闭环 | 🟡 待执行 | 下一圈主目标 |
| S2b | MSS+IRS+PAS 集成推荐闭环 | 📋 未开始 | 依赖 S2a 完成 |
| S3 | 回测闭环 | 📋 未开始 | 依赖 S2 完成 |
| S4 | 纸上交易闭环 | 📋 未开始 | 依赖 S3 完成 |
| S5 | GUI + 分析闭环 | 📋 未开始 | 依赖 S4 完成 |
| S6 | 稳定化闭环 | 📋 未开始 | 重跑一致性与债务清偿 |

---

## 下一步（S2a）

1. 实现 `eq recommend --date {trade_date} --mode mss_irs_pas --with-validation` 最小执行路径。
2. 补齐 `tests/unit/algorithms/irs/test_irs_contract.py`、`tests/unit/algorithms/pas/test_pas_contract.py`、`tests/unit/integration/test_validation_gate_contract.py`。
3. 产出 `irs_industry_daily_sample.parquet`、`stock_pas_daily_sample.parquet`、`validation_gate_decision_sample.parquet`。
4. 完成 S2a 的 `requirements/review/final` 与最小同步 5 项。

---

## 风险提示

1. S0c 行业快照为“全市场聚合”最小实现，尚未接入 SW 行业粒度聚合。
2. 真实远端采集链路仍需端到端回归，不应在交易路径直接使用当前离线样例口径。

---

## 版本历史

| 日期 | 版本 | 变更内容 |
|---|---|---|
| 2026-02-15 | v3.6 | 完成 S1b 开发与 6A 收口，状态推进到 S2a 待执行 |
| 2026-02-15 | v3.5 | 完成 S1a 开发与 6A 收口，状态推进到 S1b 待执行 |
| 2026-02-15 | v3.4 | 完成 S0c 开发与 6A 收口，状态推进到 S1a 待执行 |
| 2026-02-15 | v3.3 | 回补 S0a/S0b 的 6A 收口证据，并把状态推进到 S0c 待执行 |
| 2026-02-14 | v3.2 | 同步闭环修订：补齐 `contract_version=nc-v1` / `risk_reward_ratio>=1.0` 执行边界与 contracts/governance 门禁口径 |
| 2026-02-07 | v3.1 | 统一 CP 术语与最小同步契约；重写 ROADMAP/Workflow/Steering 关键文档 |
| 2026-02-07 | v3.0 | 切换到 Spiral 状态看板；更新仓库地址为 GitHub；定义 S0 进出门禁 |
| 2026-02-06 | v2.3 | 线性 Phase 状态（归档口径） |
