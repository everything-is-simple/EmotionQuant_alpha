# MSS — 修复方案

---

## 批次一：information-flow 文档修订

### MSS-P0-1 修复：重写趋势判定章节

**目标文件**: `docs/design/core-algorithms/mss/mss-information-flow.md` §2.6 Step 6

重写为完整的趋势判定逻辑：
1. **正式方法**（≥8日样本）：EMA(temperature, 3) vs EMA(temperature, 8) 交叉 + 5日斜率 + 动态 trend_band = max(0.8, 0.15×std(20))
2. **冷启动回退**（3-7日）：3日严格递增/递减，标记 trend_quality=cold_start
3. **极端退化**（<3日）：sideways + trend_quality=degraded

### MSS-P0-2 修复：重写异常处理章节

**目标文件**: `docs/design/core-algorithms/mss/mss-information-flow.md` §6

**删除"使用前一日数据"表述**，替换为与 mss-algorithm.md §10.5 一致的异常处理矩阵：
- stale_days ≤ 3 → 允许计算，标记 data_quality=stale
- stale_days > 3 → 抛出 DataNotReadyError，阻断主流程
- total_stocks ≤ 0 → 回退中性分 50
- mean/std 缺失 → 该因子回退中性分 50
- 任一必备字段缺失 → 拒绝计算

### MSS-P0-3 修复：重绘组件架构图

**目标文件**: `docs/design/core-algorithms/mss/mss-information-flow.md` §3

替换为实际 Pipeline 架构：
```
run_mss_scoring() [pipeline.py — 编排入口]
  ├→ DuckDB 加载 market_snapshot
  ├→ calculate_mss_score() [engine.py — 纯计算]
  │     内含：因子计算 + Z-Score + 加权温度 + 趋势 + 周期
  ├→ 持久化到 DuckDB mss_panorama 表
  └→ 写出 artifacts（JSON/Parquet）

MssCalculator / MssRepository [calculator.py, repository.py]
  → Protocol 薄封装，TD-DA-001 试点，非主链调用路径
```

---

## 批次二：代码防御性补强

### MSS-P1-2 修复：补输入验证

**目标文件**: `src/algorithms/mss/engine.py`

在 `calculate_mss_score()` 入口或 `MssInputSnapshot.from_record()` 中增加验证：

```python
def _validate_mss_input(snap: MssInputSnapshot) -> None:
    """设计 §10.1 输入约束检查"""
    if snap.total_stocks <= 0:
        raise ValueError(f"total_stocks must be > 0, got {snap.total_stocks}")
    if not (0 <= snap.rise_count <= snap.total_stocks):
        raise ValueError(f"rise_count {snap.rise_count} out of range [0, {snap.total_stocks}]")
    if snap.rise_count + snap.fall_count > snap.total_stocks:
        raise ValueError("rise_count + fall_count exceeds total_stocks")
    if not (0 <= snap.limit_up_count <= snap.touched_limit_up):
        raise ValueError("limit_up_count exceeds touched_limit_up")
    # ratio 字段范围检查
    for field in ['rise_ratio', 'fall_ratio']:
        val = getattr(snap, field, None)
        if val is not None and not (0.0 <= val <= 1.0):
            raise ValueError(f"{field} must be in [0, 1], got {val}")
```

### MSS-P2-1 修复：返回类型注解

**目标文件**: `src/algorithms/mss/engine.py:462`

```python
# 修改前
def calculate_mss_score(...) -> MssScoreResult:
# 修改后
def calculate_mss_score(...) -> MssPanorama:
```

---

## 批次三：数据模型文档对齐

### MSS-P2-2 修复：更新数据模型文档

**目标文件**: `docs/design/core-algorithms/mss/mss-data-models.md`

1. §2.1 输入模型 `MssMarketSnapshot` 补充 data_quality/stale_days/source_trade_date 三个质量字段
2. §3.1 输出模型 `MssPanorama` 补充 mss_score(deprecated)/data_quality/stale_days/source_trade_date/contract_version/created_at
3. 标注命名约定：代码使用 `mss_` 前缀（如 mss_temperature）以避免存储层字段名冲突

---

## 批次四：功能完善

### MSS-P1-1 修复：Z-Score Baseline 机制

**目标文件**: `src/algorithms/mss/engine.py` + 新增 baseline 模块

完整实现设计 §7.1 的 baseline 机制：
1. 启动时加载 `${DATA_PATH}/config/mss_zscore_baseline.parquet`
2. 若 parquet 不存在，回退到硬编码 DEFAULT_FACTOR_BASELINES（当前行为）
3. 每日收盘后，按滚动窗口（默认 120 日）增量更新 mean/std
4. 更新后写回 parquet，记录 sample_start/sample_end/updated_at

### MSS-P3-1 修复：预警规则实现

按设计 §9 实现 4 种预警：
- 过热预警：temperature > threshold_high 且 trend=up
- 过冷预警：temperature < threshold_low 且 trend=down
- 尾部活跃：extreme_factor 超阈值
- 趋势背离：温度方向与大盘指数方向相反

### MSS-P3-2 ~ P3-5 修复

- PositionAdvice 枚举：加入 `src/models/enums.py`
- extreme_direction_bias 阈值：文档统一为 1e-12
- trend_quality 分级：文档补充 degraded/normal 描述
- yesterday_limit_up_today_avg_pct：补入 MssInputSnapshot（默认 0.0，观测字段）

---

## OOP 重建目标结构

```
src/algorithms/mss/
├── pipeline.py      # 编排入口
├── service.py       # MssService（对外接口）
├── engine.py        # MssEngine（六因子计算+温度合成+趋势+周期）
├── models.py        # MssInputSnapshot, MssPanorama, MssAlert
├── repository.py    # MssRepository（DuckDB 读写）
├── baseline.py      # Z-Score Baseline 管理（加载+滚动更新）
└── alert.py         # 预警规则引擎
```
