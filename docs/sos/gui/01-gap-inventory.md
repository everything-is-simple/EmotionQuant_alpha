# GUI 模块 — 偏差清单

> 审计日期 2026-02-27 | 设计基准 gui v3.2.0

---

## A. 模块结构差异

### G-01 目录结构完全不同 `P0`

| 维度 | 设计 (4 层 ~18 文件) | 代码 (扁平 5 文件) |
|------|-----|-----|
| 页面 | `pages/` 7 个独立模块 | dashboard.py 中 7 个 `_render_xxx()` |
| 组件 | `components/` 6 个可复用组件 | 无抽象，UI 渲染内联在页面函数中 |
| 服务 | `services/` data + cache + observability | data_service.py 一个文件（无 cache/observability） |
| 工具 | `utils/` formatters + filters + exporters | formatter.py 一个文件 |

单页面无法独立测试；组件不可跨页面复用；页面增长后 dashboard.py 不可维护。

---

## B. 数据模型差异

### G-02 GuiRunResult 同名异义 `P0`

设计: `GuiRunResult(rendered_pages, data_state, freshness_summary, created_at)` — GUI 渲染闭环结果。
代码 (app.py:37-49): `GuiRunResult(export_mode, artifacts_dir, daily_report_path, quality_status, go_nogo, ...)` — 导出产物打包结果。
两者描述完全不同的概念。

### G-03 7 个数据模型完全缺失 `P1`

| 模型 | 设计用途 |
|------|----------|
| UiObservabilityPanel | UI 异常可观测性面板（timeout/empty/fallback 计数） |
| RecommendationReasonPanel | 推荐原因面板（mss/irs/pas_attribution + risk_alert） |
| ChartZone | 温度曲线区域划分（4 色 zones） |
| RecommendationScatterData + ScatterPoint | 推荐散点图数据 |
| GuiConfig | 全局配置（refresh_interval, page_size, top_n 等），当前全部硬编码 |
| PermissionConfig | 权限配置（Viewer/Analyst/Admin），当前无权限概念 |

### G-04 3 个模型字段缺失 `P1`

- `IntegratedPageData` 缺 `observability: UiObservabilityPanel`
- `RecommendationItem` 缺 `reason_panel: RecommendationReasonPanel`
- `TemperatureChartData` 缺 `zones: List[ChartZone]`

### G-05 已正确实现的模型 ✅

18 个 dataclass + 5 个枚举与设计完全一致（FreshnessMeta, FilterConfig, PaginationInfo,
DashboardData, IrsPageData, PasPageData 等）。

---

## C. API / 服务层差异

### G-06 DataService 构造方式根本偏离 `P0`

设计: `DataService(repository: DataRepository)` — 通过仓库抽象层访问。
代码: `DataService(database_path: Path)` — 直接 `duckdb.connect` + 裸 SQL。
DataRepository 抽象层完全不存在，无法 mock 测试。

### G-07 CacheService 整层缺失 `P0`

设计 6 个方法（get_cached/set_cached/build_cache_key/get_freshness_meta/record_ui_event/
get_recommendation_reason_panel）全部不存在。每次请求直接查库，无缓存。

`_build_freshness()` 用 `_utc_now()` 作为 `data_asof`，cache_age 永远 ≈ 0，
FreshnessMeta 永远 "fresh"，新鲜度机制名存实亡。

### G-08 FilterService 整层缺失 `P0`

设计 5 个方法（apply_filters/apply_sort/paginate/resolve_filter_config/build_filter_preset_badges）。
代码中 `FilterConfig` 参数被接受但 **SQL 查询完全不使用任何过滤条件**。

```python
# data_service.py — 所有带 filters 参数的方法都存在此问题：
rows = conn.execute(
    "SELECT * FROM integrated_recommendation "
    "WHERE CAST(trade_date AS VARCHAR) = ? "
    "ORDER BY final_score DESC LIMIT ?", [trade_date, top_n])
# ← 没有 WHERE final_score >= fc.dashboard_min_score
```

用户看到的是全量未过滤数据。`build_filter_preset_badges` 虽然生成了徽标文本，
但对应的过滤逻辑不存在——这些徽标是"虚假承诺"。

### G-09 ExportService 整层缺失 `P0`

设计 4 个方法（CSV/Markdown 导出 + 推荐列表导出 + 绩效报告导出）全不存在。
app.py 有不同的导出逻辑（CLI 批量导出 vs 设计的交互式按需导出）。

### G-10 CP-09 最小闭环入口缺失 `P0`

设计: `DataService.run_minimal(trade_date) → GuiRunResult`。
代码: 此方法不存在，无法满足 CP-09 闭环契约。

### G-11 ChartService 缺失 `P1`

设计 3 个方法（temperature_chart/industry_chart/recommendation_scatter）。
代码中图表构建散落在 DataService 内联中，且推荐散点图完全缺失。

### G-12 FormatterService 签名偏差 `P2`

- `format_temperature` 多了 `trend` 参数（轻微）
- `format_pnl` 拆分为 `pnl_color`（只返回颜色，不返回格式化金额）

---

## D. 算法逻辑差异

### G-13 所有指标分级算法已正确实现 ✅

温度颜色、推荐等级、轮动状态、机会等级、周期映射、趋势图标、盈亏颜色——全部与设计一致。

### G-14 默认过滤条件全部未实现 `P0`（归入 G-08）

| 页面 | 设计要求的过滤 | 代码 |
|------|---------------|------|
| Dashboard | `final_score >= dashboard_min_score` | ❌ 无过滤 |
| IRS | `rank <= max_rank, rotation_status IN ...` | ❌ 无过滤 |
| PAS | `opportunity_score >= min_score, grade >= level` | ❌ 无过滤 |
| 集成推荐 | `final_score >= min_score, position >= min_position` | ❌ 无过滤 |

### G-15 排序字段仅实现主排序，次排序全缺 `P1`

| 页面 | 设计次排序 | 代码 |
|------|-----------|------|
| Dashboard 推荐 | `stock_code ASC` | ❌ |
| IRS 行业 | `industry_score DESC` (按 rank 仅单字段) | ❌ |
| PAS 个股 | `neutrality ASC` | ❌ |
| 集成推荐 | `position_size DESC` | ❌ |
| 交易记录 | `trade_date DESC` | ❌ |
| 持仓列表 | `unrealized_pnl DESC` | ❌ |

### G-16 缓存策略完全未实现 `P0`（归入 G-07）

设计定义 4 类 TTL（24h/1min/24h/会话级），代码有 `_FRESHNESS_TTL` 字典但从未使用。

### G-17 温度曲线缺 zones `P1`

代码构建了 x_axis + y_axis，但设计要求的 4 色 zones 背景域完全未实现。

### G-18 IRS 图表颜色偏差 `P3`

设计: IN→green, HOLD→**gray**, OUT→gray（二色）。
代码: IN→green, HOLD→**orange**, OUT→gray（三色）。

### G-19 推荐散点图完全未实现 `P2`

设计中的 `transform_recommendation_scatter()` 不存在，Dashboard 仅有 dataframe 表格。

---

## E. 信息流差异

### G-20 CP-09 闭环流程偏离（归入 G-10）

设计: `run_minimal → render Dashboard + Integrated → GuiRunResult(渲染状态)`。
代码: 两个独立模式——export_mode 写 artifacts 或 launch_dashboard 启动 Streamlit 全部 7 页。

### G-21 导出范式完全不同 `P1`

设计 = 交互式按需导出（Streamlit 中点击按钮 → `.reports/gui/xxx.csv`）。
代码 = CLI 批量导出（`eq gui --export daily-report` → `artifacts/spiral-s5/{date}/`）。

### G-22 推荐原因联动流完全未实现 `P2`

设计: 用户点击推荐项 → `get_recommendation_reason_panel()` → 读取 L4 归因数据 → 侧边栏展示。
代码: Integrated 页面仅展示 dataframe，无点击联动。

### G-23 可观测性完全未实现 `P2`

设计要求 logger + metrics 记录 UI 事件（timeout/empty_state/data_fallback）。代码无任何 UI 事件记录。

---

## F. 回测-GUI 集成差异

### G-24 BacktestSummaryDisplay 字段映射错误 `P2`

| GUI 读取 | 回测写入 | 状态 |
|----------|---------|------|
| `backtest_name` | 不存在（只有 `backtest_id`） | ❌ 读到空 |
| `annual_return` | 不存在 | ❌ 永远 0 |
| `sharpe_ratio` | 不存在 | ❌ 永远 0 |
| `total_return` | ✅ | |
| `max_drawdown` | ✅ | |

### G-25 performance_metrics 表生产者不明确 `P2`

GUI 从 `performance_metrics` 表读取 8 个指标。
回测不写此表（仅写 `backtest_results`），Analysis 向此表写入但 7 个指标硬编码 0.0。
所以 GUI 绩效显示全为 0。
