# ENH-06/07/08/09 — 设计 vs 代码差异报告

**严重度**: 🔴 严重（ENH-09 Qlib 适配层）+ 🔴 严重（ENH-08 方向偏差）+ 🟡 中等（ENH-06/07）
**涉及设计**: `enhancement-selection-analysis` §2 ENH-06~09
**涉及代码**: `src/analysis/benchmark_comparison.py`, `src/gui/app.py`, `scripts/quality/design_traceability_check.py`, `src/` 全局

---

## ENH-06 A/B/C 对照看板

### 1.1 🟡 对照分组与设计不完全匹配

| 维度 | 设计规格 | 实际代码 |
|------|---------|---------|
| A 组 | 情绪主线（系统信号） | MSS 信号 ✅ |
| B 组 | 随机选股 | 随机选股（`generate_random_signals`） ✅ |
| C 组 | **等权买入持有** | ❌ **不存在**（被技术基线替代） |
| D 组（可选） | 技术指标基线（仅对照） | MA5/MA20+RSI+MACD 投票 ✅ |

**详情**: 设计明确 C 组是等权买入持有（buy & hold），D 组是可选的技术基线。实际代码中没有等权持有组，技术基线直接成为了 C 组。

**影响**: 缺少最基础的 buy & hold 基准，无法证明系统跑赢了"什么都不做"的策略。

**实际代码结构**:
- `BenchmarkResult`: strategy_name, total_return, max_drawdown, win_rate, sharpe_ratio 等 ✅
- `BenchmarkComparisonResult`: mss_result, random_result, technical_result ✅
- `generate_random_signals()`: 随机选股生成器 ✅
- `compute_technical_signals()`: MA/RSI/MACD 技术信号计算 ✅

---

### 1.2 建议

| 编号 | 动作 | 方向 | 优先级 |
|------|------|------|--------|
| R06-1 | 补齐等权买入持有基准（C 组），将技术基线改回 D 组 | 修订代码 | P1 |
| R06-2 | `BenchmarkComparisonResult` 增加 `buyhold_result` 字段 | 修订代码 | P1 |

---

## ENH-07 L4 产物标准化

### 2.1 🟢 基本对齐

| 维度 | 设计规格 | 实际代码 | 状态 |
|------|---------|---------|------|
| 日报导出 | 固定 Markdown 模板 | `src/gui/app.py` → `run_gui(export_mode="daily-report")` | ✅ 有 |
| 命名规范 | `{name}_{YYYYMMDD}_{HHMMSS}.md` | 需确认具体命名 | 🟡 待验 |
| 实施阶段 | S5 | S5 GUI 闭环 ✅ | ✅ 对齐 |

**结论**: 大体对齐，命名规范需细查。

### 2.2 建议

| 编号 | 动作 | 方向 | 优先级 |
|------|------|------|--------|
| R07-1 | 确认日报文件命名是否符合 `{name}_{YYYYMMDD}_{HHMMSS}.md` 规范 | 检查代码 | P3 |

---

## ENH-08 设计冻结检查

### 3.1 🔴 实现方向与设计完全不同

| 维度 | 设计规格 | 实际代码 |
|------|---------|---------|
| 脚本名 | `scripts/quality/freeze_check.py` | `scripts/quality/design_traceability_check.py` |
| 检查机制 | **SHA256 hash 锚点** — 对核心设计文件计算哈希，与 `freeze_anchors.json` 比对 | **DESIGN_TRACE 标记** — 检查代码文件中是否含有 `DESIGN_TRACE` 字典 |
| 检测目标 | **设计文档是否被修改** | **代码是否标注了设计溯源** |
| 锚点文件 | `freeze_anchors.json` | 不存在 |
| 阻断规则 | 任一锚点变化且无审查记录时 P0 失败 | 标记缺失时返回非零退出码 |

**核心差异**: 这两种实现解决的是**不同的问题**：
- 设计要的是"守卫设计文档不被意外修改"（文档变更检测）
- 实际做的是"确保代码可以追溯到设计文档"（代码溯源检查）

两者互补但不等价。设计的核心意图（SHA256 守卫）在代码中完全未实现。

---

### 3.2 代码实际覆盖的模块（`REQUIRED_TRACE_MARKERS`）

设计溯源检查覆盖了 17 个核心模块文件，检查它们是否包含 `DESIGN_TRACE` 标记和对应的设计文档路径引用。这个功能本身有价值，但不是 ENH-08 设计要求的。

---

### 3.3 建议

| 编号 | 动作 | 方向 | 优先级 |
|------|------|------|--------|
| R08-1 | 新建 `scripts/quality/freeze_check.py` 实现 SHA256 hash 锚点检查 | 修订代码 | **P0** |
| R08-2 | 生成 `freeze_anchors.json` 基线文件 | 修订代码 | **P0** |
| R08-3 | 保留现有 `design_traceability_check.py` 作为互补功能（非 ENH-08 替代品） | 保持现状 | — |
| R08-4 | 设计文档补充 DESIGN_TRACE 溯源检查作为 ENH-08 的扩展能力 | 修订设计 | P2 |

---

## ENH-09 Qlib 适配层

### 4.1 🔴 完全缺失

| 维度 | 设计规格 | 实际代码 |
|------|---------|---------|
| 文件 | `src/adapters/qlib_adapter.py` | **不存在** |
| 目录 | `src/adapters/` | **不存在**（适配器在 `src/data/adapters/`） |
| `to_qlib_signal()` | 将 `integrated_recommendation` 转为 Qlib 信号格式 | **不存在** |
| `from_qlib_result()` | 将 Qlib 回测结果转回标准格式 | **不存在** |
| 实施阶段 | S3 | — |

**搜索结果**: 在整个 `src/` 目录中搜索 `qlib_adapter`、`qlib_signal`、`to_qlib`，结果均为零匹配。

---

### 4.2 实际回测实现方式

`src/backtest/pipeline.py` (77KB) 实现了一个完整的本地向量化回测器，直接消费 DuckDB 中的推荐数据。没有任何 Qlib 集成代码。

| 维度 | 设计预期 | 实际实现 |
|------|---------|---------|
| 回测主引擎 | Qlib（通过适配层） | 本地向量化回测器（无 Qlib） |
| 信号来源 | `integrated_recommendation` → Qlib 信号 | `integrated_recommendation` → 直接消费 |
| 结果格式 | Qlib 结果 → 标准格式转换 | 直接输出标准格式 |

---

### 4.3 核心问题

设计文档将 ENH-09 标记为 **"核心诉求必需项"**（enhancement-selection-analysis §3），裁决为 **"必留 ✅"**，核心链路依赖度标为 **"最高：核心诉求"**。但代码中完全没有实现，也没有任何 Qlib 相关代码。

系统总览 §2.3 也明确写了 "回测主选：Qlib"。

---

### 4.4 建议

| 编号 | 动作 | 方向 | 优先级 |
|------|------|------|--------|
| R09-1 | 创建 `src/adapters/qlib_adapter.py` 实现 `to_qlib_signal()` 和 `from_qlib_result()` | 修订代码 | **P0** |
| R09-2 | 或者：如果决定不使用 Qlib，则修订设计文档和系统总览，将本地向量化回测器定为主引擎 | 修订设计 | **P0** |
| R09-3 | 无论选哪条路，需要做一个明确的裁决并记录 | 决策 | **P0** |

**注意**: 这是一个需要明确决策的问题。如果本地回测器已经满足需求，那么 Qlib 适配层可能不是必需的——但此时设计文档的多处描述需要全面修订。
