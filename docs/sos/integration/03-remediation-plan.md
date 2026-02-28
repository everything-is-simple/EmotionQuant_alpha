# Integration — 修复方案

---

## 批次一：仓位风控修复

### INT-P0-3：实现三类仓位调整因子

**目标文件**: `src/integration/pipeline.py`

```python
# 替换 line 948-954 区域

# 1. MSS 连续温度因子
mss_factor = 1.0 - abs(mss_temperature - 50.0) / 100.0

# 2. IRS 配置因子
IRS_ALLOC_FACTOR = {"overweight": 1.2, "equal_weight": 1.0, "underweight": 0.7, "avoid": 0.3}
irs_factor = IRS_ALLOC_FACTOR.get(allocation_advice, 1.0)

# 3. PAS 等级因子
PAS_GRADE_FACTOR = {"S": 1.2, "A": 1.0, "B": 0.7, "C": 0.3, "D": 0.3}
pas_factor = PAS_GRADE_FACTOR.get(opportunity_grade, 1.0)

# 综合仓位
base_position_size = max(0.0, min(1.0, final_score / 100.0))
position_size = base_position_size * mss_factor * irs_factor * pas_factor
position_size = round(min(position_size, position_cap), 4)
```

### INT-P0-4：实现 per-grade cap

```python
GRADE_CAP = {"S": 0.10, "A": 0.08, "B": 0.05, "C": 0.03, "D": 0.03}
grade_cap = GRADE_CAP.get(opportunity_grade, 0.05)
position_size = min(position_size, grade_cap)
```

---

## 批次二：核心算法修正

### INT-P0-1：应用 strength_factor

**目标文件**: `pipeline.py`，在 line 944-945 之后

```python
STRENGTH_MAP = {"consistent": 1.0, "partial": 0.9, "divergent": 0.8}
strength_factor = STRENGTH_MAP.get(consistency, 1.0)
final_score = round(final_score * strength_factor, 4)
```

### INT-P0-2：修正 IRS 方向来源

1. 在 IRS 查询 SQL 中增加 `rotation_status` 列
2. 新增映射函数 `_direction_from_rotation_status()`：IN→bullish, OUT→bearish, HOLD→neutral
3. 替换 line 878 的调用
4. 回退：若 rotation_status 列不存在，降级使用 recommendation

### INT-P0-5：neutrality 加权聚合

1. 在 MSS/IRS/PAS 查询中补读 neutrality 字段
2. 计算：`neutrality = max(w_mss*mss_n, w_irs*irs_n, w_pas*pas_n)`

### INT-P0-6：IRS 协同调整补全

补充超配 boost：allocation_advice="overweight" 时 PAS 评分 ×1.05（已有 avoid ×0.85，需补对称的 boost）

---

## 批次三：模式修正

### INT-P0-7 + INT-P1-3：complementary 模式

```python
# 替换 line 937-942
else:  # complementary
    final_score = top_down_score  # 使用 TD 评分（设计：TD 定风控框架）
    recommendation = _to_recommendation(final_score, mss_cycle)
    # BU 的作用体现在推荐列表排序中（按 pas_score 降序）
    mode_position_cap = cycle_position_cap_top_down
```

### INT-P1-1：dual_verify consensus_factor

```python
elif resolved_integration_mode == "dual_verify":
    final_score = round((top_down_score + bottom_up_score) / 2.0, 4)
    # 计算共识因子
    td_dir = _dir_to_int(td_direction)  # +1/0/-1
    bu_dir = _dir_to_int(bu_direction)
    consensus = td_dir + bu_dir
    if abs(consensus) == 2:
        consensus_factor = 1.0
    elif abs(consensus) == 1:
        consensus_factor = 0.9
    elif td_dir != bu_dir:  # 矛盾
        consensus_factor = 0.7
    else:  # 双中性
        consensus_factor = 1.0
    final_score = round(final_score * consensus_factor, 4)
    recommendation = _to_recommendation(final_score, mss_cycle)
    if consensus_factor <= 0.7 or (td_dir == 0 and bu_dir == 0):
        recommendation = min_recommendation(recommendation, "HOLD")
```

---

## 批次四：筛选与数据契约

### INT-P2-1：补 55 分门槛

在 `_apply_recommendation_limits()` 开头：`frame = frame[frame["final_score"] >= 55.0]`

### INT-P2-4：cold_start/stale 强制回退 baseline 权重

在 cold_start/stale 分支增加 `w_mss = w_irs = w_pas = BASELINE_WEIGHT`

### INT-P2-3：RR<1.0 过滤反向补入设计

在 integration-algorithm.md §9.1 补入 `risk_reward_ratio >= 1.0` 筛选条件

### INT-P3-1~P3-4：字段对齐、Regime 参数、信息流文档

- 输出表双向补齐字段
- 输入查询补读缺失字段（rotation_status, neutrality 等）
- Regime 参数系统：提取硬编码为模块级常量，后续实现动态切换
- 信息流文档重绘为 Pipeline 架构

---

## OOP 重建目标结构

```
src/integration/
├── pipeline.py      # 编排入口
├── service.py       # IntegrationService
├── engine.py        # ScoreEngine（评分合成 + 协同调整 + 仓位计算）
├── models.py        # IntegrationInput, IntegrationResult, RegimeParameters
├── repository.py    # IntegrationRepository
├── modes/
│   ├── top_down.py      # TD 模式
│   ├── bottom_up.py     # BU 模式
│   ├── dual_verify.py   # 双验证模式
│   └── complementary.py # 互补模式
└── constraints.py   # 方向检查 + 筛选 + 限额
```
