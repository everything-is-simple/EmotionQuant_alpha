# 债务清理卡 C — 滞留债务清理

**状态**: Planned  
**更新时间**: 2026-02-25  
**触发**: debts.md 积压债务复核  
**定位**: 收敛历史遗留 P1/P2 债务，降低长期维护风险  
**预估工作量**: 2 圈（分批执行）  
**前置**: 卡 A/B 完成后执行，或随相关圈位自然消化

---

## 1. 目标

将 debts.md 中非结构性、但持续积压的债务集中清理：
- 唯一 P1：bridge source_missing 修复
- Validation 丰富 API 推进（从 1→3 核心接口）
- DESIGN_TRACE 覆盖扩展到全仓核心代码
- Legacy "Phase" 措辞清理
- AKShare/BaoStock 兜底预留
- Validation 生产级校准推进

---

## 2. Scope

### In Scope

| 序号 | 债务 ID | 优先级 | 任务 | 预估 |
|---|---|---|---|---|
| 1 | TD-S2C-019 | P1 | 修复 `recommend --with-validation-bridge` 在 Parquet 单日覆盖场景误报 `source_missing` | 45 min |
| 2 | TD-DA-006 | P2 | Validation API 扩展：新增 `validate_factor()`/`evaluate_candidate()` 独立入口（从 12 接口中挑 2-3 核心） | 120 min |
| 3 | TD-GOV-012 | P2 | DESIGN_TRACE 标记扩展到 Data/Analysis/GUI 层核心文件 | 30 min |
| 4 | TD-S0-005 | P2 | 全仓搜索 `Phase` 历史措辞并替换为 Spiral 口径 | 20 min |
| 5 | TD-S3A-015 | P2 | AKShare/BaoStock fetcher 适配器骨架（不要求全量实现，仅接口 + 1 个 API 验证） | 60 min |
| 6 | TD-S0-002 | P2 | Validation 生产级真实收益口径：至少完成 IC/ICIR 与真实 pct_chg 序列的校准基线 | 90 min |

### Out Scope

- AKShare 全量 API 覆盖（仅骨架）
- Validation 12 接口全部实现（仅核心 2-3 个）

---

## 3. 执行顺序（建议分两批）

### 批次 1（P1 优先 + 快速清理）

| 轮次 | 任务 | 依赖 |
|---|---|---|
| 第 1 轮 | TD-S2C-019: bridge source_missing 修复 | 无 |
| 第 2 轮 | TD-S0-005: Phase 措辞清理 | 无 |
| 第 3 轮 | TD-GOV-012: DESIGN_TRACE 扩展 | 无 |

### 批次 2（深度实现）

| 轮次 | 任务 | 依赖 |
|---|---|---|
| 第 4 轮 | TD-DA-006: Validation API 扩展 | 卡 A（helpers + enums） |
| 第 5 轮 | TD-S0-002: Validation 生产级校准 | 第 4 轮 |
| 第 6 轮 | TD-S3A-015: AKShare 适配器骨架 | 无 |

---

## 4. run

```bash
pytest tests/ -q
python -m scripts.quality.local_quality_check --contracts --governance
```

---

## 5. test

```bash
pytest tests/unit/ -v --tb=short
```

---

## 6. 验收标准

- TD-S2C-019: `recommend --with-validation-bridge` 在 Parquet 单日覆盖场景不再误报
- TD-DA-006: `validate_factor()` 可独立调用并产出 IC/ICIR 报告
- TD-GOV-012: `grep -r DESIGN_TRACE src/` 覆盖所有核心模块（≥10 个文件）
- TD-S0-005: `grep -ri "phase" docs/ Governance/` 无非归档目录中的遗留 Phase 措辞
- TD-S3A-015: AKShare fetcher 通过至少 1 个 API 的冒烟测试
- TD-S0-002: IC 校准基线产物存在且可审计

---

## 7. 失败回退

- 任一深度实现未完成：标记为"部分清偿"，剩余部分回登 debts.md

---

## 8. 关联

- 债务登记: `Governance/record/debts.md`
- bridge 相关: `src/pipeline/recommend.py`
- Validation 设计: `docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md`
- Data 设计: `docs/design/core-infrastructure/data/data-fetcher-design.md`

---

## 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-02-25 | 首版：定义卡 C（bridge 修复 + Validation API + DESIGN_TRACE + legacy + AKShare + 校准） |
