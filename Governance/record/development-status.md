# EmotionQuant 开发状态（Spiral 版）

**最后更新**: 2026-02-16  
**当前版本**: v3.9（S3a 规划已落位，进入 ENH-10 执行准备）  
**仓库地址**: ${REPO_REMOTE_URL}（定义见 `.env.example`）

---

## 当前阶段

**S3a 准备：S2 信号生成闭环已完成，先执行 ENH-10 数据采集增强**

- S0a（统一入口与配置注入）: 已完成并补齐 6A 证据链。
- S0b（L1 采集入库闭环）: 已完成并补齐 6A 证据链。
- S0c（L2 快照与失败链路）: 已完成并补齐 6A 证据链。
- S1a（MSS 最小评分可跑）: 已完成并补齐 6A 证据链。
- S1b（MSS 消费验证闭环）: 已完成并补齐 6A 证据链。
- S2a（IRS + PAS + Validation 最小闭环）: 已完成并补齐 6A 证据链。
- S2b（MSS+IRS+PAS 集成推荐闭环）: 已完成并补齐 6A 证据链。

---

## 已完成（2026-02-15）

1. 完成 S2b 开发与验证：`eq recommend --date {trade_date} --mode integrated`，输出 `integrated_recommendation` 与 `quality_gate_report`。
2. 新增 S2b 合同测试：`test_integration_contract.py`、`test_quality_gate_contract.py`；并补 CLI `integrated` 路径回归。
3. 归档 S2b 样例证据到 `Governance/specs/spiral-s2b`。
4. 重跑关键门禁并通过：env baseline、S2b 目标测试、contracts/governance、防跑偏回归测试。

## 本次同步（2026-02-16）

1. 新增下一阶段执行卡：`Governance/SpiralRoadmap/S3A-EXECUTION-CARD.md`。
2. 新建 `Governance/specs/spiral-s3a/` 证据目录，并落位 `requirements/review/final` 三件套骨架。
3. 主控路线状态推进为 `S3a planned`，并明确 `S3` 为 S3a 后继圈。

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
| S3a | ENH-10 数据采集增强闭环 | 🟡 准备中 | 下一圈主目标 |
| S3 | 回测闭环 | 📋 未开始 | 依赖 S3a 完成 |
| S4 | 纸上交易闭环 | 📋 未开始 | 依赖 S3 完成 |
| S5 | GUI + 分析闭环 | 📋 未开始 | 依赖 S4 完成 |
| S6 | 稳定化闭环 | 📋 未开始 | 重跑一致性与债务清偿 |

---

## 下一步（S3a 准备）

1. 启动 `eq fetch-batch/fetch-status/fetch-retry` 三命令实现与契约测试补齐。
2. 固化 S3a 核心证据：`fetch_progress.json`、`throughput_benchmark.md`、`fetch_retry_report.md`。
3. 完成 S3a 门禁验收后，推进 S3 回测闭环实施。

---

## 风险提示

1. S0c 行业快照为“全市场聚合”最小实现，尚未接入 SW 行业粒度聚合。
2. 真实远端采集链路仍需端到端回归，不应在交易路径直接使用当前离线样例口径。

---

## 版本历史

| 日期 | 版本 | 变更内容 |
|---|---|---|
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
