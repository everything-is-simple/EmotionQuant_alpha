# ROADMAP Capability Pack CP-05｜Integration（三系统集成）

**文件名**: `CP-05-integration.md`  
**版本**: v6.0.2  
> ⚠️ 历史说明（2026-02-13）
> 本文件为线性阶段能力包留档，仅供回顾历史，不作为当前路线图执行入口。
> 当前执行入口：`Governance/SpiralRoadmap/VORTEX-EVOLUTION-ROADMAP.md` 与 `Governance/SpiralRoadmap/DEPENDENCY-MAP.md`。
> 除历史纠错外，不再作为迭代依赖。
---

## 1. 定位

合成统一推荐信号，作为 CP-06/07/08/09 的唯一上游输出。

---

## 2. 稳定契约

### 2.1 输入

| 输入 | 来源 | 就绪条件 | 失败处理 |
|---|---|---|---|
| `mss_panorama` | CP-02 | 当日数据存在 | P0 |
| `irs_industry_daily` | CP-03 | 当日数据存在 | P0 |
| `stock_pas_daily` | CP-04 | 当日数据存在；`risk_reward_ratio` 字段可解析 | P0 |
| `validation_gate_decision` | CP-10 | Gate 非 FAIL 且 `contract_version="nc-v1"` | FAIL 或版本不兼容阻断 |
| `validation_weight_plan` | CP-10 | 对应 `plan_id` 可解析 | P0 |

### 2.2 输出

| 输出 | 消费方 | 验收 |
|---|---|---|
| `integrated_recommendation` | CP-06/07/08/09 | 字段完整且可追溯；`contract_version="nc-v1"` |

---

## 3. Slice 库（按需抽取）

| Slice ID | 推荐 Spiral | 说明 | 最小闭环证据 |
|---|---|---|---|
| CP05-S1 | S2 | baseline 集成输出 | 集成表 + 测试 |
| CP05-S2 | S3 | 风险约束接入 | 约束测试 |
| CP05-S3 | S4 | 阈值校准 | 校准报告 |

---

## 4. Entry / Exit Gate

### 4.1 Entry

- CP-02/03/04 输出就绪
- 验证 Gate 非 FAIL
- 契约版本兼容：`contract_version = "nc-v1"`

### 4.2 Exit

- baseline 与候选权重对比证据齐全
- 输出可被 CP-06/07 直接消费
- 执行候选满足 `risk_reward_ratio >= 1.0`（`<1.0` 已过滤）
- 至少 1 条集成自动化测试通过

---

## 5. 风险与回退

| 场景 | 级别 | 策略 |
|---|---|---|
| 任一核心输入缺失 | P0 | 阻断 |
| 权重候选验证失败 | P1 | 回退 baseline |
| `contract_version` 不兼容 | P0 | 阻断并提示契约升级/迁移 |

---

## 6. 何时更新本文件

1. 集成输入/输出字段变化
2. 权重策略变化
3. Gate 规则变化
4. 回退策略变化
5. `contract_version` 或 `risk_reward_ratio` 执行边界变化

---

## 7. 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v6.0.2 | 2026-02-14 | 补齐 Integration 契约边界：输入 Gate 需 `contract_version=nc-v1`；输出携带契约版本；明确 `risk_reward_ratio >= 1.0` 执行过滤 |



