# Enhancements 模块 — 代码-设计偏差总览

## 审计范围

| 维度 | 对象 |
|------|------|
| 设计文档 | `docs/design/enhancements/` 全部 6 份设计文档 |
| 代码 | `src/pipeline/`, `src/data/`, `src/monitoring/`, `src/adapters/`, `scripts/quality/`, `tests/` |

覆盖 ENH-01~11 增强项 + `scheduler-orchestration-design` + `monitoring-alerting-design`。

## 问题统计

| 严重程度 | 数量 | 关键问题 |
|----------|:---:|------|
| 🔴 致命 | 5 | Qlib 适配层完全缺失、监控模块仅占位(16行)、SHA256 冻结检查方向偏离、金丝雀 parquet 缺失、validate_token() 缺失 |
| 🟡 中等 | 7 | error_manifest 格式不统一、调度器重试策略偏离、A/B/C 对照分组 C 组缺失、异常类命名不匹配、目录结构偏差、DAG 编排未完整实现、调度窗口未实现 |
| 🟢 轻微 | 3 | ENH-10 采集增强(已完整)、ENH-11 调度器骨架(已完整)、L4 产物标准化(基本对齐) |
| **合计** | **15** | |

## 致命问题速览

1. **ENH-09 Qlib 适配层完全缺失** — 设计标记为"核心诉求必需项"，代码中零 Qlib 代码。
   回测用本地向量化引擎，需要明确裁决是否保留 Qlib 路径。（AD-03 已裁决：Qlib 为唯一回测引擎）
2. **监控告警模块仅占位** — `quality_monitor.py` 只有 16 行 + `raise NotImplementedError`。
   设计定义了完整 P0/P1/P2 体系、6 层监控、9 条指标、升级规则。
3. **ENH-08 冻结检查方向偏离** — 设计要 SHA256 hash 检测文档变更，
   代码做的是 DESIGN_TRACE 标记检查代码溯源（解决不同问题）。
4. **ENH-05 金丝雀 parquet 缺失** — 设计要求 10 天 × 8 表 × 50-100 只的 parquet 包，
   实际只有一个交易日历 JSON。SimulatedTuShareClient 作为替代但数据嵌入被测代码中。
5. **validate_token() 缺失** — 无 token 预检，失败在首次正式请求才暴露。

## 亮点

- **ENH-10 数据采集增强**: 分批下载/断点续传/多线程全部实现，与设计高度对齐
- **ENH-11 调度器骨架**: CalendarGuard/幂等检查/执行日志全部实现
- **ENH-01 CLI 入口**: 19 个子命令全部有实现支撑，设计仅列 7 个

## 文件索引

| 文件 | 内容 |
|------|------|
| `01-gap-inventory.md` | 15 项偏差逐条清单（按 ENH 编号组织） |
| `02-risk-assessment.md` | 风险评级 + Qlib 裁决影响分析 |
| `03-remediation-plan.md` | 分批修复方案 + 开放决策点 |
