# EmotionQuant 可复用资产登记表（Spiral 版）

**最后更新**: 2026-02-17  
**版本**: v2.12  
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
| S-GOV-009 | S0a/S0b/S0c 6A 证据档案模板 | `Governance/specs/spiral-s0a/*` + `Governance/specs/spiral-s0b/*` + `Governance/specs/spiral-s0c/*` | S | requirements/review/final 与样例证据可复用 |
| S-GOV-010 | S1a 6A 证据档案模板 | `Governance/specs/spiral-s1a/*` | S | MSS 圈 requirements/review/final 与样例证据复用 |
| S-GOV-011 | S1b 6A 证据档案模板 | `Governance/specs/spiral-s1b/*` | S | MSS 消费验证圈 requirements/review/final 与样例证据复用 |
| S-GOV-012 | S2a 6A 证据档案模板 | `Governance/specs/spiral-s2a/*` | S | IRS/PAS/Validation 圈 requirements/review/final 与样例证据复用 |
| S-GOV-013 | S2b 6A 证据档案模板 | `Governance/specs/spiral-s2b/*` | S | Integration 圈 requirements/review/final 与样例证据复用 |
| S-GOV-014 | S3a 6A 证据档案模板 | `Governance/specs/spiral-s3a/*` | S | ENH-10 圈 requirements/review/final 与门禁证据骨架复用 |
| S-GOV-015 | S2c 6A 阶段证据模板 | `Governance/specs/spiral-s2c/*` | A | 桥接硬门禁子步与 full 语义收口证据复用 |

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
| S-QA-005 | 设计溯源检查脚本 | `scripts/quality/design_traceability_check.py` | A | 检查 MSS/IRS/PAS/Validation/Integration 等核心模块 `DESIGN_TRACE` 标记，降低设计-实现漂移 |
| A-CODE-005 | 统一 CLI 入口骨架 | `src/pipeline/main.py` + `main.py` | A | 统一入口、参数路由、配置注入 |
| A-CODE-006 | L1 采集最小闭环骨架 | `src/data/fetcher.py` + `src/data/l1_pipeline.py` + `src/data/repositories/*` | A | S0b 数据采集、落库、产物输出 |
| A-CODE-007 | L2 快照与 canary 最小闭环骨架 | `src/data/l2_pipeline.py` + `src/data/models/snapshots.py` | A | S0c 快照生成、质量字段门禁、错误分级 |
| A-TEST-008 | S0 合同测试集 | `tests/unit/pipeline/test_cli_entrypoint.py` + `tests/unit/data/test_fetcher_contract.py` + `tests/unit/data/test_l1_repository_contract.py` + `tests/unit/data/test_snapshot_contract.py` + `tests/unit/data/test_s0_canary.py` | A | 入口/L1/L2 合同回归保障 |
| A-CODE-009 | MSS 最小评分骨架 | `src/algorithms/mss/engine.py` + `src/algorithms/mss/pipeline.py` + `src/pipeline/main.py` | A | S1a 的 `eq mss` 计算、落库、产物输出 |
| A-TEST-010 | MSS 合同测试集 | `tests/unit/algorithms/mss/test_mss_contract.py` + `tests/unit/algorithms/mss/test_mss_engine.py` | A | MSS 输出字段与评分边界回归保障 |
| A-CODE-011 | MSS 探针与消费器骨架 | `src/algorithms/mss/probe.py` + `src/integration/mss_consumer.py` + `src/pipeline/main.py` | A | S1b 的 `eq mss-probe` 消费验证与证据生成 |
| A-TEST-012 | MSS 探针/集成消费合同测试集 | `tests/unit/algorithms/mss/test_mss_probe_contract.py` + `tests/unit/integration/test_mss_integration_contract.py` | A | MSS 输出可消费性与探针指标回归保障 |
| A-CODE-013 | S2a 推荐编排与三表最小闭环骨架 | `src/algorithms/irs/pipeline.py` + `src/algorithms/pas/pipeline.py` + `src/algorithms/validation/pipeline.py` + `src/pipeline/recommend.py` | A | S2a 的 `eq recommend --mode mss_irs_pas --with-validation` |
| A-TEST-014 | S2a 合同测试集 | `tests/unit/algorithms/irs/test_irs_contract.py` + `tests/unit/algorithms/pas/test_pas_contract.py` + `tests/unit/integration/test_validation_gate_contract.py` | A | IRS/PAS/Validation 输出契约回归保障 |
| A-CODE-015 | S2b 集成推荐与质量门骨架 | `src/integration/pipeline.py` + `src/pipeline/recommend.py` + `src/pipeline/main.py` | A | S2b 的 `eq recommend --mode integrated` 与质量门输出 |
| A-TEST-016 | S2b 合同测试集 | `tests/unit/integration/test_integration_contract.py` + `tests/unit/integration/test_quality_gate_contract.py` + `tests/unit/pipeline/test_cli_entrypoint.py` | A | Integration/Quality Gate/CLI 路径回归保障 |
| A-CODE-017 | S2c Validation-Integration 桥接硬门禁实现 | `src/algorithms/validation/pipeline.py` + `src/integration/pipeline.py` + `src/pipeline/recommend.py` + `src/pipeline/main.py` | A | `selected_weight_plan -> validation_weight_plan -> integrated_recommendation` 契约落地 |
| A-TEST-018 | S2c 桥接与语义回归测试集 | `tests/unit/algorithms/validation/test_weight_plan_bridge_contract.py` + `tests/unit/integration/test_validation_weight_plan_bridge.py` + `tests/unit/integration/test_algorithm_semantics_regression.py` | A | 桥接一致性、Gate 阻断、关键语义边界回归 |
| A-CODE-019 | MSS zscore 语义实现与中间产物输出 | `src/algorithms/mss/engine.py` + `src/algorithms/mss/pipeline.py` | A | `ratio->zscore->[0,100]` + 缺失回退 50 + `mss_factor_intermediate` 证据 |
| A-TEST-020 | MSS full 语义合同测试 | `tests/unit/algorithms/mss/test_mss_full_semantics_contract.py` | A | 六因子温度公式与缺失回退 50 行为回归 |
| A-CODE-021 | IRS full 语义实现与中间产物输出 | `src/algorithms/irs/pipeline.py` | A | 六因子评分 + 轮动状态 + 配置建议 + `irs_factor_intermediate` 证据 |
| A-CODE-022 | PAS full 语义实现与中间产物输出 | `src/algorithms/pas/pipeline.py` | A | 三因子评分 + `effective_risk_reward_ratio` + `pas_factor_intermediate` 证据 |
| A-CODE-023 | Validation full 语义实现（五件套） | `src/algorithms/validation/pipeline.py` | A | 因子验证 + Walk-Forward 权重验证 + Gate 决策 + `validation_run_manifest` |
| A-TEST-024 | S2c full 语义合同测试集 | `tests/unit/algorithms/irs/test_irs_full_semantics_contract.py` + `tests/unit/algorithms/pas/test_pas_full_semantics_contract.py` + `tests/unit/algorithms/validation/test_factor_validation_metrics_contract.py` + `tests/unit/algorithms/validation/test_weight_validation_walk_forward_contract.py` | A | IRS/PAS/Validation full 语义回归保障 |

---

## 当前空缺（需后续沉淀）

1. 可复用 SW 行业映射聚合器（目标 S3）
2. 可复用验证报告生成器（目标 S1/S2）
3. 可复用回测基线 Runner（目标 S3）
4. `local_quality_check` 结果自动归档器（目标 S2/S3）
5. MSS 自适应分位阈值基线生成器（目标 S3）
6. Probe 真实收益口径桥接器（目标 S3）
7. IRS/PAS 评分校准器（目标 S3）

---

## 版本历史

| 日期 | 版本 | 变更内容 |
|---|---|---|
| 2026-02-17 | v2.12 | 增加 IRS/PAS/Validation full 语义实现与测试资产（A-CODE-021/022/023、A-TEST-024），并更新 S-QA-005 覆盖范围 |
| 2026-02-17 | v2.11 | 增加设计溯源检查资产（S-QA-005）与 MSS 语义实现/测试资产（A-CODE-019、A-TEST-020） |
| 2026-02-17 | v2.10 | 增加 S2c 阶段证据模板（S-GOV-015）与桥接硬门禁实现/测试资产（A-CODE-017、A-TEST-018） |
| 2026-02-16 | v2.9 | 增加 S3a 证据模板资产登记（S-GOV-014） |
| 2026-02-15 | v2.8 | 增加 S2b 证据模板与 Integration/Quality Gate 代码测试资产登记 |
| 2026-02-15 | v2.7 | 增加 S2a 证据模板与推荐编排/三表合同资产登记 |
| 2026-02-15 | v2.6 | 增加 S1b 证据模板与 MSS 探针/集成消费资产登记 |
| 2026-02-15 | v2.5 | 增加 S1a 证据模板与 MSS 代码/测试资产登记 |
| 2026-02-15 | v2.4 | 增加 S0c L2/canary 资产与 S0 全链路合同测试资产登记 |
| 2026-02-15 | v2.3 | 增加 S0a/S0b 6A 证据档案资产与 CLI/L1 合同资产登记 |
| 2026-02-14 | v2.2 | 新增命名契约与质量门禁资产（schema/glossary/templates/local-check/CI workflow）；补齐当前空缺 |
| 2026-02-12 | v2.1 | 路径整理：S-GOV-005 从失效归档目录切换为 `6A-WORKFLOW.md` 历史兼容说明入口 |
| 2026-02-07 | v2.0 | 重建为 Spiral 资产清单，移除旧线性 Task 占位口径 |
| 2026-02-05 | v1.4 | 线性阶段资产登记版本 |
