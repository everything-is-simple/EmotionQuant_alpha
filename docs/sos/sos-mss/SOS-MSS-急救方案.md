# SOS — MSS 系统代码与核心设计差异急救方案

**审计日期**: 2026-02-27
**审计范围**: `src/algorithms/mss/` 全部代码 vs `docs/design/core-algorithms/mss/` 全部设计文档
**审计方法**: 逐公式、逐字段、逐流程独立比对

---

## 一、审计结论总览

| 严重等级 | 数量 | 说明 |
|---------|------|------|
| P0 危险（设计文档内部矛盾） | 3 处 | `mss-information-flow.md` 三处与算法文档/代码直接冲突 |
| P1 重要（代码与设计不一致） | 2 处 | Z-Score baseline 机制缺失、输入验证远松于设计 |
| P2 中等（代码与设计不一致） | 2 处 | 返回类型注解错误、数据模型字段缺失 |
| P3 低优（命名/枚举/预警） | 5 处 | 可控，但应有明确记录 |

**总计 12 处差异，其中 5 处（P0+P1）需要紧急处理。**

---

## 二、P0 危险项：设计文档内部矛盾（必须立即修订）

### P0-1: information-flow 趋势判定与算法文档矛盾

**问题位置**:
- `mss-information-flow.md` §2.6 Step 6（第 197-201 行）
- 对标: `mss-algorithm.md` §5.4（第 336-354 行）
- 对标: `engine.py` `_detect_trend_and_quality()`（第 330-361 行）

**现状**:
information-flow 描述的趋势判定方法：
```
趋势判断（需至少3日历史）
- 严格递增（T-2 < T-1 < T）→ up
- 严格递减（T-2 > T-1 > T）→ down
- 其他 → sideways
```

算法文档与代码的实际方法：
```
正式方法（≥8日样本）:
  ema_short = EMA(temperature, 3)
  ema_long  = EMA(temperature, 8)
  slope_5d  = (temperature[t] - temperature[t-5]) / 5
  trend_band = max(0.8, 0.15 × std(temperature, 20))
  up:   ema_short > ema_long AND slope_5d >= +trend_band
  down: ema_short < ema_long AND slope_5d <= -trend_band

冷启动回退（<8日）:
  3日单调方法（即 information-flow 描述的版本）
```

**问题实质**: information-flow 把冷启动的回退方案当成了正式方案来描述，遗漏了 EMA+slope+trend_band 整套正式趋势判定逻辑。这会误导任何只看 information-flow 的读者。

**急救方案**: 重写 §2.6 Step 6 趋势判断段落，对齐 `mss-algorithm.md` §5.4，包含：
1. 正式方法（EMA 交叉 + 5日斜率 + 动态 trend_band）
2. 冷启动回退（<8日用 3日单调，标记 cold_start）
3. 极端退化（<3日，sideways + degraded）

---

### P0-2: information-flow 异常处理与算法文档直接冲突

**问题位置**:
- `mss-information-flow.md` §6.1（第 388 行）
- 对标: `mss-algorithm.md` §10.5（第 504-516 行）
- 对标: `engine.py` `calculate_mss_score()`（第 456-608 行）

**现状**:
information-flow 写的：
```
| 数据缺失 | total_stocks < 1000 | 使用前一日数据 |
```

算法文档明确禁止的：
```
强制约束：
- 不允许沿用上一交易日 temperature/cycle/trend 作为兜底输出。
- 所有降级都必须可追溯（日志或质量字段）。
```

代码的实际行为：
- `total_stocks <= 0` → 回退中性分 50（不使用前一日数据）
- `stale_days > 3` → 抛出 `DataNotReadyError` 阻断（不使用前一日数据）

**问题实质**: "使用前一日数据"这个策略被算法文档明确禁止，代码也从未实现。information-flow 此处与系统的核心安全约束直接冲突。如果有人按 information-flow 来实现新功能或做审核，会引入被禁止的行为。

**急救方案**: 重写 §6 异常处理段落，与 `mss-algorithm.md` §10.5 的异常处理矩阵完全对齐：

| 场景 | 处理策略 | 允许执行 |
|------|----------|----------|
| stale_days ≤ 3 | 允许计算，打 data_quality=stale 标记 | 是 |
| stale_days > 3 | 抛出 DataNotReadyError，阻断主流程 | 否 |
| total_stocks ≤ 0 | 回退中性分 50，记录降级 | 是（降级） |
| mean/std 缺失 | 该因子回退中性分 50 | 是 |
| 趋势输入异常 | cycle=unknown + position_advice=0%-20% | 是（降级） |
| 任一必备字段缺失 | 拒绝计算 | 否 |

**明确删除"使用前一日数据"这个表述。**

---

### P0-3: information-flow 组件架构图与实际架构不符

**问题位置**:
- `mss-information-flow.md` §3（第 230-262 行）
- 对标: `mss-api.md` v4.0.0（第 9-13 行）
- 对标: 实际代码架构

**现状**:
information-flow 画的组件依赖图：
```
MssController → MssService → MssEngine + MssRepository + MssAlertService
MssEngine → MssFactorCalculator → MssNormalizer + MssCycleDetector → MssTrendAnalyzer
```

实际代码架构（mss-api.md 已更新确认）：
```
run_mss_scoring()  [pipeline.py — 编排入口]
  └→ calculate_mss_score()  [engine.py — 纯计算函数]
       内含：因子计算 + Z-Score归一化 + 加权温度 + 趋势检测 + 周期判定

MssCalculator / MssRepository  [calculator.py, repository.py — Protocol 薄封装，非主链]
```

不存在的类：`MssController`、`MssService`、`MssAlertService`、`MssFactorCalculator`、`MssNormalizer`、`MssCycleDetector`、`MssTrendAnalyzer`（均为 information-flow 虚构）。

**问题实质**: 组件依赖图描绘了一个从未实现的 OOP 架构。`mss-api.md` v4.0.0 已在 2026-02-26 更新为 Pipeline 模式，但 information-flow 未同步。

**急救方案**:
1. 重绘 §3 组件依赖图，反映 Pipeline 实际架构
2. 新架构图需体现：`run_mss_scoring()` → DuckDB 加载 → `calculate_mss_score()` → 持久化 + artifacts
3. 将 `MssCalculator`/`MssRepository` 标注为"TD-DA-001 试点薄封装，非主链调用路径"

---

## 三、P1 重要项：代码与设计不一致（应尽快处理）

### P1-1: Z-Score Baseline 加载机制完全缺失

**问题位置**:
- `mss-algorithm.md` §7.1（第 407-418 行）
- `engine.py`（第 46-53 行）

**设计规定**:
```
参数文件：${DATA_PATH}/config/mss_zscore_baseline.parquet
字段：factor_name, mean, std, sample_start, sample_end, updated_at

- 首次部署：使用离线 baseline 文件（2015-2025）初始化 mean/std
- 热启动：每日收盘后按滚动窗口（默认 120 日）增量更新统计参数
- 冷启动兜底：若某因子缺失 mean/std，直接返回 50（中性分）
```

**代码实际**:
```python
DEFAULT_FACTOR_BASELINES: dict[str, tuple[float, float]] = {
    "market_coefficient": (0.50, 0.20),
    "profit_effect": (0.08, 0.05),
    "loss_effect": (0.08, 0.05),
    "continuity_factor": (0.35, 0.20),
    "extreme_factor": (0.05, 0.03),
    "volatility_factor": (0.08, 0.05),
}
```

**差异分析**:
- ❌ 没有 parquet 文件加载
- ❌ 没有滚动窗口在线更新
- ✅ 冷启动兜底有（`_zscore_normalize` 在 `std <= 0` 时返回 50）
- 当前永远使用硬编码常量，等同于永远处于"冷启动兜底"状态

**风险评估**: 硬编码 baseline 意味着所有 Z-Score 归一化都基于固定参数。如果真实市场统计特征偏离这些硬编码值，因子得分的分布会系统性偏移。短期可接受，长期是真实风险。

**急救方案（二选一）**:
- **方案 A（对齐代码到文档）**: 实现 parquet baseline 加载 + 滚动窗口更新。工作量较大。
- **方案 B（对齐文档到代码）**: 在 `mss-algorithm.md` §7.1 中明确标注"当前阶段使用硬编码默认 baseline，热启动为 Phase-2 目标"，并在设计中增加"实现状态"标记。工作量很小。

**建议**: 采用方案 B 作为急救，同时登记技术债，在后续迭代中实现方案 A。

---

### P1-2: 输入验证远松于设计的"零容忍"约束

**问题位置**:
- `mss-algorithm.md` §10.1（第 467-480 行）
- `engine.py` `calculate_mss_score()`（第 456-608 行）与 `MssInputSnapshot.from_record()`（第 196-232 行）

**设计的"零容忍"约束清单与代码执行情况**:

| 设计约束 | 代码状态 | 差异 |
|---------|---------|------|
| `total_stocks > 0` | 回退中性分 50，不抛错 | ⚠️ 设计说零容忍，代码做降级 |
| `0 ≤ rise_count ≤ total_stocks` | 不检查 | ⚠️ 未实现 |
| `rise_count + fall_count ≤ total_stocks` | 不检查 | ⚠️ 未实现 |
| `0 ≤ limit_up_count ≤ touched_limit_up` | 不检查 | ⚠️ 未实现 |
| 所有 ratio ∈ [0, 1] | 不检查 | ⚠️ 未实现 |
| `stale_days ≤ 3` 约束 | ✅ `DataNotReadyError` | ✅ 已实现 |
| `strong_up/down` 须分板块归一 | 由 L2 快照提供，engine 不校验 | 信任上游 |
| 任一必备字段缺失 → `ValueError` | `_to_int/_to_float` 默认返回 0 | ⚠️ 静默吞零 |

**风险评估**: 如果上游 L2 `market_snapshot` 出现脏数据（如 `rise_count > total_stocks` 或 `limit_up_count > touched_limit_up`），MSS 会静默产出不合理的因子值，而不是像设计预期那样阻断并报错。

**急救方案（二选一）**:
- **方案 A（代码补检查）**: 在 `calculate_mss_score()` 入口或 `MssInputSnapshot.from_record()` 中增加 §10.1 所列的断言检查。
- **方案 B（文档降级约束）**: 在 §10.1 中将部分约束从"零容忍"降级为"advisory（建议检查，当前依赖上游保证）"，并标注实现状态。

**建议**: 对"必备字段缺失"场景补实现（方案 A），其余约束降级为 advisory 并登记债务（方案 B）。

---

## 四、P2 中等项

### P2-1: `calculate_mss_score` 返回类型注解错误

**问题位置**: `engine.py` 第 462 行

**现状**:
```python
def calculate_mss_score(...) -> MssScoreResult:
```
`MssScoreResult` 在 `engine.py` 中未定义（未 import，也无本地定义）。实际返回 `MssPanorama`。`MssScoreResult = MssPanorama` 仅在 `pipeline.py` 第 28 行定义为别名。

**问题实质**: 静态类型检查（mypy/pyright）会在 `engine.py` 报 `NameError`。设计文档 `mss-api.md` §2.2 明确标注返回类型为 `MssPanorama`。

**急救方案**: 将 `engine.py:462` 的 `-> MssScoreResult` 改为 `-> MssPanorama`。一行改动。

---

### P2-2: 数据模型字段差异 — 文档未反映实际

**问题位置**: `mss-data-models.md` §2.1 / §3.1 vs `engine.py` `MssInputSnapshot` / `MssPanorama`

**输入模型差异**:

| 字段 | 设计 `MssMarketSnapshot` | 代码 `MssInputSnapshot` |
|------|-------------------------|------------------------|
| `data_quality` | ❌ 缺失 | ✅ 存在（用于 stale 判断） |
| `stale_days` | ❌ 缺失 | ✅ 存在（用于 DataNotReadyError） |
| `source_trade_date` | ❌ 缺失 | ✅ 存在 |
| `yesterday_limit_up_today_avg_pct` | ✅ 存在 | ❌ 缺失 |
| 类名 | `MssMarketSnapshot` | `MssInputSnapshot` |

> 注：`mss-algorithm.md` §10.1 提到了 `data_quality/stale_days/source_trade_date` 这三个质量字段，但 `mss-data-models.md` 的 `MssMarketSnapshot` dataclass 定义中未包含它们。

**输出模型差异**:

| 字段 | 设计 `MssPanorama` | 代码 `MssPanorama` |
|------|-------------------|-------------------|
| `mss_score`（deprecated） | ❌ | ✅ 存在 |
| `data_quality` | ❌ | ✅ 存在 |
| `stale_days` | ❌ | ✅ 存在 |
| `source_trade_date` | ❌ | ✅ 存在 |
| `contract_version` | ❌ | ✅ 存在 |
| `created_at` | ❌ | ✅ 存在 |
| 字段命名 | `temperature` | `mss_temperature` |
| 字段命名 | `cycle` | `mss_cycle` |
| 字段命名 | `rank` | `mss_rank` |
| 字段命名 | `percentile` | `mss_percentile` |

**急救方案**: 更新 `mss-data-models.md`：
1. §2.1 输入模型补充 `data_quality`、`stale_days`、`source_trade_date` 三个质量字段
2. §3.1 输出模型补充 `mss_score`（标注 deprecated）、`data_quality`、`stale_days`、`source_trade_date`、`contract_version`、`created_at`
3. 类名说明：标注设计用 `MssMarketSnapshot`，代码实现为 `MssInputSnapshot`
4. 命名说明：标注代码使用 `mss_` 前缀以避免存储层字段名冲突

---

## 五、P3 低优项（记录备查）

### P3-1: 预警规则完全未实现

`mss-algorithm.md` §9 定义了 4 种预警（过热/过冷/尾部活跃/趋势背离），`mss-data-models.md` 定义了 `mss_alert_log` 表。代码中无任何预警生成逻辑。

**建议**: 在 `mss-algorithm.md` §9 和 `mss-data-models.md` §4.3 中标注"**当前未实现，待后续迭代**"。

### P3-2: PositionAdvice 枚举未实现

`mss-data-models.md` §3.4 定义了 `PositionAdvice(Enum)`，代码中 `_position_advice_for_cycle()` 使用字符串映射，未引用枚举。

**建议**: 将 `PositionAdvice` 枚举加入 `src/models/enums.py`，或在文档中标注"代码以字符串常量实现，语义等价"。

### P3-3: extreme_direction_bias 零值防护阈值

设计: `max(extreme_factor_raw, 1e-6)` → 代码: `extreme_factor_raw <= 1e-12` 守卫后直接除。实际效果等价（极端因子为零时两种路径均输出 0.0），无功能风险。

**建议**: 无需修改。如需统一，可将文档 `1e-6` 改为与代码一致的 `1e-12` 守卫描述。

### P3-4: trend_quality 分级粒度

设计仅提及 `cold_start`（<8日），代码增加了 `degraded`（<3日或8-19日）和 `normal`（≥20日）的更细分级。

**建议**: 在 `mss-algorithm.md` §5.4 中补充完整的 trend_quality 分级逻辑。

### P3-5: yesterday_limit_up_today_avg_pct 字段缺失

设计输入模型包含此字段（标注为"兼容观测字段，当前不直接参与评分"），代码 `MssInputSnapshot` 未定义。

**建议**: 决策是否保留。如保留，在代码中补入（默认值 0.0）；如废弃，在设计中移除。

---

## 六、算法公式核对结果（确认正确的部分）

以下核心公式经逐行比对，**代码与设计完全一致**：

| 公式/逻辑 | 设计位置 | 代码位置 | 状态 |
|----------|---------|---------|------|
| 大盘系数 `rise_count/total_stocks` | §3.1 | engine.py:483 | ✅ 一致 |
| 赚钱效应 `0.4×涨停+0.3×新高+0.3×强涨` | §3.2 | engine.py:489-494 | ✅ 一致 |
| 亏钱效应 `0.3×炸板+0.2×跌停+0.3×强跌+0.2×新低` | §3.3 | engine.py:500-512 | ✅ 一致 |
| 连续性 `0.5×连板比+0.5×连新高比` | §3.4 | engine.py:518-528 | ✅ 一致 |
| 极端因子 `恐慌尾部+逼空尾部` | §3.5 | engine.py:534-536 | ✅ 一致 |
| 波动因子 `0.5×涨跌幅标准差+0.5×成交额波动比` | §3.6 | engine.py:550-553 | ✅ 一致 |
| 温度公式 `0.17+0.34+0.34+0.05+0.05+0.05` | §4.2 | engine.py:559-568 | ✅ 一致 |
| Z-Score 归一化 `(z+3)/6×100` | §7 | engine.py:88-101 | ✅ 一致 |
| 周期状态机 8 态优先级匹配 | §5.2 | engine.py:369-418 | ✅ 一致 |
| 仓位建议映射 | §5.1 | engine.py:421-432 | ✅ 一致 |
| 中性度 `1-|t-50|/50` | §6 | engine.py:581 | ✅ 一致 |
| 历史排名/百分位 | §6.1 | engine.py:435-453 | ✅ 一致 |
| 自适应阈值分位数 | §5.1 | engine.py:134-152 | ✅ 一致 |
| 冷启动回退固定阈值 | §5.1 | engine.py:143-144 | ✅ 一致 |

**MSS 的核心算法公式实现完全正确，无计算逻辑偏差。**

---

## 七、急救优先级与执行建议

### 第一波急救（立即执行）

| 编号 | 动作 | 涉及文件 | 工作量 |
|------|------|---------|--------|
| P0-1 | 重写 information-flow §2.6 趋势判定 | `mss-information-flow.md` | 小 |
| P0-2 | 重写 information-flow §6 异常处理 | `mss-information-flow.md` | 小 |
| P0-3 | 重绘 information-flow §3 组件架构 | `mss-information-flow.md` | 中 |
| P2-1 | 修复返回类型注解 | `engine.py:462` | 极小 |

### 第二波急救（尽快执行）

| 编号 | 动作 | 涉及文件 | 工作量 |
|------|------|---------|--------|
| P1-1 | §7.1 标注当前使用硬编码 baseline + 登记债务 | `mss-algorithm.md` | 小 |
| P1-2 | 补充必备字段缺失检查 + 降级其余约束 | `engine.py` + `mss-algorithm.md` | 中 |
| P2-2 | 补齐数据模型字段差异 | `mss-data-models.md` | 中 |

### 第三波（正常迭代处理）

| 编号 | 动作 | 涉及文件 | 工作量 |
|------|------|---------|--------|
| P3-1 | 标注预警规则未实现 | `mss-algorithm.md` + `mss-data-models.md` | 极小 |
| P3-2 | PositionAdvice 枚举 | `enums.py` 或文档 | 极小 |
| P3-3 | extreme_direction_bias 阈值对齐 | 文档 | 极小 |
| P3-4 | trend_quality 分级文档补充 | `mss-algorithm.md` | 小 |
| P3-5 | yesterday_limit_up_today_avg_pct 去留 | 文档或代码 | 极小 |
| P1-1 延伸 | 实现 parquet baseline 加载 + 滚动更新 | `engine.py` + 新模块 | 大 |

---

## 八、关键判断

1. **MSS 核心算法公式正确无误** — 六因子计算、温度合成、周期状态机、趋势判定的代码实现与设计文档完全一致。
2. **最大问题在 `mss-information-flow.md`** — 这份文档有三处严重滞后/矛盾，是全部 12 项差异中最危险的，因为它可能误导后续开发和审核。
3. **代码质量良好** — 差异主要集中在"防御性检查不够严格"和"部分设计特性尚未实现"，而非"实现了错误逻辑"。代码中额外增加的防护（NaN/inf 检查、defensive max(0, ...)）反而比设计更健壮。
