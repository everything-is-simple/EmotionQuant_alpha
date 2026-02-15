# S0a 执行卡（v0.1）

**状态**: Active  
**更新时间**: 2026-02-15  
**阶段**: 阶段A（S0-S2）  
**微圈**: S0a（入口与配置）

---

## 1. 目标

- 落地统一入口 `eq`。
- 落地 `src.pipeline.main` 最小 CLI。
- 确保配置读取仅通过 `Config.from_env()` 注入。

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
```

---

## 4. artifact

- `artifacts/spiral-s0a/{trade_date}/run.log`
- `artifacts/spiral-s0a/{trade_date}/test.log`
- `artifacts/spiral-s0a/{trade_date}/cli_contract.md`
- `artifacts/spiral-s0a/{trade_date}/config_effective_values.json`

---

## 5. review

- 复盘文件：`Governance/specs/spiral-s0a/review.md`
- 必填结论：
  - 入口命令是否可复现
  - 配置注入是否仅走 `Config.from_env()`
  - 是否存在硬编码路径

---

## 6. sync

- `Governance/specs/spiral-s0a/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`

---

## 7. 失败回退

- 若入口不可执行或配置注入不一致：状态置 `blocked`，仅修复 S0a，不推进 S0b。
- 若契约/治理检查失败：必须先修复并补齐回归证据，再重跑 S0a 验收。

---

## 8. 关联

- 微圈合同：`Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
