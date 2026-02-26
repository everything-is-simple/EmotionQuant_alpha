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

## 历史债务挂载（2026-02-26 独立审计）

| 债务 ID | 类型 | 说明 | 处理策略 |
|---|---|---|---|
| TD-DA-009 | 历史债务（未清偿） | Enum 设计-实现对齐缺口（类名/成员/缺失枚举） | 执行本卡时必须在 gate_report.md 给出 Enum 对齐结论（resolved/deferred） |
| TD-DA-010 | 历史债务（后续） | Calculator/Repository 与设计 API 存在方法/签名差距（卡 B 仅完成试点） | 执行本卡时按 ARCH-DECISION-001 二选一：继续对齐实现或下修设计契约 |
| TD-DA-011 | 历史债务（后续） | Integration dual_verify/complementary 与设计语义存在冲突（共识因子/落库字段/权重语义） | 执行本卡时输出语义对齐结论并同步 docs + tests + debts |
| TD-ARCH-001 | 架构决策债务 | OOP 设计口径与 Pipeline 实现口径并存 | 执行本卡时引用 ARCH-DECISION-001，禁止新增口径漂移 |

