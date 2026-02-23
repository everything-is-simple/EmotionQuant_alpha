# ROADMAP Capability Pack CP-04｜PAS（个股信号）

**文件名**: `CP-04-pas.md`  
**版本**: v6.0.2  
> ✅ 当前口径（2026-02-23）
> 本文件为当前有效能力契约（CP），用于定义输入/输出/门禁/回退。
> 本文件不承担路线主控；执行以运行事实与执行卡证据为准。
> 执行入口：`Governance/SpiralRoadmap/planA/EXECUTION-CARDS-INDEX.md` 与 `Governance/record/development-status.md`。
---

## 1. 定位

输出个股机会评分、等级、方向与执行参考字段。

---

## 2. 稳定契约

### 2.1 输入

| 输入 | 来源 | 就绪条件 | 失败处理 |
|---|---|---|---|
| `raw_daily` | CP-01 | 可读取 | P0 |
| `stock_gene_cache` | CP-01 | 字段完整 | P0 |
| `raw_stock_basic` | CP-01 | 行业映射可用 | P1 |

### 2.2 输出

| 输出 | 消费方 | 验收 |
|---|---|---|
| `stock_pas_daily` | CP-05/08/09 | score 范围合法；direction/grade 枚举合法；`risk_reward_ratio >= 1.0`（执行边界） |

---

## 3. Slice 库（按需抽取）

| Slice ID | 推荐 Spiral | 说明 | 最小闭环证据 |
|---|---|---|---|
| CP04-S1 | S2 | 评分最小版 | TopN 结果 + 测试 |
| CP04-S2 | S2/S3 | 等级/方向/执行字段 | 字段校验测试 |

---

## 4. Entry / Exit Gate

### 4.1 Entry

- CP-01 行情数据可用
- 股票与行业映射可用

### 4.2 Exit

- 单指标不得独立决策
- 输出可被 CP-05 直接消费
- 执行参考字段满足 `risk_reward_ratio >= 1.0`（`<1.0` 仅观察，不进入执行层）
- 至少 1 条 PAS 自动化测试通过

---

## 5. 风险与回退

| 场景 | 级别 | 策略 |
|---|---|---|
| 停牌或缺行情 | P1 | 跳过并标注 |
| 输入字段缺失 | P0 | 阻断 |
| `risk_reward_ratio` 异常（空值/负值/低于门槛） | P1 | 降级为观察，阻断执行层消费 |

---

## 6. 何时更新本文件

1. PAS 输入/输出字段变化
2. 等级或方向规则变化
3. 风险字段口径变化
4. 门禁变化
5. `risk_reward_ratio` 执行边界变化

---

## 7. 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v6.0.2 | 2026-02-14 | 补齐 PAS 执行边界：明确 `risk_reward_ratio >= 1.0` 为执行门槛，并同步 Exit Gate/风险/更新触发条件 |



