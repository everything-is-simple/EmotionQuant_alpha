# EmotionQuant 开发状态（Spiral 版）

**最后更新**: 2026-02-15  
**当前版本**: v3.3（S0a/S0b 已按 6A 收口，进入 S0c）  
**仓库地址**: ${REPO_REMOTE_URL}（定义见 `.env.example`）

---

## 当前阶段

**S0：数据最小闭环**（执行中）

- S0a（统一入口与配置注入）: 已完成并补齐 6A 证据链。
- S0b（L1 采集入库闭环）: 已完成并补齐 6A 证据链。
- S0c（L2 快照与失败链路）: 下一执行圈。

---

## 已完成（2026-02-15）

1. 回补 S0a 的 6A 文档链路：`requirements/review/final`。
2. 回补 S0b 的 6A 文档链路：`requirements/review/final`。
3. 归档 S0a/S0b 样例证据到 `Governance/specs/spiral-s0a` 与 `Governance/specs/spiral-s0b`。
4. 重跑关键门禁并通过：入口测试、L1 合同测试、contracts/governance 检查、防跑偏回归测试。

---

## Spiral 进度看板

| Spiral | 目标 | 状态 | 备注 |
|---|---|---|---|
| S0a | 统一入口与配置注入可用 | ✅ 已完成 | 6A 证据已归档 |
| S0b | L1 采集入库闭环 | ✅ 已完成 | 6A 证据已归档 |
| S0c | L2 快照与失败链路闭环 | 🟡 待执行 | 下一圈主目标 |
| S1 | MSS 闭环 | 📋 未开始 | 依赖 S0c 完成 |
| S2 | IRS/PAS/Integration 闭环 | 📋 未开始 | 依赖 S1 完成 |
| S3 | 回测闭环 | 📋 未开始 | 依赖 S2 完成 |
| S4 | 纸上交易闭环 | 📋 未开始 | 依赖 S3 完成 |
| S5 | GUI + 分析闭环 | 📋 未开始 | 依赖 S4 完成 |
| S6 | 稳定化闭环 | 📋 未开始 | 重跑一致性与债务清偿 |

---

## 下一步（S0c）

1. 实现 `eq run --date {trade_date} --source tushare --to-l2` 最小链路。
2. 补齐 `tests/unit/data/test_snapshot_contract.py` 与 `tests/unit/data/test_s0_canary.py`。
3. 产出 `market_snapshot_sample.parquet`、`industry_snapshot_sample.parquet`、`s0_canary_report.md`。
4. 完成 S0c 的 `requirements/review/final` 与最小同步 5 项。

---

## 风险提示

1. S0c 尚未落地，当前系统仍停留在 L1 可用、L2 未闭环状态。
2. S0b 当前以离线模拟数据为主，真实采集链路还需补端到端回归。

---

## 版本历史

| 日期 | 版本 | 变更内容 |
|---|---|---|
| 2026-02-15 | v3.3 | 回补 S0a/S0b 的 6A 收口证据，并把状态推进到 S0c 待执行 |
| 2026-02-14 | v3.2 | 同步闭环修订：补齐 `contract_version=nc-v1` / `risk_reward_ratio>=1.0` 执行边界与 contracts/governance 门禁口径 |
| 2026-02-07 | v3.1 | 统一 CP 术语与最小同步契约；重写 ROADMAP/Workflow/Steering 关键文档 |
| 2026-02-07 | v3.0 | 切换到 Spiral 状态看板；更新仓库地址为 GitHub；定义 S0 进出门禁 |
| 2026-02-06 | v2.3 | 线性 Phase 状态（归档口径） |
