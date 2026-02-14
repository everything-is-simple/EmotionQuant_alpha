# EmotionQuant 开发状态（Spiral 版）

**最后更新**: 2026-02-14  
**当前版本**: v3.2（治理与契约门禁基线收敛，S0 待执行）  
**仓库地址**: ${REPO_REMOTE_URL}（定义见 `.env.example`）

---

## 当前阶段

**S0：数据最小闭环**（准备就绪，待执行）

S0 目标：完成一条可复现的最小数据链路，并产出可验证证据。

---

## 已完成（本轮）

1. 核心设计完成首轮沙盘评审与闭环修订（MSS/IRS/PAS/Validation/Integration/Backtest/Trading/Analysis/GUI/Data Layer）。
2. 命名契约收敛为 Schema-first：`docs/naming-contracts.schema.json`（`nc-v1`）+ `docs/naming-contracts-glossary.md`。
3. Integration/Backtest/Trading 执行边界统一：`contract_version=nc-v1` 与 `risk_reward_ratio >= 1.0`。
4. 本地质量门禁与行为回归脚本可执行：`scripts/quality/local_quality_check.py`、`scripts/quality/contract_behavior_regression.py`。
5. SpiralRoadmap 与 Capability/Steering 已完成交叉同步，圈间推进门禁明确。
6. 本轮已完成“必须更新 + 建议更新”10 份治理文档闭环修订。

---

## Spiral 进度看板

| Spiral | 目标 | 状态 | 备注 |
|---|---|---|---|
| S0 | 数据最小闭环 | 🟡 准备就绪 | 治理门禁就绪，等待首条 run/test/artifact 实现证据 |
| S1 | MSS 闭环 | 📋 未开始 | 依赖 S0 完成 |
| S2 | IRS/PAS/Integration 闭环 | 📋 未开始 | 依赖 S1 完成 |
| S3 | 回测闭环 | 📋 未开始 | 依赖 S2 完成 |
| S4 | 纸上交易闭环 | 📋 未开始 | 依赖 S3 完成 |
| S5 | GUI + 分析闭环 | 📋 未开始 | 依赖 S4 完成 |
| S6 | 稳定化闭环 | 📋 未开始 | 重跑一致性与债务清偿 |

---

## S0 进入条件（Go）

- [x] 任务模板已纳入契约/治理门禁检查项
- [x] S0 In/Out Scope 与依赖边界已在路线图明确
- [x] 输入输出契约与失败处理口径已统一
- [ ] 选定一条运行命令和一条最小测试

---

## S0 退出条件（Done）

- [ ] 可复制命令可运行
- [ ] 自动化测试通过
- [ ] 至少 1 个产物文件生成
- [ ] `review.md` 与 `final.md` 已产出
- [ ] `Governance/record/*` 已同步
- [ ] 如涉及契约/治理变更，`python -m scripts.quality.local_quality_check --contracts --governance` 已通过

---

## 风险提示

1. 代码层仍未形成首圈可运行闭环，当前最大风险仍是“文档先行但实现滞后”。
2. Validation/Integration/Backtest/Trading 的契约边界已收敛，但缺少持续运行回归证据。
3. 回测与交易链路尚未形成端到端最小可运行样例。

---

## 版本历史

| 日期 | 版本 | 变更内容 |
|---|---|---|
| 2026-02-14 | v3.2 | 同步闭环修订：补齐 `contract_version=nc-v1` / `risk_reward_ratio>=1.0` 执行边界与 contracts/governance 门禁口径 |
| 2026-02-07 | v3.1 | 统一 CP 术语与最小同步契约；重写 ROADMAP/Workflow/Steering 关键文档 |
| 2026-02-07 | v3.0 | 切换到 Spiral 状态看板；更新仓库地址为 GitHub；定义 S0 进出门禁 |
| 2026-02-06 | v2.3 | 线性 Phase 状态（归档口径） |


