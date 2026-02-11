# EmotionQuant 文档检查报告 — R12

**检查工具**: Warp (claude 4.6 opus max)
**检查时间**: 2026-02-11
**检查范围**: `docs/design/core-infrastructure/data-layer/`（4 文件）
**累计轮次**: R1–R12（R1–R11 已修复 43 项）

---

## 检查范围

| # | 文件 | 结果 |
|---|------|------|
| 1 | algorithm.md | ⚠️ 见 P2-R12-01 |
| 2 | api.md | ⚠️ 见 P2-R12-02 |
| 3 | data-models.md | ⚠️ 见 P2-R12-03 |
| 4 | info-flow.md | ⚠️ 见 P3-R12-04 |

---

## 问题清单

### P2-R12-01 | algorithm.md L3：DDL 字段类型/命名与项目规范不一致

**位置**: algorithm.md §… L3 附近 DDL 定义

**现状**:
- `trade_date DATE` — 项目全局使用 `VARCHAR(8)` 格式（`YYYYMMDD` 字符串）
- `create_time` / `update_time` — 项目规范统一使用 `created_at` / `updated_at`

**问题**: 与项目其他模块（MSS/IRS/PAS/Validation）DDL 约定不一致。

**修复方案**:
- `trade_date DATE` → `trade_date VARCHAR(8)`
- `create_time` → `created_at`
- `update_time` → `updated_at`

---

### P2-R12-02 | api.md §11.4：表名/列名引用错误

**位置**: api.md §11.4

**现状**:
- 引用 `industry_daily` 表 → 实际表名应为 `industry_snapshot`
- 引用 `pct_change` 列 → 实际列名应为 `industry_pct_chg`
- 引用 `daily_bar` / `limit_info` 表 → 这两张表在 data-models DDL 中不存在

**问题**: §11.4 示例代码中的表名和列名与 data-models.md 定义的 DDL 不匹配。

**修复方案**:
- `industry_daily` → `industry_snapshot`
- `pct_change` → `industry_pct_chg`
- 移除或修正对 `daily_bar` / `limit_info` 的引用，改用 data-models.md 中实际定义的表名

---

### P2-R12-03 | data-models.md §3.3：`stock_gene_cache` 缺少质量追踪字段

**位置**: data-models.md §3.3 `stock_gene_cache` 表定义

**现状**: 表中未包含 `data_quality`、`stale_days`、`source_trade_date` 字段。

**问题**: info-flow.md §2.2 明确要求基因缓存必须携带数据质量追踪元数据（`data_quality` 质量等级、`stale_days` 陈旧天数、`source_trade_date` 数据来源交易日），但 DDL 定义中缺失这三个字段。

**修复方案**: 在 `stock_gene_cache` DDL 中补充：
```sql
data_quality VARCHAR(10) DEFAULT 'unknown',
stale_days INT DEFAULT 0,
source_trade_date VARCHAR(8)
```

---

### P3-R12-04 | info-flow.md：§2.2 编号重复

**位置**: info-flow.md 文档中部

**现状**: 文档中出现两个 §2.2 小节，编号重复。

**问题**: 章节编号重复导致交叉引用歧义。

**修复方案**: 将第二个 §2.2 重编号为 §2.3，并顺延后续章节编号。

---

## 统计

| 等级 | 本轮 | 累计 (R1–R12) |
|------|------|---------------|
| P1 | 0 | 1 |
| P2 | 3 | 23 |
| P3 | 1 | 23 |
| **合计** | **4 项** | **47 项** |

---

## 交叉验证确认

- data-layer DDL 表名与 MSS/IRS/PAS 各模块 info-flow 引用的数据源表名交叉核对 ✓
- `industry_snapshot` 表结构与 MSS algorithm §3.1 消费的字段集合核对 ✓
- `stock_gene_cache` 字段需求源自 info-flow §2.2 质量追踪流程规范 ✓
- algorithm.md §… 时间戳命名规范与 Validation/Integration DDL 统一比对 ✓

---

## 下一轮预告

**R13** 预计范围: `docs/design/core-infrastructure/backtest/`（~6 文件）
