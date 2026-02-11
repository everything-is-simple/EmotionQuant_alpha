# EmotionQuant 文档检查报告 — R11

**检查工具**: Warp (claude 4.6 opus max)
**检查时间**: 2026-02-11
**检查范围**: `docs/design/core-algorithms/validation/`（4 文件）
**累计轮次**: R1–R11（R1–R10 已修复 41 项）

---

## 检查范围

| # | 文件 | 结果 |
|---|------|------|
| 1 | factor-weight-validation-algorithm.md | ✅ Clean Pass |
| 2 | factor-weight-validation-api.md | ✅ Clean Pass |
| 3 | factor-weight-validation-data-models.md | ⚠️ 见 P3-R11-02 |
| 4 | factor-weight-validation-information-flow.md | ⚠️ 见 P2-R11-01 |

---

## 问题清单

### P2-R11-01 | info-flow §4.1：因子→字段映射与 MSS 算法不对齐

**位置**: factor-weight-validation-information-flow.md §4.1 L60-61

**现状**:
- `mss_market_coefficient` 字段列写的是 `yesterday_limit_up_today_avg_pct 等派生字段`
- `mss_profit_effect` 字段列写的是 `rise_count/limit_up_count 相关派生`

**MSS 算法实际公式** (mss-algorithm.md §3.1-§3.2):
- **大盘系数** (market_coefficient): `rise_count / total_stocks` → 代表字段应为 `rise_count`
- **赚钱效应** (profit_effect): `0.4×limit_up_ratio + 0.3×new_high_ratio + 0.3×strong_up_ratio` → 代表字段应为 `limit_up_count/new_100d_high_count/strong_up_count`

**问题**: 两行代表字段互串——`rise_count` 属于大盘系数而非赚钱效应；`yesterday_limit_up_today_avg_pct` 不出现在大盘系数公式中。

**修复方案**:
- L60: `mss_market_coefficient` 字段列改为 `rise_count`（上涨占比/参与度核心字段）
- L61: `mss_profit_effect` 字段列改为 `limit_up_count/new_100d_high_count/strong_up_count` 相关派生

---

### P3-R11-02 | data-models §1.6：`ValidationRunManifest` 时间戳类型注解不一致

**位置**: factor-weight-validation-data-models.md §1.6 L127-128

**现状**:
```python
started_at: str
finished_at: str
```

**DDL** (§3.5 L268-269): `started_at DATETIME NOT NULL` / `finished_at DATETIME`
**同类字段**: 同一 dataclass L131: `created_at: datetime`

**问题**: `started_at`/`finished_at` 表示时间戳，类型应为 `datetime` 以匹配 DDL 和同类字段 `created_at: datetime`。

**修复方案**: `started_at: str` → `started_at: datetime`，`finished_at: str` → `finished_at: datetime`。

---

## 统计

| 等级 | 本轮 | 累计 (R1–R11) |
|------|------|---------------|
| P1 | 0 | 1 |
| P2 | 1 | 20 |
| P3 | 1 | 21 |
| **合计** | **2 项** | **43 项** |

---

## Clean Pass 确认（2 / 4 文件）

- factor-weight-validation-algorithm.md ✅ — §3.3 门禁阈值与 `ValidationConfig` 完全对齐；§4 权重验证参数与 config 默认值一致；§5 Gate 决策矩阵逻辑完整；§6 输出 5 张表与 DDL 匹配；§6.1 桥接代码正确
- factor-weight-validation-api.md ✅ — API 签名与数据模型类型一致；`resolve_weight_plan()` 返回 `WeightPlan`（轻量桥接类型，定义于 integration-data-models.md §2.5）；`build_integration_inputs()` 返回元组与 Integration 消费契约匹配；§6 上下游契约正确

---

## 交叉验证确认

- `ValidatedFactor` 枚举 15 项 = MSS 6 + IRS 6 + PAS 3（与各模块算法文档因子体系一一对应）✓
- DDL 5 张表名与 algorithm §6 输出清单、info-flow §5 输出边界、api §4.1 持久化清单三方一致 ✓
- `WeightPlan`（Integration 侧轻量类型）vs `ValidationWeightPlan`（Validation 侧存储模型）设计意图清晰，`resolve_weight_plan()` 负责转换 ✓
- Gate 决策规则（algorithm §5）与 Integration 侧 `resolve_gate_and_weights()` 消费逻辑对齐 ✓

---

## 下一轮预告

**R12** 预计范围: `docs/design/core-infrastructure/data-layer/`（4 文件）
