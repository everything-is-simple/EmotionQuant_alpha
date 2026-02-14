# EmotionQuant 可复用资产登记表（Spiral 版）

**最后更新**: 2026-02-14  
**版本**: v2.2  
**范围**: S0-S6

---

## 分级定义

| 等级 | 说明 |
|---|---|
| S | 可直接复用、稳定 |
| A | 可复用，但需少量适配 |
| B | 结构可参考，需较大改造 |

---

## 治理与流程资产

| ID | 资产 | 路径 | 等级 | 用途 |
|---|---|---|---|---|
| S-GOV-001 | Spiral 主控路线图 | `Governance/Capability/SPIRAL-CP-OVERVIEW.md` | S | 圈级目标、CP 组合、最小同步 |
| S-GOV-002 | CP 能力包模板 | `Governance/Capability/CP-*.md` | S | 契约/Slice/Gate 复用 |
| S-GOV-003 | Task 闭环卡片模板 | `Governance/Capability/SPIRAL-TASK-TEMPLATE.md` | S | 每日任务拆解 |
| S-GOV-004 | 统一 6A 工作流 | `Governance/steering/6A-WORKFLOW.md` | S | Spiral 到 Task 到 Step 一体执行 |
| S-GOV-005 | 6A 历史兼容说明 | `Governance/steering/6A-WORKFLOW.md` | A | 回溯历史口径（已并入主工作流），不参与当前执行 |
| S-GOV-006 | 命名契约变更模板 | `Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md` | S | 契约变更单点归档与审计 |
| S-GOV-007 | 跨文档联动模板 | `Governance/steering/CROSS-DOC-CHANGE-LINKAGE-TEMPLATE.md` | S | 变更影响面同步 |
| A-GOV-008 | 质量门禁 CI 工作流 | `.github/workflows/quality-gates.yml` | A | contracts/governance 自动化检查 |

---

## 设计资产

| ID | 资产 | 路径 | 等级 | 用途 |
|---|---|---|---|---|
| S-DES-001 | 系统总览（Spiral） | `docs/system-overview.md` | S | 架构基线 |
| S-DES-002 | 模块索引 | `docs/module-index.md` | S | 设计导航 |
| S-DES-003 | 命名契约 Schema | `docs/naming-contracts.schema.json` | S | 枚举/阈值机器可读单源 |
| S-DES-004 | 命名契约术语表 | `docs/naming-contracts-glossary.md` | S | 名词与边界统一 |
| A-DES-005 | 回测选型策略 | `docs/design/core-infrastructure/backtest/backtest-engine-selection.md` | A | 引擎替换决策 |
| A-DES-006 | 因子/权重验证设计 | `docs/design/core-algorithms/validation/*` | A | 验证模块落地 |

---

## 代码与配置资产

| ID | 资产 | 路径 | 等级 | 用途 |
|---|---|---|---|---|
| A-CFG-001 | Python 项目依赖分层 | `pyproject.toml` | A | 主依赖与可选依赖管理 |
| A-CFG-002 | 运行依赖清单 | `requirements.txt` | A | 快速环境安装 |
| S-QA-003 | 本地一致性检查脚本 | `scripts/quality/local_quality_check.py` | S | contracts/governance 本地门禁 |
| S-QA-004 | 契约行为回归脚本 | `scripts/quality/contract_behavior_regression.py` | S | 边界行为固定回归 |
| B-CODE-005 | Skeleton 目录结构 | `src/` | B | 模块落地骨架 |

---

## 当前空缺（需后续沉淀）

1. 可复用数据下载 CLI（目标 S0/S1）
2. 可复用验证报告生成器（目标 S1/S2）
3. 可复用回测基线 Runner（目标 S3）
4. `local_quality_check` 结果自动归档器（目标 S2/S3）

---

## 版本历史

| 日期 | 版本 | 变更内容 |
|---|---|---|
| 2026-02-14 | v2.2 | 新增命名契约与质量门禁资产（schema/glossary/templates/local-check/CI workflow）；补齐当前空缺 |
| 2026-02-12 | v2.1 | 路径整理：S-GOV-005 从失效归档目录切换为 `6A-WORKFLOW.md` 历史兼容说明入口 |
| 2026-02-07 | v2.0 | 重建为 Spiral 资产清单，移除旧线性 Task 占位口径 |
| 2026-02-05 | v1.4 | 线性阶段资产登记版本 |


