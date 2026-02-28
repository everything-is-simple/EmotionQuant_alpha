# GUI 模块 — 修复方案

> 原则: AD-01 设计为权威 | AD-02 OOP 全面 | AD-05 统一模块结构

---

## 1. 架构重建目标

从 5 文件扁平结构重建为设计的 4 层架构：

```
src/gui/
├── pages/
│   ├── dashboard.py          ← 从现 dashboard.py 拆出
│   ├── mss.py
│   ├── irs.py
│   ├── pas.py
│   ├── integrated.py
│   ├── trading.py
│   └── analysis.py
├── components/
│   ├── temperature_card.py
│   ├── cycle_badge.py
│   ├── industry_rank_table.py
│   ├── stock_signal_table.py
│   ├── recommendation_table.py
│   └── risk_overview.py
├── services/
│   ├── data_service.py       ← 改为接受 DataRepository
│   ├── cache_service.py      ← 新增
│   ├── filter_service.py     ← 新增
│   ├── export_service.py     ← 新增
│   ├── chart_service.py      ← 新增
│   └── observability.py      ← 新增
├── utils/
│   ├── formatters.py         ← 现 formatter.py 改名
│   ├── filters.py            ← 新增
│   └── exporters.py          ← 新增
├── models.py                 ← 补齐缺失模型
└── app.py                    ← 入口
```

---

## 2. 分批修复任务

### 第一批：P0 致命 — 数据正确性与核心功能

#### FIX-01 FilterService — 过滤逻辑落地 (G-08, G-14)

**最高优先级**。当前用户看到的是未过滤全量数据。

实现 `FilterService.apply_filters(items, config)` 链式过滤：
- Dashboard: `final_score >= dashboard_min_score`
- IRS: `rank <= max_rank, rotation_status IN allowed_statuses`
- PAS: `opportunity_score >= min_score, grade >= min_level`
- Integrated: `final_score >= min_score, position_size >= min_position`

在所有 DataService 查询方法中，将 FilterConfig 参数实际应用到 SQL WHERE 子句。

#### FIX-02 CacheService — 缓存机制引入 (G-07, G-16)

实现基于 Streamlit `st.cache_data` 或内存 dict 的缓存层：
- `get_cached(key) → data | None`
- `set_cached(key, data, ttl)`
- `build_cache_key(data_type, trade_date, filters)`

修复 FreshnessMeta: `data_asof` 改为从 DB 查询实际最新 `trade_date`，不再用 `_utc_now()` 伪造。

#### FIX-03 DataService 重构 (G-06)

构造函数改为 `DataService(repository: DataRepository)`，引入 Repository 抽象层。
现有裸 SQL 逻辑下沉到 `DataRepository` 实现类中。

#### FIX-04 GuiRunResult 拆分 (G-02)

- 设计版改名为 `GuiRenderResult`（渲染闭环结果）
- 代码版改名为 `GuiExportResult`（导出产物结果）
- 两者各司其职，不再同名冲突

#### FIX-05 CP-09 闭环入口 (G-10, G-20)

新增 `DataService.run_minimal(trade_date) → GuiRenderResult`：
1. `get_dashboard_data(trade_date, top_n)`
2. `get_integrated_page_data(trade_date, filters, page=1)`
3. 渲染 Dashboard + Integrated
4. 返回 `GuiRenderResult(rendered_pages, data_state, freshness_summary)`

#### FIX-06 ExportService (G-09)

实现交互式按需导出（Streamlit 下载按钮）：
- `export_to_csv(data, columns, filename)`
- `export_recommendations(trade_date, filters)`
- `export_performance_report(report_date)`

保留现有 CLI 批量导出作为补充路径。

---

### 第二批：P1 严重 — 功能完整性

#### FIX-07 补齐 7 个数据模型 (G-03)

在 models.py 中新增：
- `UiObservabilityPanel`
- `RecommendationReasonPanel`
- `ChartZone`
- `RecommendationScatterData` + `ScatterPoint`
- `GuiConfig`（替换所有硬编码 top_n=10, page_size=50）
- `PermissionConfig`

#### FIX-08 补齐 3 个模型字段 (G-04)

- `IntegratedPageData` 添加 `observability: UiObservabilityPanel`
- `RecommendationItem` 添加 `reason_panel: RecommendationReasonPanel = None`
- `TemperatureChartData` 添加 `zones: List[ChartZone]`

#### FIX-09 ChartService (G-11, G-17, G-19)

提取为独立 `services/chart_service.py`：
- `build_temperature_chart(mss_history)` — 含 4 色 zones
- `build_industry_chart(industries, top_n)`
- `build_recommendation_scatter(recommendations)` — 新增

#### FIX-10 次排序补齐 (G-15)

所有 SQL ORDER BY 补齐次排序字段。

#### FIX-11 页面拆分 (G-01)

将 dashboard.py 的 7 个 `_render_xxx()` 拆分为 7 个独立页面模块。
提取可复用 UI 元素为 `components/` 组件。

#### FIX-12 导出范式补齐 (G-21)

在 Streamlit 页面中添加 `st.download_button` 实现交互式导出。

---

### 第三批：P2/P3 — 增强

#### FIX-13 回测-GUI 字段映射修复 (G-24)

`_map_backtest` 用 `backtest_id` 替代 `backtest_name`。
`annual_return` / `sharpe_ratio` 从 `daily_return_mean/std` 推算或等待 Analysis 修复。

#### FIX-14 推荐原因联动 (G-22)

实现 `get_recommendation_reason_panel(stock_code, trade_date)` — 依赖 L4 归因数据就绪。

#### FIX-15 可观测性 (G-23)

实现 `record_ui_event(page_name, event_type)` logger 记录。

#### FIX-16 IRS 颜色决策 (G-18)

决策: 接受代码的三色方案（green/orange/gray 比设计的二色更有信息量），更新设计文档。

#### FIX-17 FormatterService 对齐 (G-12)

`format_pnl` 恢复为返回 `(formatted_amount, color)` 元组。

---

## 3. 依赖关系

```
FIX-03 (DataService 重构)
  ├→ FIX-01 (FilterService，需 Repository)
  ├→ FIX-02 (CacheService，需 Repository 读 data_asof)
  └→ FIX-05 (CP-09 闭环，需 DataService 新方法)

FIX-07 (数据模型)
  ├→ FIX-08 (字段补齐，需模型定义)
  └→ FIX-09 (ChartService，需 ChartZone 模型)

FIX-11 (页面拆分) — 独立，可并行
FIX-12 (导出) → 依赖 FIX-06 (ExportService)
```

**关键路径**: FIX-03 → FIX-01（DataService 重构 → 过滤落地）是最核心路径。

---

## 4. 跨模块依赖

| GUI 问题 | 上游依赖 |
|----------|----------|
| G-25 绩效全 0 | Analysis A-01 + A-07（绩效指标 + equity_curve） |
| G-24 回测字段 | Backtest 补充 annual_return / sharpe_ratio |
| G-22 推荐原因 | Analysis 风险分析 + 归因数据 |

GUI 的部分修复阻塞于 Analysis 和 Backtest 模块的先行修复。
