# EmotionQuant Capability 状态总览（执行事实版）

**版本**: v8.0.0  
**最后更新**: 2026-02-23  
**适用对象**: 个人开发、个人使用

---

## 1. 文档定位（去路线主控）

本文件不是路线图，不承担任务编排。

本文件只回答 3 件事：

1. 哪些能力已经可运行可复现
2. 当前阻断点在哪里
3. 进入下一圈前必须满足什么门禁

判定原则：一切以 `run/test/artifact/review/sync` 与质量门结果为准，不以“计划文字完成”作为完成依据。
闭环五件套标准写法：`run + test + artifact + review + sync`。

---

## 2. 能力可用判定（统一口径）

能力标记为 `completed` 必须同时满足：

1. 存在可复现 `run` 命令
2. 至少 1 条自动化测试通过
3. 存在可检查产物
4. 有圈级复盘（`review.md`）
5. 有最小同步记录（development-status/debts/reusable-assets）
6. 通过 `python -m scripts.quality.local_quality_check --contracts --governance`

---

## 3. 当前能力状态快照（2026-02-23）

| CP | 能力 | 状态 | 证据入口 |
|---|---|---|---|
| CP-01 | Data Layer | completed | `Governance/specs/spiral-s0*/final.md` |
| CP-02 | MSS | completed | `Governance/specs/spiral-s1*/final.md` |
| CP-03 | IRS | completed | `Governance/specs/spiral-s2*/final.md` |
| CP-04 | PAS | completed | `Governance/specs/spiral-s2*/final.md` |
| CP-05 | Integration | completed | `Governance/specs/spiral-s2b/final.md` `Governance/specs/spiral-s2c/final.md` |
| CP-06 | Backtest | completed | `Governance/specs/spiral-s3/final.md` |
| CP-07 | Trading | completed | `Governance/specs/spiral-s4/final.md` `Governance/specs/spiral-s4r/final.md` |
| CP-08 | GUI | in_progress | `Governance/specs/spiral-s5/final.md` |
| CP-09 | Analysis | completed | `Governance/specs/spiral-s3b/final.md` |
| CP-10 | Validation | completed | `Governance/specs/spiral-s3e/final.md` |

---

## 4. 当前执行焦点与阻断

### 4.1 当前焦点

- 焦点圈：S5（GUI 最小闭环）
- 后续圈：S6（稳定化）-> S7a（自动调度）

### 4.2 阻断管理

- P0/P1 阻断以 `Governance/record/debts.md` 最新记录为准
- 圈状态与事件时间线以 `Governance/record/development-status.md` 为准
- 若“文档状态”与“运行事实”冲突，按运行事实回滚文档口径

---

## 5. 执行入口（事实优先）

1. 执行卡入口：`Governance/SpiralRoadmap/planA/EXECUTION-CARDS-INDEX.md`
2. 圈级状态日志：`Governance/record/development-status.md`
3. 圈级交付证据：`Governance/specs/spiral-s{N}/final.md` + `review.md`
4. 路线图文档（如 planA）仅作参考，不作为“完成判定”唯一依据

---

## 6. CP 文档角色

`CP-*.md` 统一作为能力契约文档，职责仅限：

1. 输入/输出字段契约
2. Entry/Exit 门禁
3. 风险与回退策略

不承担路线编排，不承担阶段总控。

---

## 7. 每圈最小同步（硬约束）

1. `Governance/specs/spiral-s{N}/final.md`
2. `Governance/record/development-status.md`
3. `Governance/record/debts.md`
4. `Governance/record/reusable-assets.md`
5. `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`（仅状态变化时更新）

---

## 8. 历史归档（只读）

- 线性旧版归档：`Governance/archive/archive-legacy-linear-v4-20260207/`
- 该目录只读，不参与当前执行，不作为任何门禁依据。

---

## 9. 核心算法完成 DoD（保留硬门槛）

仅当以下全部满足，才允许声明“核心算法 full 完成”：

1. MSS/IRS/PAS 输出语义与设计一致，且有回归证据
2. Validation 完整产出 `validation_factor_report` / `validation_weight_report` / `validation_gate_decision` / `validation_weight_plan` / `validation_run_manifest`
3. Integration 完成 Gate + 权重桥接，链路可审计
4. `final_gate=FAIL` 必阻断；`PASS/WARN` 才可进入后续圈
5. 执行边界一致生效：`contract_version="nc-v1"` 且 `risk_reward_ratio >= 1.0`
6. 契约行为回归、治理一致性、算法语义回归全部通过
7. S3c/S3d/S3e 全部完成并具备 SW31/MSS adaptive/Validation 生产口径三条证据链

---

## 10. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v8.0.0 | 2026-02-23 | 去路线主控化：改为执行事实版（能力状态 + 阻断 + 硬门禁）；历史归档路径迁移到 `Governance/archive/` |
