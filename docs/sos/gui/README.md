# GUI 模块 — 代码-设计偏差总览

## 审计范围

| 维度 | 对象 |
|------|------|
| 设计文档 | `docs/design/core-infrastructure/gui/` — 4 文档 v3.2.0 |
| 代码 | `src/gui/` (app.py, dashboard.py, data_service.py, formatter.py, models.py) |
| 关联 | `src/backtest/pipeline.py` (回测输出与 GUI Analysis 页面的字段映射) |

## 核心矛盾

```
设计:  4 层目录 (pages/ + components/ + services/ + utils/)  ≈ 18 个模块文件
代码:  扁平结构 5 个文件，无子目录
```

**架构完全不同**。设计是分层组件化 GUI 引擎（CacheService + FilterService +
ExportService + ChartService + 7 个独立页面模块），代码是 Streamlit 直写式单文件应用
（dashboard.py 包含全部 7 页渲染逻辑）。

**关键功能性缺陷**: FilterConfig 参数被接受但从未在 SQL 中使用——用户看到的是全量未过滤数据。

## 问题统计

| 严重程度 | 数量 | 关键问题 |
|----------|:---:|------|
| P0 致命 | 7 | 模块结构完全不同、DataService 构造偏离、GuiRunResult 同名异义、CacheService/FilterService/ExportService 三整层缺失、CP-09 闭环缺失 |
| P1 严重 | 9 | 7 个数据模型缺失、ChartService 缺失、PermissionConfig 缺失 |
| P2 中度 | 6 | FilterConfig 假接受、IRS 颜色偏差、回测字段不匹配、FreshnessMeta 伪造、可观测性缺失、散点图缺失 |
| P3 轻微 | 3 | 文件命名差异、导出路径差异、dashboard.py 双重用途 |
| **合计** | **25** | |

## 跨模块集成断裂

GUI Analysis 页面与回测模块之间存在字段映射问题：
- `backtest_name` — 回测只写 `backtest_id`，GUI 读到空字符串
- `annual_return` / `sharpe_ratio` — 回测 `backtest_results` 表不含这些列，GUI 显示 0
- `performance_metrics` 表 — 生产者不明确（Analysis 模块也硬编码 0）

## 文件索引

| 文件 | 内容 |
|------|------|
| `01-gap-inventory.md` | 25 项偏差逐条清单（6 维度：结构/模型/API/算法/信息流/集成） |
| `02-risk-assessment.md` | 风险评级 + 功能缺陷影响分析 |
| `03-remediation-plan.md` | 分批修复方案 + 架构重建目标 |
