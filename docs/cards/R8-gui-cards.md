# R8 GUI 重建 — 执行卡

**阶段目标**：完全按设计的 4 层架构重建。
**总工期**：8-10 天
**前置条件**：R7 完成（依赖 Analysis 产出的 dashboard_snapshot）
**SOS 覆盖**：docs/sos/gui 全部 25 项

---

## CARD-R8.1: 目录重组 + 服务层骨架

**工作量**：1.5 天
**优先级**：P0（架构完全不同）
**SOS 映射**：G-01, G-06

### 交付物

- [ ] 目录重组为 4 层
  ```
  src/gui/
  ├── pages/           # 7 个页面模块
  ├── services/        # 5 个服务
  ├── components/      # 可复用 UI 组件
  ├── models/          # 数据模型
  └── utils/           # 工具函数
  ```
- [ ] DataService 重建 (G-06)
  - `DataService(repository: DataRepository)` — 通过仓库抽象层
  - 删除 `DataService(database_path: Path)` 直连 DuckDB
  - 创建 `DataRepository` 抽象层
  - 所有 SQL 封装在 repository 中，service 不含裸 SQL
- [ ] CacheService 实现 (G-07)
  - `get_cached(key) → Optional[data]`
  - `set_cached(key, data, ttl)`
  - `build_cache_key(page, trade_date, filters) → str`
  - `get_freshness_meta(key) → FreshnessMeta`
  - 4 类 TTL：dashboard=24h, market=1min, industry=24h, session=会话级
  - FreshnessMeta 使用真实 `data_asof`（非 `_utc_now()` 填充）
- [ ] FilterService 骨架 (G-08)
  - `apply_filters(df, config) → df`
  - `apply_sort(df, sort_config) → df`
  - `paginate(df, page, size) → (df, PaginationInfo)`

### 验收标准

1. 目录结构与设计文档一致
2. DataService 不含 `duckdb.connect` 直连
3. CacheService 缓存生效（重复请求不查库）
4. FreshnessMeta.cache_age > 0（非始终 0）

---

## CARD-R8.2: FilterService + ExportService 完整实现

**工作量**：1.5 天
**优先级**：P0
**SOS 映射**：G-08, G-09, G-14, G-15

### 交付物

- [ ] FilterService 完整实现 (G-08, G-14)
  - Dashboard：`final_score >= dashboard_min_score`
  - IRS：`rank <= max_rank`, `rotation_status IN (...)`
  - PAS：`opportunity_score >= min_score`, `grade >= level`
  - 集成推荐：`final_score >= min_score`, `position >= min_position`
  - 删除当前"参数被接受但 SQL 不使用"的虚假过滤
- [ ] 排序完整实现 (G-15)
  - Dashboard 推荐：主排序 final_score DESC + 次排序 stock_code ASC
  - IRS 行业：主排序 rank ASC + 次排序 industry_score DESC
  - PAS 个股：主排序 opportunity_score DESC + 次排序 neutrality ASC
  - 集成推荐：主排序 final_score DESC + 次排序 position_size DESC
  - 交易记录：主排序 trade_date DESC
  - 持仓列表：主排序 unrealized_pnl DESC
- [ ] ExportService 实现 (G-09)
  - `export_csv(data, filename) → Path`
  - `export_markdown(report, filename) → Path`
  - `export_recommendation_list(recommendations) → Path`
  - `export_performance_report(metrics) → Path`
  - 交互式按需导出（Streamlit 中点击按钮触发）

### 验收标准

1. 过滤生效：设置 min_score=60 后列表不含 <60 分的标的
2. 次排序生效：同分标的按次排序字段排列
3. 导出按钮点击后生成 CSV/Markdown 文件

---

## CARD-R8.3: 7 个页面模块拆分

**工作量**：2 天
**优先级**：P0
**SOS 映射**：G-01（页面拆分）

### 交付物

- [ ] `src/gui/pages/dashboard.py` — Dashboard 页
  - 市场概况（温度/周期/趋势）
  - Top 推荐列表（带过滤+排序）
  - 绩效摘要
- [ ] `src/gui/pages/market.py` — Market 页
  - MSS 温度曲线
  - 温度历史对比
- [ ] `src/gui/pages/industry.py` — Industry 页
  - IRS 行业评分排行
  - 行业轮动状态
- [ ] `src/gui/pages/stock.py` — Stock 页
  - PAS 个股评分
  - 机会列表
- [ ] `src/gui/pages/backtest.py` — Backtest 页
  - 回测结果展示
  - equity_curve 图表
  - A/B/C 对照
- [ ] `src/gui/pages/trading.py` — Trading 页
  - 交易记录
  - 持仓列表
  - 风控事件
- [ ] `src/gui/pages/analysis.py` — Analysis 页
  - 绩效指标
  - 信号归因
  - 日报展示
- [ ] 从 dashboard.py 拆分 7 个 `_render_xxx()` 到独立页面
  - 每个页面独立可测试
  - 页面间通过 Streamlit session_state 共享数据

### 验收标准

1. 7 个页面模块可独立 import
2. 旧 dashboard.py 的 `_render_xxx()` 全部迁移
3. Streamlit 侧边栏导航可切换页面

---

## CARD-R8.4: 数据模型 + ChartService

**工作量**：1.5 天
**优先级**：P1
**SOS 映射**：G-02, G-03, G-04, G-11, G-17, G-19

### 交付物

- [ ] GuiRunResult 语义修正 (G-02)
  - 修正为设计定义：`GuiRunResult(rendered_pages, data_state, freshness_summary, created_at)`
  - 保留旧 export 功能但改名为 `ExportResult`
- [ ] 7 个缺失数据模型 (G-03)
  - UiObservabilityPanel：timeout/empty/fallback 计数
  - RecommendationReasonPanel：mss/irs/pas_attribution + risk_alert
  - ChartZone：温度曲线 4 色区域划分
  - RecommendationScatterData + ScatterPoint
  - GuiConfig：refresh_interval, page_size, top_n 等（从硬编码提取）
  - PermissionConfig：Viewer/Analyst/Admin（可选，标注 TODO）
- [ ] 模型字段补齐 (G-04)
  - IntegratedPageData += observability: UiObservabilityPanel
  - RecommendationItem += reason_panel: RecommendationReasonPanel
  - TemperatureChartData += zones: List[ChartZone]
- [ ] ChartService 实现 (G-11)
  - `build_temperature_chart(history) → TemperatureChartData`（含 4 色 zones）
  - `build_industry_chart(scores) → IndustryChartData`
  - `build_recommendation_scatter(recommendations) → RecommendationScatterData`
- [ ] 温度曲线 zones 实现 (G-17)
  - 过热区 (≥70)：红色
  - 偏热区 (50-70)：橙色
  - 偏冷区 (30-50)：蓝色
  - 过冷区 (<30)：深蓝色
- [ ] 推荐散点图实现 (G-19)
  - X 轴：final_score
  - Y 轴：risk_reward_ratio
  - 颜色：recommendation 等级
  - 大小：position_size

### 验收标准

1. GuiConfig 从配置读取（非硬编码）
2. 温度曲线有 4 色背景区域
3. 推荐散点图可交互

---

## CARD-R8.5: CP-09 最小闭环 + 集成对齐

**工作量**：1 天
**优先级**：P0
**SOS 映射**：G-10, G-20, G-21, G-22, G-23, G-24, G-25

### 交付物

- [ ] run_minimal() 实现 (G-10, G-20)
  - `DataService.run_minimal(trade_date) → GuiRunResult`
  - 渲染 Dashboard + Integrated 两个核心页面
  - 返回渲染状态（成功/部分/失败）
- [ ] 导出范式统一 (G-21)
  - 支持两种模式：
    - 交互式：Streamlit 中点击按钮 → 按需导出
    - CLI 批量：`eq gui --export daily-report` → 批量导出
- [ ] 推荐原因联动 (G-22)
  - 用户点击推荐项 → get_recommendation_reason_panel()
  - 读取 L4 归因数据（mss/irs/pas attribution）
  - 侧边栏展示原因面板
- [ ] 可观测性基础 (G-23)
  - UI 事件记录：timeout / empty_state / data_fallback
  - 写入日志 + 计数器
- [ ] 回测字段名匹配 (G-24)
  - `backtest_name` → 从 `backtest_id` 生成（或更新 GUI 读取 backtest_id）
  - `annual_return` / `sharpe_ratio` → 从 R5 持久化的 backtest_results 读取（非 0）
- [ ] performance_metrics 数据源确认 (G-25)
  - GUI 从 R7 Analysis 写入的 `performance_metrics` 表读取
  - 确认 R7 写入后指标非零

### 验收标准

1. run_minimal() 可渲染 Dashboard + Integrated
2. 推荐项可点击查看原因
3. annual_return / sharpe_ratio 展示非零值
4. 导出 CSV/Markdown 文件可正常生成

---

## CARD-R8.6: Streamlit 验证 + 契约测试

**工作量**：1 天
**优先级**：P1（质量闭环）
**前置依赖**：CARD-R8.1~R8.5

### 交付物

- [ ] Streamlit 逐页面验证
  - Dashboard：温度/周期/趋势显示正确
  - Market：温度曲线含 4 色 zones
  - Industry：行业评分排行 + 轮动状态正确
  - Stock：个股评分列表 + 过滤生效
  - Backtest：equity_curve 图表 + 绩效指标非零
  - Trading：交易记录 + 持仓列表正确
  - Analysis：绩效指标 + 日报内容正确
- [ ] 过滤/排序验证
  - 设置过滤条件 → 列表内容变化
  - 切换排序 → 顺序变化
- [ ] 缓存验证
  - 首次加载查库
  - 刷新页面在 TTL 内不查库
- [ ] 契约测试
  - GuiRunResult 字段完整性
  - 7 个页面模块可独立 import
  - DataService / CacheService / FilterService / ExportService 可实例化
- [ ] IRS 图表颜色修正 (G-18)
  - HOLD → gray（非 orange）

### 验收标准

1. 7 个页面全部可正常渲染
2. 过滤/排序/缓存机制全部生效
3. 数据展示正确性：温度/评分/绩效指标与数据库一致

---

## R8 阶段验收总览

完成以上 6 张卡后，需满足：

1. **4 层架构**：pages + services + components + models + utils
2. **7 个页面**：独立模块，可独立测试
3. **5 个服务**：DataService + CacheService + FilterService + ChartService + ExportService
4. **过滤生效**：FilterConfig 真正驱动 SQL 查询
5. **缓存有效**：FreshnessMeta 真实缓存年龄
6. **CP-09 闭环**：run_minimal() 可渲染核心页面
7. **质量闭环**：7 页面验证通过 + 契约测试

**下一步**：进入 R9 增强包 + 稳定化（全链路闭环）。
