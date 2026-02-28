# GUI 模块 — 风险评估

---

## 1. 总体风险定级：🟠 高

GUI 不直接操作资金（风险低于 Trading），但它是**用户决策的唯一视觉入口**。
展示未过滤数据、虚假的新鲜度标记、全为 0 的绩效指标，会导致用户基于错误信息做决策。

**亮点**: 所有指标分级算法（温度颜色、推荐等级、盈亏颜色等）实现正确，
18 个 dataclass + 5 个枚举与设计一致。问题集中在**服务层缺失**而非**算法错误**。

---

## 2. 分层风险分析

### P0 致命 — 7 项

| ID | 问题 | 用户影响 |
|----|------|----------|
| G-01 | 目录结构完全不同 | 不可维护，无法扩展 |
| G-02 | GuiRunResult 同名异义 | CP-09 闭环无法落地 |
| G-06 | DataService 直连 DB | 无法 mock 测试 |
| G-07 | CacheService 全缺 | 每次查库，FreshnessMeta 伪造 |
| G-08 | FilterService 全缺 | **用户看到未过滤全量数据** |
| G-09 | ExportService 全缺 | 无交互式导出 |
| G-10 | CP-09 闭环缺失 | 无法验证 GUI 最小可用性 |

**最严重**: G-08 — 过滤逻辑的缺失意味着用户看到的推荐列表包含低分、低仓位、
不推荐的票，直接影响决策质量。

### P1 严重 — 9 项

| ID | 问题 | 用户影响 |
|----|------|----------|
| G-03 | 7 个数据模型缺失 | 功能不完整 |
| G-04 | 3 个模型字段缺失 | 信息展示不全 |
| G-11 | ChartService 缺失 | 图表功能不完整 |
| G-15 | 次排序全缺 | 排序稳定性差 |
| G-17 | 温度曲线缺 zones | 温度区域无视觉区分 |
| G-21 | 导出范式不同 | 无法在 UI 中导出 |

### P2/P3 — 9 项

功能性影响有限，主要是回测集成字段映射（G-24/G-25 导致绩效显示 0）、
可观测性缺失（G-23）、散点图缺失（G-19）等。

---

## 3. 级联影响

### 过滤缺失 → 决策污染 (G-08)

```
FilterConfig 被接受但未使用
  → 所有页面显示全量数据
    → 低分 / SELL / AVOID 推荐出现在列表中
      → 用户可能误选低质量标的
```

### FreshnessMeta 伪造 → 用户不知数据过时 (G-07)

```
data_asof = _utc_now()
  → cache_age ≈ 0
    → 永远显示 "fresh"
      → 即使 DB 数据已隔天，用户仍认为数据是最新的
```

### performance_metrics 全 0 → 绩效展示误导 (G-25 + Analysis A-01)

```
Analysis 写入 performance_metrics 但 7 个指标 = 0.0
  → GUI Analysis 页面读取
    → 用户看到 Sharpe=0, 年化=0%, Calmar=0
      → 误以为系统无收益
```

---

## 4. 重建方向

**AD-01 设计为权威**，代码对齐设计的 4 层架构：

- `pages/`: 7 个独立页面模块，从 dashboard.py 拆分
- `components/`: 可复用 UI 组件（TemperatureCard, RecommendationTable 等）
- `services/`: DataService (通过 Repository) + CacheService + FilterService + ExportService + ChartService
- `utils/`: formatters + filters + exporters

**不接受**: 保持 5 文件扁平结构并将设计降级为"反映现状"。

**保留**: 所有已正确实现的指标分级算法、18 个 dataclass、5 个枚举——这些是重建的基础。
