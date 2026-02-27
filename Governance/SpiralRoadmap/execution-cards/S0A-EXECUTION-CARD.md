# S0a 执行卡（v0.3）

**状态**: Implemented（工程完成，业务待重验）  
**重验口径**: 本卡“工程完成”不等于螺旋闭环完成；是否可推进以 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 的 GO/NO_GO 为准。  
**更新时间**: 2026-02-21  
**阶段**: 阶段A（S0-S2）  
**微圈**: S0a（入口与配置）

---

## 工程实现复核（2026-02-21）

- 复核结论：本卡任务已完成，入口与配置契约满足完整版并可支持实战链路。
- 证据锚点：`src/pipeline/main.py`、`src/config/config.py`、`tests/unit/pipeline/test_cli_entrypoint.py`、`tests/unit/config/test_config_defaults.py`、`tests/unit/config/test_env_docs_alignment.py`。
- 关键确认：`recommend` 子命令已支持 `--integration-mode` 与 `--repair s2r`，可承载 S2 完整语义执行。

---

## 1. 目标

- 落地统一入口 `eq`。
- 落地 `src.pipeline.main` 最小 CLI。
- 确保配置读取仅通过 `Config.from_env()` 注入。
- 确保数据门禁关键配置可在入口层可见（`flat_threshold/min_coverage_ratio/stale_hard_limit_days`）。
- 为 S2 完全版保留入口能力：`recommend` 子命令支持 `--integration-mode` 与 `--repair s2r` 参数透传。

---

## 2. run

```bash
python -m src.pipeline.main --help
eq --help
eq --env-file .env --print-config run --date 20260215 --dry-run
```

---

## 3. test

```bash
pytest tests/unit/pipeline/test_cli_entrypoint.py -q
pytest tests/unit/config/test_config_defaults.py -q
pytest tests/unit/config/test_env_docs_alignment.py -q
```

---

## 4. artifact

- `artifacts/spiral-s0a/{trade_date}/run.log`
- `artifacts/spiral-s0a/{trade_date}/test.log`
- `artifacts/spiral-s0a/{trade_date}/cli_contract.md`
- `artifacts/spiral-s0a/{trade_date}/config_effective_values.json`
- `artifacts/spiral-s0a/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields：逐字段校验 `system_config` 与 `data-layer-data-models.md` 一致性）

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s0a/review.md`
- 必填结论：
  - 入口命令是否可复现
  - 配置注入是否仅走 `Config.from_env()`
  - 门禁关键配置是否可见（`flat_threshold/min_coverage_ratio/stale_hard_limit_days`）
  - `recommend` 子命令参数契约是否包含 `--integration-mode` 与 `--repair`
  - 是否存在硬编码路径
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 6. sync

- `Governance/specs/spiral-s0a/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 7. 失败回退

- 若入口不可执行或配置注入不一致：状态置 `blocked`，仅修复 S0a，不推进 S0b。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S0a 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`

---

## 历史债务状态（2026-02-27 清零同步）

| 债务 ID | 类型 | 说明 | 处理策略 |
|---|---|---|---|
| TD-DA-009 | 已清偿（2026-02-27） | Enum 设计-实现对齐已通过 schema 审计 | 证据：`artifacts/spiral-s0s2/revalidation/20260227_104537/enum_contract_audit.json` |
| TD-DA-010 | 已清偿（2026-02-27） | API 口径已按 ARCH-DECISION-001 对齐 Pipeline 主口径 | 证据：各模块 `*-api.md` v4.0.0 |
| TD-DA-011 | 已清偿（2026-02-27） | Integration 双模式语义已通过顺序重验与回归测试 | 证据：`s0a_s2c_revalidation_summary.md` + `test_algorithm_semantics_regression.py` |
| TD-ARCH-001 | 治理基线（非债务） | 架构决策已固化并落地 | 约束：后续变更不得新增口径漂移 |

