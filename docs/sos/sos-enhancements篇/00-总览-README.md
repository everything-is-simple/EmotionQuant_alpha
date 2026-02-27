# SOS：系统代码与核心设计的差异急救方案（enhancements 篇）

**检查日期**: 2026-02-27
**检查范围**: `docs/design/enhancements/` 全部 6 份设计文档 vs `src/` 实际代码
**检查方法**: 逐条对照设计规格与实际实现，记录偏差

---

## 检查结论概览

| 差异等级 | 数量 | 说明 |
|---------|------|------|
| 🔴 严重（设计有/代码完全缺失或方向性偏差） | 5 | ENH-09 Qlib 适配层、监控告警模块、SHA256 冻结检查、金丝雀 parquet 数据包、validate_token() |
| 🟡 中等（已实现但与设计规格有偏差） | 7 | error_manifest 格式、调度器重试策略、A/B/C 对照分组、异常体系命名、目录结构、ENH-01 框架选型、DAG 编排 |
| 🟢 轻微（基本对齐，命名/路径微调即可） | 3 | ENH-10 采集增强、ENH-11 调度器骨架、L4 产物标准化 |

---

## 分文件索引

| 文件 | 覆盖范围 | 严重度 |
|------|---------|--------|
| `01-ENH-01-统一运行入口-差异报告.md` | ENH-01 CLI 统一入口 | 🟡 中 |
| `02-ENH-02-数据预检与限流-差异报告.md` | ENH-02 token 预检 / 限流 / 异常体系 | 🔴🟡 |
| `03-ENH-03-失败产物协议-差异报告.md` | ENH-03 error_manifest 统一协议 | 🟡 中 |
| `04-ENH-04-05-契约测试与金丝雀-差异报告.md` | ENH-04 契约测试目录 + ENH-05 金丝雀数据包 | 🔴🟡 |
| `05-ENH-06-09-对照看板-冻结检查-Qlib-差异报告.md` | ENH-06/07/08/09 | 🔴🟡 |
| `06-ENH-10-11-调度监控-差异报告.md` | ENH-10/11 + scheduler-orchestration-design + monitoring-alerting-design | 🔴🟡 |
| `07-目录结构与命名规范-差异报告.md` | 设计文档指定的目录布局 vs 实际目录 | 🟡 中 |

---

## 整体风险评估

### 需要优先处理的阻断级问题

1. **ENH-09 Qlib 适配层完全缺失** — 设计文档明确为"核心诉求必需项"，代码中无任何 `qlib_adapter` 实现
2. **监控告警模块仅占位** — `monitoring-alerting-design.md` 定义了完整的 P0/P1/P2 体系，`src/monitoring/quality_monitor.py` 只有 `raise NotImplementedError`
3. **ENH-08 设计冻结检查实现方向偏离** — 设计要求 SHA256 hash 锚点检测文档变更，实际实现为 DESIGN_TRACE 标记检查（功能本质不同）

### 需要对齐的兼容级问题

4. error_manifest 缺少 `error_level`(P0/P1/P2)、`failed_step`、`timestamp` 字段
5. 调度器重试策略偏离设计（固定 5min vs 指数退避 30s-480s；3 次 vs 5 次）
6. A/B/C 对照分组中 C 组应为等权持有，实际用技术基线替代
7. `validate_token()` 预检函数完全缺失
8. 目录结构：`src/adapters/`、`tests/contracts/`、`tests/canary/` 均不存在

---

## 建议处理策略

**方案 A（修订设计对齐代码）**: 对于代码实现实际上更合理的差异（如 argparse 替代 Typer、DESIGN_TRACE 替代 SHA256），考虑反向修订设计文档。

**方案 B（修订代码对齐设计）**: 对于代码明确缺失或偏离核心意图的差异（如 Qlib 适配层、监控模块、validate_token），需要补齐代码实现。

**方案 C（双向对齐）**: 对于双方都有道理的差异（如 error_manifest 格式、目录结构），需要讨论后统一口径。

---

## 参照设计文档清单

- `docs/design/enhancements/eq-improvement-plan-core-frozen.md` — 执行主计划
- `docs/design/enhancements/enhancement-selection-analysis_claude-opus-max_20260210.md` — 外挂选型权威设计
- `docs/design/enhancements/scheduler-orchestration-design.md` — 调度与编排设计
- `docs/design/enhancements/monitoring-alerting-design.md` — 监控与告警设计
- `docs/design/enhancements/debt-clearance-plan-v1.md` — 债务清偿计划
- `docs/design/enhancements/README.md` — 外挂增强设计目录
