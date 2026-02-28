# R3 IRS + PAS 重建 — 执行卡

**阶段目标**：两个评分系统的因子计算完全对齐设计。本路线图最大工作量阶段。
**总工期**：12-15 天
**前置条件**：R1 完成（依赖正确的 industry_snapshot / stock_gene_cache / raw_daily）
**SOS 覆盖**：docs/sos/irs 全部 8 项 + docs/sos/pas 全部 15 项

---

## CARD-R3.1: IRS 归一化路径修复（致命 C1/C2/C3）

**工作量**：2 天
**优先级**：P0（核心算法错误，行业评分不可信）
**SOS 映射**：IRS-C1, IRS-C2, IRS-C3

### 交付物

- [ ] 修复估值因子归一化路径 (C1)
  - **错误**：`valuation_raw = w_pe * (-pe) + w_pb * (-pb)` → 一次 z-score
  - **正确**：先 z-score(-PE) → 先 z-score(-PB) → 按 style_bucket 权重加权 → 再 z-score
  - 位置：`pipeline.py:498-533`, `calculator.py:189-224`
  - 修复两个文件保持一致
- [ ] 修复龙头因子归一化路径 (C2)
  - **错误**：原始值 0.6/0.4 加权 → z-score
  - **正确**：先 z-score(leader_avg_pct) → 先 z-score(leader_limit_up_ratio) → 0.6/0.4 加权（无最终 z-score）
  - 位置：`pipeline.py:503-538`, `calculator.py:194-230`
- [ ] 修复 calculator.py 估值权重 (C3)
  - **错误**：硬编码 `0.5 * (-pe) + 0.5 * (-pb)`
  - **正确**：按 style_bucket 查表（growth: 0.35/0.65, balanced: 0.50/0.50, value: 0.65/0.35）
  - 恢复 `STYLE_WEIGHTS` 常量和 `style_bucket` 读取逻辑
  - 位置：`calculator.py:189-192`

### 验收标准

1. 估值因子：PE(50) + PB(5) 的行业，PE 不再主导（两者标准化后贡献相当）
2. 龙头因子：涨幅均值(连续)和涨停比率(离散)分别标准化后再合成
3. growth 行业 PB 权重 0.65，value 行业 PE 权重 0.65
4. pipeline.py 与 calculator.py 输出一致（消除副本漂移）

### 技术要点

- z-score 使用 `src/shared/zscore.py` 的统一实现
- style_bucket 来自 `industry_snapshot` 表的 `style_bucket` 字段（R1 已确保正确）
- 归一化顺序：子因子各自 z-score → 加权合成 → 组合 z-score（估值）/ 不再 z-score（龙头）

---

## CARD-R3.2: IRS 数据源与质量修复（M1/M2/M3）

**工作量**：1 天
**优先级**：P1（数据语义偏差）
**前置依赖**：CARD-R3.1
**SOS 映射**：IRS-M1, IRS-M2, IRS-M3

### 交付物

- [ ] M1：基因库因子数据源对齐
  - **当前**：使用 industry_snapshot 当日涨停/新高数 + EWM(decay=0.9)
  - **设计**：从 raw_daily + raw_limit_list 统计 3 年滚动窗口累计涨停/新高数
  - 实现方案：从 stock_gene_cache 读取个股 3 年累计数据 → 按行业聚合
  - 位置：`pipeline.py:508-514`
- [ ] M2：market_amount_total 来源统一
  - **当前**：`groupby("trade_date")["industry_amount"].sum()`
  - **正确**：从 industry_snapshot 的 `market_amount_total` 字段直读
  - 过滤 "ALL" 聚合行避免重复计算
  - 位置：`pipeline.py:406-410, 460-461`
- [ ] M3：calculator.py 补齐 stale_days 判断
  - 添加 `stale_days > 0` → quality_flag = "stale" 分支
  - 保留现有 `sample_days < 60` → "cold_start" 分支
  - 位置：`calculator.py:262`

### 验收标准

1. 基因库因子反映 3 年历史惯性，而非仅当日 EWM 衰减
2. market_amount_total 与 industry_snapshot 表值一致
3. stale 数据被标记为 "stale" 而非 "normal"

---

## CARD-R3.3: IRS OOP 门面 + 输出清理

**工作量**：1 天
**优先级**：P1（架构对齐）+ P3（清理）
**前置依赖**：CARD-R3.1
**SOS 映射**：IRS-m1, IRS-m2

### 交付物

- [ ] 创建 `src/algorithms/irs/service.py`
  - `IrsService(BaseService)` 类
  - 构造函数注入 `config`, `repository: IrsRepository`
  - 方法：
    - `calculate(trade_date: str) -> pd.DataFrame`
    - `get_industry_scores(trade_date: str) -> pd.DataFrame`
    - `get_rotation_status(trade_date: str, industry_code: str) -> str`
- [ ] 创建 `src/algorithms/irs/repository.py`
  - `IrsRepository(BaseRepository)` 类
  - 方法：`read_industry_snapshot()`, `write_industry_daily()`, `read_history()`
- [ ] 创建 `src/algorithms/irs/models.py`
  - 从 pipeline.py/calculator.py 提取 dataclass（IrsIndustryScore, IrsRunResult 等）
- [ ] 清理多余输出列 (m1)
  - 删除 `irs_score`（重复 industry_score）
  - 删除 `recommendation`（与设计 allocation_advice 语义冲突）
  - 保留但标注 `data_quality/stale_days/source_trade_date/contract_version`
- [ ] 修正 gene_score docstring (m2)
  - 删除"强势率"描述，更正为"涨停率 + 新高率"两个子因子

### 验收标准

1. `IrsService` 可被 Integration 模块导入使用
2. 输出 DataFrame 无 `recommendation` 列（仅保留 `allocation_advice`）
3. pipeline.py 与 calculator.py 对齐，消除副本漂移

---

## CARD-R3.4: PAS 数据源修复

**工作量**：1.5 天
**优先级**：P1（数据源缺失）
**SOS 映射**：PAS-P1-01, PAS-P1-02

### 交付物

- [ ] 读取 `raw_daily_basic` 真实换手率
  - 新增 DuckDB 查询：`SELECT stock_code, trade_date, turnover_rate FROM raw_daily_basic`
  - 替换当前 `amount / (close × 10000)` 近似公式
  - 位置：`pipeline.py:408`
  - 确保自适应窗口选择阈值 (3.0/8.0) 基于真实换手率
- [ ] 读取 `raw_limit_list` 真实涨跌停状态
  - 新增 DuckDB 查询：`SELECT stock_code, trade_date, limit FROM raw_limit_list`
  - `limit='U'` → is_limit_up=True
  - `limit='Z'` → is_touched_limit_up=True（炸板）
  - `limit='D'` → is_limit_down=True
  - 替换当前日收益率阈值近似法
  - 位置：`pipeline.py:280-282`（牛股基因）, `pipeline.py:472-474`（风险折扣）
- [ ] 统一口径
  - 牛股基因和风险折扣使用同一个 is_limit_up 来源（raw_limit_list）
  - 消除日间 vs 日内口径不一致

### 验收标准

1. turnover_rate 来自 raw_daily_basic（非近似），值域 [0, 100]
2. is_limit_up/is_limit_down 来自 raw_limit_list（非价格推断）
3. 自适应窗口选择不再因换手率偏差产生系统性偏移

### 技术要点

- raw_daily_basic 可能部分日期缺失，需 left join + fillna（用前一日或行业均值）
- raw_limit_list 仅涨跌停日有记录，非涨跌停日应为 False

---

## CARD-R3.5: PAS 三因子公式重写

**工作量**：3 天
**优先级**：P0（三因子公式全部偏离设计，核心算法）
**前置依赖**：CARD-R3.4（数据源已修复）
**SOS 映射**：PAS-P0-01~P0-08

### 交付物

- [ ] **牛股基因因子** (P0-01, P0-02)
  - 权重修正：`0.4×limit_up_120d_ratio + 0.3×new_high_60d_ratio + 0.3×max_pct_chg_history_ratio`
  - max_pct_chg_history 修正：`max_pct_chg_history / 100`（百分数→ratio，去掉 `/0.30` 天花板）
  - 位置：`pipeline.py:289-292`
- [ ] **结构因子** (P0-03, P0-04, P0-07, P0-08)
  - 恢复 trend_continuity_ratio（从行为因子移回结构因子）
  - 权重：`0.4×price_position + 0.3×trend_continuity_ratio + 0.3×breakout_strength`
  - breakout_ref 按 adaptive_window 切换：
    - 20d → high_20d_prev
    - 60d → high_60d_prev
    - 120d → high_120d_prev（需新增计算）
  - 突破强度改为简单比率：`(close - breakout_ref) / max(breakout_ref, ε)`（允许负值，去掉 clip + 线性映射）
  - 位置：`pipeline.py:295-311`
- [ ] **行为确认因子** (P0-04, P0-05, P0-06)
  - 组件替换：`trend_comp` → `limit_up_flag`（来自 raw_limit_list）
  - 权重：`0.4×volume_quality + 0.3×pct_chg_norm(±20%) + 0.3×limit_up_flag`
  - pct_chg_norm 范围扩大：±10% → ±20%
  - 位置：`pipeline.py:435-436`
- [ ] **volume_quality 恢复三子组件** (P0-06)
  - `0.60×量比归一化 + 0.25×换手率归一化 + 0.15×收盘保真度`
  - 量比归一化：`clip(vol/vol_avg, 0, 3) / 3`
  - 换手率归一化：`clip(turnover_rate/行业中位数, 0, 3) / 3`（使用 R3.4 的真实 turnover_rate）
  - 收盘保真度：`1 - abs(close - high) / max(high - low, ε)`
  - 位置：`pipeline.py:314-315`

### 验收标准

1. 牛股基因：涨幅 >30% 的爆发股不被截断（区分度保留）
2. 结构因子：连续上涨 5 天 vs 0 天的股票获得不同结构评分
3. 行为因子：当日涨停的股票 limit_up_flag=1.0，非涨停=0.0
4. volume_quality：换手率高+量比大+收盘在高位的股票得分显著高于反例
5. 突破强度：120d 窗口标的使用 high_120d_prev 而非短期前高

### 技术要点

- trend_continuity_ratio 计算：连续收盘价高于前一日的天数 / adaptive_window
- 收盘保真度：衡量收盘价接近最高价的程度（1=收在最高，0=收在最低）
- 所有归一化后通过 `src/shared/zscore.py` 做最终 z-score

---

## CARD-R3.6: PAS 输出模型补全 + OOP 门面

**工作量**：1.5 天
**优先级**：P1（架构对齐）+ P2（输出模型）
**前置依赖**：CARD-R3.5
**SOS 映射**：PAS-P2-01, PAS-P2-02, PAS-P2-03, PAS-P3-01, PAS-P3-02

### 交付物

- [ ] 主表字段补全 (P2-01)
  - 补增：`stock_name`, `industry_code`, `entry_price`, `stop_price`, `target_price`
  - 删除别名：`pas_score`（使用 `opportunity_score`）, `pas_direction`（使用 `direction`）
- [ ] 因子中间表补全 (P2-02)
  - 补增 12 个缺失字段：
    - `limit_up_count_120d`, `new_high_count_60d`, `max_pct_chg_history`
    - `price_position`, `trend_continuity_ratio`, `breakout_ref`, `breakout_strength`
    - `volume_quality`, `turnover_norm`, `intraday_retention`
    - `pct_chg_norm`, `limit_up_flag`
  - 确保中间表 18 字段全部写入
- [ ] pas_opportunity_log 表实现 (P2-03)
  - 创建表：`(trade_date, stock_code, prev_grade, new_grade, score_change, trigger_factor)`
  - 每次评分后对比前一日等级，变化时写入日志
- [ ] 创建 `src/algorithms/pas/service.py`
  - `PasService(BaseService)` 类
  - 方法：`calculate()`, `get_stock_scores()`, `get_opportunities()`
- [ ] 创建 `src/algorithms/pas/engine.py`
  - 将纯计算逻辑从 pipeline.py 分离
  - 三因子计算函数：`calc_bull_gene()`, `calc_structure()`, `calc_behavior()`
  - volume_quality 子函数：`calc_volume_quality()`
- [ ] 创建 `src/algorithms/pas/repository.py`
  - `PasRepository(BaseRepository)` 类
- [ ] 创建 `src/algorithms/pas/models.py`
  - `StockPasDaily`, `PasFactorIntermediate`, `PasOpportunityLog` dataclass
- [ ] 更新 docstring (P3-01)
  - `momentum_score` → `bull_gene_score`
  - `volume_score` → `behavior_score`
  - `pattern_score` → `structure_score`

### 验收标准

1. 主表含 stock_name/industry_code/entry/stop/target 五个必要字段
2. 中间表 18 字段全部非空写入
3. 等级变化时 opportunity_log 有记录
4. pipeline.py 仅做编排，业务逻辑在 engine.py

---

## CARD-R3.7: IRS 契约测试

**工作量**：0.5 天
**优先级**：P1（质量闭环）
**前置依赖**：CARD-R3.1~R3.3

### 交付物

- [ ] 契约测试 `tests/contracts/test_irs.py`
  - 检查 `irs_industry_daily` 表 18 字段完整性
  - 检查 industry_score 值在 [0, 100] 范围
  - 检查 allocation_advice 为 {超配, 标配, 减配, 回避} 之一
  - 检查 rotation_status 为 {IN, OUT, HOLD} 之一
  - 检查 quality_flag 为 {normal, cold_start, stale} 之一
  - 检查估值因子：growth 行业 PB 权重 > PE 权重
- [ ] pipeline.py 与 calculator.py 对齐验证
  - 同一输入数据两套代码输出完全一致
  - 输出差异 → 测试失败

### 验收标准

1. 契约测试在 3 个交易日上全部通过
2. pipeline.py 和 calculator.py 输出 diff = 0

---

## CARD-R3.8: PAS 契约测试 + 评分分布验证

**工作量**：1.5 天
**优先级**：P1（质量闭环）
**前置依赖**：CARD-R3.4~R3.6

### 交付物

- [ ] 契约测试 `tests/contracts/test_pas.py`
  - 检查 `stock_pas_daily` 表 20 字段完整性
  - 检查 opportunity_score 值在 [0, 100] 范围
  - 检查 opportunity_grade 为 {S, A, B, C, D} 之一
  - 检查 direction 为 {bullish, bearish, neutral} 之一
  - 检查 entry_price / stop_price / target_price 非空且 stop < entry < target
  - 检查因子中间表 18 字段全部非空
- [ ] 评分分布验证（3-5 个交易日）
  - 全量运行，统计评分分布（均值/中位数/标准差/偏度）
  - 人工抽检 10 只标的的因子中间值
  - 验证三因子权重生效：修改某因子输入 → 输出变化方向正确
  - 输出验证报告：`artifacts/r3-validation-report.md`
- [ ] 端到端烟雾测试
  - Data(R1) → MSS(R2) → IRS(R3) → PAS(R3) 全链路运行
  - 检查无 ImportError / TypeError / KeyError
  - 检查输出行数 > 0

### 验收标准

1. 契约测试在 3-5 个交易日上全部通过
2. 评分分布合理（均值 ≈ 50，标准差 15-25，无极端偏度）
3. 抽检标的因子中间值与手算一致
4. 全链路烟雾测试通过

### 技术要点

- 评分分布验证用 `describe()` + 直方图（可选）
- 手算对照：选 2 只典型标的（一只高分一只低分），逐步骤核对三因子值
- 烟雾测试可复用 R0.5 的 CI 框架

---

## R3 阶段验收总览

完成以上 8 张卡后，需满足：

1. **IRS 致命修复**：C1/C2 归一化路径正确，C3 style_bucket 权重生效
2. **IRS 数据源**：基因库因子使用 3 年滚动窗口，market_amount_total 直读
3. **PAS 三因子**：牛股基因/结构/行为因子公式与设计 100% 一致
4. **PAS 数据源**：turnover_rate 和涨跌停状态来自真实数据
5. **OOP 架构**：IrsService + PasService 可用，pipeline 仅做编排
6. **输出模型**：主表/中间表/日志表字段完整
7. **质量闭环**：契约测试通过 + 评分分布合理 + 全链路烟雾测试通过

**下一步**：进入 R4 Validation + Integration 重建（32 项偏差，Validation 近乎完全重写）。
