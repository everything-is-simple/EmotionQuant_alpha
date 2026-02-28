# PAS — 差异清单

共 15 项差异。三因子公式全部偏离设计。

---

## P0 算法语义偏差（8 项）

### PAS-P0-01：牛股基因因子子权重不一致

- **设计**: `0.4×limit_up_120d_ratio + 0.3×new_high_60d_ratio + 0.3×max_pct_chg_history_ratio`
- **代码**: `0.4 * wlur + 0.4 * wnhr + 0.2 * wmaxpct`
- **位置**: `pipeline.py:292`
- **实锤**: new_high 权重 0.3→0.4，max_pct_chg 权重 0.3→0.2

### PAS-P0-02：max_pct_chg_history 计算方式完全不同

- **设计**: `max_pct_chg_history / 100`（百分数字段→ratio，无天花板）
- **代码**: `rolling(120).max() / 0.30` clip 到 [0,1]（以 30% 为满分天花板）
- **位置**: `pipeline.py:289-291`
- **实锤**: 涨幅 >30% 的爆发股评分被截断为满分，丧失区分度

### PAS-P0-03：结构因子缺失 trend_continuity_ratio（30% 权重蒸发）

- **设计**: `0.4×price_position + 0.3×trend_continuity_ratio + 0.3×breakout_strength`
- **代码**: `0.7 * _pos + 0.3 * _wbsn`（trend_continuity 不存在）
- **位置**: `pipeline.py:306-311`
- **实锤**: 连续上涨 5 天和连续上涨 0 天的股票获得相同结构评分

### PAS-P0-04：trend_continuity_ratio 错误归属（结构→行为）

- **设计**: trend_continuity_ratio 属于"结构位置/突破"宏观方向
- **代码**: `_trend_comp` 被放入行为因子
- **位置**: `pipeline.py:435-436`
- **实锤**: 违反设计 §2.4 宏观方向互斥归属规则

### PAS-P0-05：行为确认因子组件和权重全部不同

- **设计**: `0.4×volume_quality + 0.3×pct_chg_norm(±20%) + 0.3×limit_up_flag`
- **代码**: `0.4 * _vq + 0.4 * _pc(±10%) + 0.2 * _trend_comp`
- **位置**: `pipeline.py:435-436`
- **实锤**: limit_up_flag(涨停/炸板确认)被替换为 trend_comp(连涨天数)；pct_chg 范围缩窄

### PAS-P0-06：volume_quality 计算被大幅简化

- **设计**: `0.60×量比归一化 + 0.25×换手率归一化 + 0.15×收盘保真度`
- **代码**: `(vol / vol_avg).clip(0, 2) / 2`（仅量比）
- **位置**: `pipeline.py:314-315`
- **缺失**: turnover_norm 和 intraday_retention 完全缺失

### PAS-P0-07：突破参考价不随自适应窗口变化

- **设计**: breakout_ref 按 adaptive_window 选择（20d→high_20d_prev, 60d→high_60d_prev, 120d→high_120d_prev）
- **代码**: 始终取 max(high_20d_prev, high_60d_prev)，120d_prev 从未计算
- **位置**: `pipeline.py:295-300`
- **实锤**: 低波动标的（应用 120 日窗口）的突破判断基于短期前高，信号过敏

### PAS-P0-08：突破强度归一化方式不同

- **设计**: `(close - breakout_ref) / max(breakout_ref, ε)`（简单比率，允许负值）
- **代码**: clip(-0.2, 0.2) + 线性映射到 [0,1]（>20% 饱和，负突破也获正值）
- **位置**: `pipeline.py:302-303`
- **实锤**: 大幅突破区分度被截断；Z-Score 本身已处理极值

---

## P1 数据源缺失（2 项）

### PAS-P1-01：raw_daily_basic 未读取 — turnover_rate 粗略近似

- **设计**: turnover_rate 来自 raw_daily_basic（真实换手率 = 成交量/流通股本×100%）
- **代码**: `amount / (close × 10000)` — 物理含义不明，大盘股系统性低估
- **位置**: `pipeline.py:408`
- **影响**: 自适应窗口选择（依赖 turnover_rate 阈值 3.0/8.0）产生系统性偏差

### PAS-P1-02：raw_limit_list 未读取 — 涨跌停全靠价格推断

- **设计**: is_limit_up / is_touched_limit_up / limit_up_count_120d 来自 raw_limit_list
- **代码**: 用日收益率阈值近似，且两处口径不一致（日间 vs 日内）
- **位置**: `pipeline.py:280-282`（牛股基因），`pipeline.py:472-474`（风险折扣）
- **影响**: 涨停统计不准 + 炸板识别缺失 + 口径不一致

---

## P2 输出模型偏差（3 项）

### PAS-P2-01：主表缺少 stock_name/industry_code/entry/stop/target

- 设计要求但代码未输出；多出别名字段 pas_score/pas_direction

### PAS-P2-02：因子中间表 18 字段仅写入 6 个

- 缺失 12 个字段：limit_up_count_120d, new_high_count_60d, max_pct_chg_history, price_position 等

### PAS-P2-03：pas_opportunity_log 表未实现

- 设计定义的等级变化日志表完全缺失

---

## P3 文档/基线（2 项）

### PAS-P3-01：docstring 因子命名为早期概念

- 代码: momentum_score/volume_score/pattern_score；设计: bull_gene/structure/behavior

### PAS-P3-02：Z-Score baseline 未按设计使用 parquet 文件

- 代码从历史 tail(120) 内联计算，未持久化版本管理
