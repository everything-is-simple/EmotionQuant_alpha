# Integration — 差异清单

共 19 项差异。合并自旧 P0/P1/P2/P3 四份文件。

---

## P0 算法语义偏差（7 项）

### INT-P0-1：strength_factor（多数一致约束）未应用于 final_score

- **设计**: consistency=divergent → `final_score *= 0.8`，partial → `*= 0.9`，见 integration-algorithm.md §5.2-§5.3
- **代码**: `_to_consistency()` 返回字符串标签后再无任何乘法操作
- **位置**: `pipeline.py:944-945`
- **实锤**: top_down_score=72 + divergent → 设计 72×0.8=57.6(HOLD)，代码仍为 72(BUY)

### INT-P0-2：IRS 方向映射来源错误（rotation_status vs recommendation）

- **设计**: IRS 方向从 `rotation_status`（IN/OUT/HOLD）映射，见 integration-algorithm.md §4.1
- **代码**: 从 `recommendation`（STRONG_BUY/BUY/HOLD/SELL/AVOID）映射，且查询 SQL 未读 rotation_status
- **位置**: `pipeline.py:878`, `_direction_from_recommendation():239-245`, 查询 `line 633`
- **实锤**: rotation_status=IN + recommendation=HOLD → 设计判涨(+1)，代码判中性(0)

### INT-P0-3：仓位计算缺失三类调整因子

- **设计**: `position = base × mss_factor × irs_factor × pas_factor × cap`，见 integration-algorithm.md §6.1
  - mss_factor = `1 - |temperature-50|/100`（连续函数）
  - irs_factor: 超配×1.2, 标配×1.0, 减配×0.7, 回避×0.3
  - pas_factor: S×1.2, A×1.0, B×0.7, C/D×0.3
- **代码**: 仅二值判断（温度极端时固定 ×0.85，否则 ×1.0），IRS/PAS 因子完全缺失
- **位置**: `pipeline.py:948-954`
- **实锤**: C 级股在回避行业 → 设计 ×0.3×0.3=×0.09，代码无缩减

### INT-P0-4：单股仓位上限（per-grade cap）未实现

- **设计**: S 级 max 10%，A 级 max 8%，B 级 max 5%，C/D 级 max 3%，见 integration-algorithm.md §6.2
- **代码**: 无 per-grade cap 逻辑
- **位置**: `pipeline.py` 主循环

### INT-P0-5：neutrality 未加权聚合

- **设计**: `neutrality = max(w_mss×mss_neutrality, w_irs×irs_neutrality, w_pas×pas_neutrality)`，见 integration-algorithm.md §7
- **代码**: `neutrality = 1.0 - abs(mss_temperature - 50.0) / 50.0`（仅从 MSS 温度计算）
- **位置**: `pipeline.py:957`
- **实锤**: IRS/PAS 的 neutrality 完全被忽略；查询中也未读取这两个字段

### INT-P0-6：IRS 行业分协同调整缺失

- **设计**: allocation_advice 为"超配"时 PAS 评分 ×1.05，"回避"时 ×0.85，见 integration-algorithm.md §5.3
- **代码**: 有 irs_avoid 的 0.85 折扣（line 895），但无超配 boost；且折扣应用位置可能不正确
- **位置**: `pipeline.py:895`

### INT-P0-7：complementary 模式评分来源偏差

- **设计**: `final_score = td_result.final_score`（TD 做风控框架），BU 仅影响选股排序
- **代码**: `final_score = td*0.40 + bu*0.60`（BU 权重反而更高，主导评分）
- **位置**: `pipeline.py:937-942`
- **实锤**: td=50(HOLD) + bu=85(BUY) → 设计 50(HOLD)，代码 71(BUY)

---

## P1 模式语义偏差（3 项）

### INT-P1-1：dual_verify 模式缺少 consensus_factor 调整

- **设计**: 弱共识 ×0.9，矛盾 ×0.7 + HOLD 上限，双中性 HOLD 上限，见 §10.5.1
- **代码**: 仅矛盾时设 recommendation=HOLD，final_score 不变
- **位置**: `pipeline.py:931-936`

### INT-P1-2：dual_verify position_size 语义偏差

- **设计**: `min(td_result.position_size, bu_result.position_size)`
- **代码**: `min(cycle_cap_td, cycle_cap_bu)`（取的是周期上限而非实际仓位）
- **位置**: `pipeline.py:936`

### INT-P1-3：complementary 模式 BU 权重倒挂（同 P0-7 的延伸）

- 设计中 complementary = "TD 定框架 + BU 定选股"，代码中 BU 60% 权重反而主导评分，本质上退化为偏 BU 的 dual_verify

---

## P2 筛选排序与数据契约（5 项）

### INT-P2-1：推荐列表缺少 final_score≥55 主门槛筛选

- **设计**: `final_score >= 55` 为入选条件，见 §9.1
- **代码**: `_apply_recommendation_limits()` 无此筛选
- **位置**: `pipeline.py:388-415`

### INT-P2-2：推荐列表排序规则不同

- **设计**: 第 1 维 final_score 降序 → 第 2 维 opportunity_score → 第 3 维 allocation_advice
- **代码**: 第 1 维 grade_priority(S>A>B) → 第 2 维 recommendation_priority → 第 3 维 final_score → 第 4 维 position_size
- **位置**: `pipeline.py:394-398`

### INT-P2-3：代码额外的 RR<1.0 硬过滤不在设计中

- **代码**: `risk_reward_ratio < 1.0` 直接跳过（line 858-861），设计筛选条件无此规则
- **性质**: 从风控角度合理，建议反向补入设计

### INT-P2-4：IRS cold_start/stale 回退不强制 baseline 权重

- **设计**: cold_start/stale 时返回 `BASELINE_WEIGHTS`，见 §3.1
- **代码**: 仅设置 WARN + position_cap=0.80，未重置权重
- **位置**: `pipeline.py:774-781`

### INT-P2-5：Gate fallback 语义差异

- **设计**: gate_status 缺失时回退为 WARN 并使用 baseline 权重
- **代码**: gate_status 缺失时回退为 PASS 并使用 baseline 权重

---

## P3 数据模型与字段差异（4 项）

### INT-P3-1：输出表列不一致

- 设计有/代码无：position_cap_ratio, tradability_pass_ratio, impact_cost_bps, candidate_exec_pass, stock_name
- 代码有/设计无：t1_restriction_hit, limit_guard_result, session_guard_result, contract_version

### INT-P3-2：输入字段读取不完整

- MSS 未读：position_advice, neutrality
- IRS 未读：rotation_status, sample_days, neutrality（额外读了设计无的 recommendation）
- PAS 未读：stock_name, industry_code, entry/stop/target, neutrality

### INT-P3-3：Regime 参数系统完全未实现

- 设计定义了 RegimeParameters dataclass + risk_on/neutral/risk_off 三档 profile
- 代码全部硬编码字面量，无动态切换

### INT-P3-4：信息流文档组件依赖图已过时

- 描述了不存在的 OOP 架构（IntegrationController/Service/Engine 等），实际为单函数 Pipeline
