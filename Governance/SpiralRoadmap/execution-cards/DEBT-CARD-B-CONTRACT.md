# 债务清理卡 B — 契约补齐

**状态**: Completed  
**更新时间**: 2026-02-25  
**触发**: 设计-代码对齐审计 P2 债务（TD-DA-001/005/007）  
**定位**: 补齐设计契约中已定义但代码未实现的接口与字段  
**预估工作量**: 1 圈（~3-5 天）  
**前置**: 卡 A 完成后执行

---

## 1. 目标

- PAS discount 字段落库，提升诊断/回测解释力
- Calculator/Repository 接口试点（MSS + IRS），为后续全模块推广验证模式
- 补齐 Integration `dual_verify`/`complementary` 模式设计文档
- 当前收口口径：TD-DA-001/005/007 全部完成

---

## 2. Scope

### In Scope

| 序号 | 债务 ID | 任务 | 影响范围 |
|---|---|---|---|
| 1 | TD-DA-005 | PAS `liquidity_discount`/`tradability_discount` 写入 `stock_pas_daily` 输出（已完成） | PAS pipeline + 下游 Integration |
| 2 | TD-DA-001 | MSS 模块试点 Calculator/Repository 接口抽象（`MssCalculator` + `MssRepository`），IRS 模块跟进（已完成） | MSS/IRS |
| 3 | TD-DA-007 | 在 `docs/design/core-algorithms/integration/integration-algorithm.md` 补充 `dual_verify`/`complementary` 模式正式定义（已完成） | 设计文档 |

### Out Scope

- Validation 丰富 API（卡 C）
- 全模块 Calculator/Repository 推广（视试点结论决定）

---

## 3. 执行顺序

| 轮次 | 任务 | 预估 | 依赖 |
|---|---|---|---|
| 第 1 轮 | TD-DA-005: PAS discount 持久化（已完成） | 30 min | 无 |
| 第 2 轮 | TD-DA-001: MSS Calculator/Repository 试点（已完成） | 90 min | 卡 A（Enum + helpers） |
| 第 3 轮 | TD-DA-001: IRS Calculator/Repository 跟进（已完成） | 60 min | 第 2 轮 |
| 第 4 轮 | TD-DA-007: Integration 模式文档补齐（已完成） | 30 min | 无 |

---

## 4. run

```bash
pytest tests/ -q
python -m scripts.quality.local_quality_check --contracts --governance
```

---

## 5. test

```bash
pytest tests/unit/algorithms/pas/ -v --tb=short
pytest tests/unit/algorithms/mss/ -v --tb=short
pytest tests/unit/algorithms/irs/ -v --tb=short
```

---

## 6. artifact

- `stock_pas_daily` 表新增 `liquidity_discount`/`tradability_discount` 列（已落地）
- `src/algorithms/mss/calculator.py` + `src/algorithms/mss/repository.py`（新建，试点）
- `src/algorithms/irs/calculator.py` + `src/algorithms/irs/repository.py`（落地，试点）
- `docs/design/core-algorithms/integration/integration-algorithm.md` 更新 diff（已落地）

---

## 7. 验收标准

- PAS 输出 DataFrame 包含 `liquidity_discount`/`tradability_discount` 列且落库（已达成）
- MSS/IRS Calculator/Repository 接口可运行，现有测试通过
- Integration 设计文档包含 `dual_verify`/`complementary` 正式定义与验收口径（已达成）

---

## 8. 失败回退

- Calculator/Repository 试点若引入过多复杂度：回退为函数式 + 接口协议（Protocol），登记后续优化债务

---

## 9. 关联

- 债务来源: `Governance/SpiralRoadmap/execution-cards/DESIGN-ALIGNMENT-ACTION-CARD.md` §4
- 债务登记: `Governance/record/debts.md`（TD-DA-001/005/007）

---

## 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-02-25 | 卡 B 收口：TD-DA-001/005/007 全部完成；补齐 IRS Calculator/Repository 实现与测试 |
| v0.2 | 2026-02-25 | 状态同步：TD-DA-005/007 标记完成，卡 B 调整为 Active（剩余 TD-DA-001） |
| v0.1 | 2026-02-25 | 首版：定义卡 B（PAS discount + Calculator/Repository 试点 + Integration 文档） |
