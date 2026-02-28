# MSS — 差异清单

共 12 项差异。核心算法公式全部正确（13/13），问题集中在文档滞后和防御性机制。

---

## P0 危险：设计文档内部矛盾（3 项）

### MSS-P0-1：information-flow 趋势判定与算法文档矛盾

- **文档位置**: `mss-information-flow.md` §2.6 Step 6（行 197-201）
- **对标**: `mss-algorithm.md` §5.4（行 336-354）, `engine.py:330-361`
- **矛盾**: information-flow 描述的是"3日严格递增/递减"判定法，这实际上是 **冷启动回退方案**（<8日样本）。正式方案是 EMA(3) vs EMA(8) 交叉 + 5日斜率 + 动态 trend_band。
- **实锤**: 算法文档和代码完全一致使用 EMA+slope+trend_band，information-flow 遗漏了整套正式逻辑。

### MSS-P0-2：information-flow 异常处理与算法文档直接冲突

- **文档位置**: `mss-information-flow.md` §6.1（行 388）
- **对标**: `mss-algorithm.md` §10.5（行 504-516）, `engine.py:456-608`
- **矛盾**: information-flow 写"数据缺失时使用前一日数据"。算法文档 **明确禁止** 沿用前一日 temperature/cycle/trend 作为兜底。代码实际行为：total_stocks≤0 → 回退中性分 50；stale_days>3 → 抛 DataNotReadyError。
- **实锤**: "使用前一日数据"违反系统核心安全约束。

### MSS-P0-3：information-flow 组件架构图与实际架构不符

- **文档位置**: `mss-information-flow.md` §3（行 230-262）
- **对标**: `mss-api.md` v4.0.0, 实际代码架构
- **矛盾**: 画了 MssController → MssService → MssEngine + MssRepository + MssAlertService 等 7 个不存在的类。实际架构是 `run_mss_scoring()` → `calculate_mss_score()` 的 Pipeline 模式。

---

## P1 重要：代码与设计不一致（2 项）

### MSS-P1-1：Z-Score Baseline 加载机制完全缺失

- **设计**: parquet baseline 文件 + 滚动窗口(120日)在线更新，见 mss-algorithm.md §7.1
- **代码**: 硬编码 `DEFAULT_FACTOR_BASELINES` 字典（6 个因子的 mean/std 常量）
- **位置**: `engine.py:46-53`
- **实质**: 系统永远处于"冷启动兜底"状态，Z-Score 归一化基于固定参数

### MSS-P1-2：输入验证远松于设计的"零容忍"约束

- **设计**: 6 条零容忍约束（total_stocks>0, rise≤total, limit_up≤touched 等），见 mss-algorithm.md §10.1
- **代码**: 仅实现 stale_days>3 的检查，其余 5 条均未实现
- **位置**: `engine.py:456-608`, `MssInputSnapshot.from_record():196-232`
- **实质**: 脏数据静默通过，_to_int/_to_float 默认返回 0 而非报错

---

## P2 中等（2 项）

### MSS-P2-1：calculate_mss_score 返回类型注解错误

- **代码**: `engine.py:462` 注解 `-> MssScoreResult`，但 MssScoreResult 在 engine.py 中未定义
- **实际**: 返回 `MssPanorama`，`MssScoreResult = MssPanorama` 仅在 `pipeline.py:28` 定义
- **影响**: mypy/pyright 会报 NameError

### MSS-P2-2：数据模型字段差异

- **输入模型**: 设计 `MssMarketSnapshot` 缺 data_quality/stale_days/source_trade_date，代码 `MssInputSnapshot` 有
- **输出模型**: 设计 `MssPanorama` 缺 mss_score(deprecated)/data_quality/stale_days/contract_version/created_at；字段命名不同（temperature vs mss_temperature 等）
- **性质**: 代码更完整，设计文档需反向对齐

---

## P3 低优（5 项）

### MSS-P3-1：预警规则完全未实现

- 设计 mss-algorithm.md §9 定义了 4 种预警（过热/过冷/尾部活跃/趋势背离），代码无任何实现

### MSS-P3-2：PositionAdvice 枚举未实现

- 设计定义了 `PositionAdvice(Enum)`，代码使用字符串映射

### MSS-P3-3：extreme_direction_bias 零值防护阈值差异

- 设计 `max(raw, 1e-6)` vs 代码 `raw <= 1e-12 守卫`。效果等价，无风险。

### MSS-P3-4：trend_quality 分级粒度

- 代码增加了 degraded（<3日或8-19日）和 normal（≥20日）的更细分级，设计仅提及 cold_start

### MSS-P3-5：yesterday_limit_up_today_avg_pct 字段缺失

- 设计输入模型有此字段（标注为观测字段），代码未定义

---

## 确认正确的核心公式（13/13）

| 公式 | 设计位置 | 代码位置 | 状态 |
|------|---------|---------|------|
| 大盘系数 rise_count/total_stocks | §3.1 | engine.py:483 | ✅ |
| 赚钱效应 0.4×涨停+0.3×新高+0.3×强涨 | §3.2 | engine.py:489-494 | ✅ |
| 亏钱效应 0.3×炸板+0.2×跌停+0.3×强跌+0.2×新低 | §3.3 | engine.py:500-512 | ✅ |
| 连续性 0.5×连板比+0.5×连新高比 | §3.4 | engine.py:518-528 | ✅ |
| 极端因子 恐慌尾部+逼空尾部 | §3.5 | engine.py:534-536 | ✅ |
| 波动因子 0.5×涨跌幅标准差+0.5×成交额波动比 | §3.6 | engine.py:550-553 | ✅ |
| 温度权重 0.17+0.34+0.34+0.05+0.05+0.05 | §4.2 | engine.py:559-568 | ✅ |
| Z-Score 归一化 (z+3)/6×100 | §7 | engine.py:88-101 | ✅ |
| 周期状态机 8 态优先级匹配 | §5.2 | engine.py:369-418 | ✅ |
| 仓位建议映射 | §5.1 | engine.py:421-432 | ✅ |
| 中性度 1-\|t-50\|/50 | §6 | engine.py:581 | ✅ |
| 历史排名/百分位 | §6.1 | engine.py:435-453 | ✅ |
| 自适应阈值分位数+冷启动回退 | §5.1 | engine.py:134-152 | ✅ |
