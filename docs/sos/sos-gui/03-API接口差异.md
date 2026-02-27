# 03 API 接口差异

**对比来源**: gui-api.md v3.2.0 vs src/gui/data_service.py + src/gui/formatter.py

---

## 一、DataService 接口对照

### 构造函数 — P0 根本性偏离

| 维度 | 设计 | 代码 |
|------|------|------|
| 签名 | `__init__(self, repository: DataRepository)` | `__init__(self, database_path: Path)` |
| 数据访问 | 通过 DataRepository 抽象层 | 直接 duckdb.connect + 裸 SQL |
| 依赖 | 仓库实例（可 mock 测试） | 文件路径（测试需真实 DB） |

**问题**: DataRepository 抽象层完全不存在。设计中的分层架构被打破。

### 方法签名对照

| 设计方法 | 代码方法 | 状态 | 差异说明 |
|----------|----------|------|----------|
| `get_dashboard_data(trade_date, top_n)` | `get_dashboard_data(trade_date, *, top_n, filters)` | ⚠️ | 代码多了 filters 参数（但未使用） |
| `get_mss_page_data(trade_date, history_days)` | `get_mss_page_data(trade_date, *, history_days)` | ✅ | 签名一致 |
| `get_irs_page_data(trade_date, filters)` | `get_irs_page_data(trade_date, *, filters)` | ⚠️ | filters 未被实际使用 |
| `get_pas_page_data(trade_date, filters, page, page_size)` | `get_pas_page_data(trade_date, *, filters, page, page_size)` | ⚠️ | filters 未被实际使用 |
| `get_integrated_page_data(trade_date, filters, page, page_size)` | `get_integrated_page_data(trade_date, *, filters, page, page_size)` | ⚠️ | filters 未被实际使用 |
| `get_trading_page_data(trade_date, page, page_size)` | `get_trading_page_data(trade_date, *, page, page_size)` | ✅ | 签名一致 |
| `get_analysis_page_data(report_date)` | `get_analysis_page_data(report_date)` | ✅ | 签名一致 |
| `run_minimal(trade_date) → GuiRunResult` | **不存在** | ❌ P0 | CP-09 最小闭环入口缺失 |

### FilterConfig 参数"假接受"问题 — P0

以 `get_dashboard_data` 为例：

```python
# data_service.py:136-137
def get_dashboard_data(
    self, trade_date: str, *, top_n: int = 10, filters: FilterConfig | None = None
) -> DashboardData:
    fc = filters or FilterConfig()  # ← 创建了 FilterConfig
    # ... 但后续 SQL 查询完全不使用 fc 的任何阈值：
    rows = conn.execute(
        "SELECT * FROM integrated_recommendation "
        "WHERE CAST(trade_date AS VARCHAR) = ? "
        "ORDER BY final_score DESC LIMIT ?",
        [trade_date, top_n],
    ).fetchall()
    # ← 没有 WHERE final_score >= fc.dashboard_min_score !!!
```

所有带 `filters` 参数的方法都存在同样问题：参数被接受但从未在 SQL 中使用。

---

## 二、完全缺失的服务层（4个）

### FilterService — P0 缺失

**设计** (gui-api.md §3) 定义了 5 个方法：

| 方法 | 功能 | 代码现状 |
|------|------|----------|
| `apply_filters(items, filters)` | 链式过滤 | ❌ 不存在 |
| `apply_sort(items, sort_fields, directions)` | 多字段排序 | ❌ 不存在 |
| `paginate(items, page, page_size)` | 分页 | ⚠️ data_service.py 有 `_paginate` 但仅计算 PaginationInfo |
| `resolve_filter_config(page_name, override)` | 阈值配置解析 | ❌ 不存在 |
| `build_filter_preset_badges(page_name, filter_config)` | 阈值徽标 | ⚠️ 在 formatter.py 中实现（位置偏离） |

**急救方案**:
- 至少在 data_service.py 中实现过滤和排序逻辑
- 或在 formatter.py 中补齐 `apply_filters` 和 `apply_sort`
- `resolve_filter_config` 需新增，支持环境配置 + 用户覆盖

### CacheService — P0 缺失

**设计** (gui-api.md §7) 定义了 6 个方法：

| 方法 | 功能 | 代码现状 |
|------|------|----------|
| `get_cached(cache_key)` | 获取缓存 | ❌ 不存在 |
| `set_cached(cache_key, data, ttl)` | 设置缓存 | ❌ 不存在 |
| `build_cache_key(data_type, trade_date, filters)` | 缓存键生成 | ❌ 不存在 |
| `get_freshness_meta(cache_key)` | 新鲜度元信息 | ⚠️ data_service.py 有 `_build_freshness` 但用 now() 伪造 |
| `record_ui_event(page_name, event_type, trace_id)` | UI 事件记录 | ❌ 不存在 |
| `get_recommendation_reason_panel(stock_code, trade_date)` | 推荐原因面板 | ❌ 不存在 |

**当前 FreshnessMeta 的问题**:
```python
# data_service.py:62-85
def _build_freshness(data_asof: str, ttl_key: str = "l3_daily") -> FreshnessMeta:
    now = _utc_now()
    cache_created = now.isoformat()
    # data_asof 参数通常传入的就是 now_iso:
    #   now_iso = _utc_now().isoformat()
    #   freshness = _build_freshness(now_iso)
    # 所以 age_sec ≈ 0，永远是 "fresh"
```

设计中的新鲜度是基于真实缓存年龄（数据写入时间 vs 当前时间），但代码用当前时间作为 data_asof，导致 age 永远为 0。

**急救方案**:
- 引入 Streamlit `st.cache_data` 或 dict 缓存
- data_asof 应从 DB 数据的实际时间戳读取（如 mss_panorama.trade_date 的最新日期）

### ExportService — P0 缺失

**设计** (gui-api.md §5) 定义了 4 个方法：

| 方法 | 功能 | 代码现状 |
|------|------|----------|
| `export_to_csv(data, columns, filename)` | CSV 导出 | ❌ 不存在 |
| `export_to_markdown(content, filename)` | Markdown 导出 | ❌ 不存在（app.py 有不同的 MD 导出逻辑） |
| `export_recommendations(trade_date, filters)` | 推荐列表导出 | ❌ 不存在 |
| `export_performance_report(report_date)` | 绩效报告导出 | ❌ 不存在 |

**急救方案**: 如果交互式导出是 MVP 需求，需新建 ExportService；否则标记为 P2 延后

### ChartService — P1 缺失

**设计** (gui-api.md §6) 定义了 3 个方法：

| 方法 | 功能 | 代码现状 |
|------|------|----------|
| `build_temperature_chart(mss_history)` | 温度曲线（含 zones） | ⚠️ data_service.py 内联构建（无 zones） |
| `build_industry_chart(industries, top_n)` | 行业柱状图 | ⚠️ data_service.py 内联构建 |
| `build_recommendation_scatter(recommendations)` | 推荐散点图 | ❌ 不存在 |

---

## 三、FormatterService 对照

设计 (gui-api.md §4) 中的 FormatterService 方法 vs formatter.py 实现：

| 设计方法 | 代码函数 | 状态 |
|----------|----------|------|
| `format_temperature(temperature) → TemperatureCardData` | `format_temperature(temperature, trend)` | ⚠️ 签名多了 trend 参数 |
| `format_cycle(cycle) → CycleBadgeData` | `format_cycle(cycle)` | ✅ 一致 |
| `format_trend(trend) → Tuple[str, str]` | `format_trend(trend)` | ✅ 一致 |
| `format_percent(value, with_sign) → str` | `format_percent(value, *, with_sign)` | ✅ 一致 |
| `format_pnl(value) → Tuple[str, str]` | `pnl_color(value) → str` | ⚠️ 功能拆分：只返回颜色，不返回格式化金额 |

**format_pnl 差异详解**:
- 设计: 返回 `("+1,234.56", "red")` — 格式化金额 + 颜色
- 代码: `pnl_color(value)` 只返回颜色字符串，金额格式化在 dashboard.py 中用 f-string 实现

**急救方案**: 考虑在 formatter.py 中补齐完整的 `format_pnl` 函数

---

## 四、急救方案优先级总表

| 缺失项 | 优先级 | 方案 |
|--------|--------|------|
| DataService.run_minimal | P0 | 新增方法，实现 CP-09 闭环 |
| FilterService (过滤逻辑) | P0 | 在 data_service.py 中补齐 SQL WHERE 条件 |
| CacheService (基础缓存) | P0 | 引入 st.cache_data 或 dict 缓存 |
| FreshnessMeta 真实性 | P0 | data_asof 改为从 DB 读取实际时间 |
| DataRepository 抽象层 | P1 | 要么补齐仓库层，要么修订设计降级为直连 |
| ExportService | P1 | 按需实现（MVP 可延后） |
| ChartService | P1 | 提取为独立函数集 + 补齐散点图 |
| record_ui_event | P2 | 补齐 logger 记录 |
| get_recommendation_reason_panel | P2 | 依赖上游 L4 数据，条件就绪后实现 |
