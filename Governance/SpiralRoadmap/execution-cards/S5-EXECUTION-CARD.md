# S5 执行卡（v1.0）

**状态**: Active  
**更新时间**: 2026-02-26  
**阶段**: 阶段C（S5-S7a）  
**微圈**: S5（展示闭环：全7页 + 日报导出 + FreshnessMeta/FilterConfig/pnl_color）

---

## 1. 目标

- 完成 GUI 全7页（Dashboard/MSS/IRS/PAS/Integrated/Trading/Analysis）只读展示，不在页面层执行算法计算。
- 日报导出可用，且输入可追溯到 L1/L2/L3 与参数快照。
- 落地 FreshnessMeta/FilterConfig/pnl_color 三项设计约束。
- 固化阶段B参数消费口径，为 S6 稳定化重跑提供展示基线。

---

## 2. Scope（本圈必须/禁止）

- In Scope：DataService 7页数据读取、FreshnessMeta 三态、FilterConfig 来源追溯、pnl_color A股红涨绿跌、日报导出、gate_report §Design-Alignment-Fields。
- Out Scope：CacheService TTL 策略、UiObservabilityPanel 全量实现、PermissionConfig 权限分级、PDF 导出、RecommendationReasonPanel 联动面板、全量组件库（temperature_card/cycle_badge 等独立组件）。

---

## 3. 模块级补齐任务（全部必做）

| 模块 | 必须补齐 | 设计依据 | 验收要点 |
|---|---|---|---|
| DataService | 7个 `get_*_page_data` 方法，从 DuckDB 只读消费 L3/L4 产物；不做算法计算 | `docs/design/core-infrastructure/gui/gui-api.md` §2 DataService | 每个方法返回对应 PageData dataclass；数据来源可审计 |
| FreshnessMeta | `FreshnessMeta` dataclass + `FreshnessLevel` 枚举（fresh/stale_soon/stale），Dashboard 与 Integrated 页面嵌入 | `docs/design/core-infrastructure/gui/gui-data-models.md` §1.12 FreshnessMeta | 三态可触发；`data_asof` 与 `cache_age_sec` 可追溯 |
| FilterConfig | `FilterConfig` dataclass（dashboard_min_score/integrated_min_score/integrated_min_position/source），Dashboard 显示 `active_filter_badges` | `docs/design/core-infrastructure/gui/gui-data-models.md` §4.2 FilterConfig | `source` 可审计（env_default/user_override/session_override） |
| pnl_color | Trading 页面 `PositionDisplay.pnl_color`：>0 red / <0 green / =0 gray（A股红涨绿跌） | `docs/design/core-infrastructure/gui/gui-data-models.md` §5.2 字段映射 | 与 §5.2 转换规则一致 |
| 7 页面渲染 | Dashboard/MSS/IRS/PAS/Integrated/Trading/Analysis 只读 Streamlit 页面，消费 DataService 输出 | `docs/design/core-infrastructure/gui/gui-api.md` §1 模块结构（pages/） | 每页可启动、只读展示、不做算法计算 |
| 日报导出 | `eq gui --export daily-report` 产出 `daily_report_sample.md` + `gui_export_manifest.json` | `docs/design/core-infrastructure/gui/gui-algorithm.md` §2 每日导出流程 | 导出可追溯到 pipeline 产物 |

---

## 4. run

**baseline**（圈前健康检查）：

```bash
pytest tests/unit/gui/test_gui_launch_contract.py tests/unit/gui/test_gui_readonly_contract.py -q
python -m scripts.quality.local_quality_check --contracts --governance
```

**target**（本圈收口必须成立）：

```bash
eq gui --date {trade_date}
eq gui --date {trade_date} --export daily-report
```

---

## 5. test

**baseline**（已存在）：

```bash
pytest tests/unit/gui/test_gui_launch_contract.py -q
pytest tests/unit/gui/test_gui_readonly_contract.py -q
pytest tests/unit/analysis/test_daily_report_export_contract.py -q
```

**target**（本圈必须补齐并执行）：

```bash
pytest tests/unit/gui/test_freshness_meta_contract.py -q
pytest tests/unit/gui/test_filter_config_contract.py -q
pytest tests/unit/gui/test_pnl_color_contract.py -q
```

验证要点：

- **FreshnessMeta**：`FreshnessLevel`（`fresh/stale_soon/stale`）三态可触发。
- **FilterConfig**：`FilterConfig.source` 可审计（`env_default/user_override/session_override`），Dashboard 显示 `active_filter_badges`。
- **pnl_color**：>0 红 / <0 绿 / =0 灰，与 `gui-data-models.md` §5.2 一致。

---

## 6. artifact

- `artifacts/spiral-s5/{trade_date}/gui_snapshot.png`
- `artifacts/spiral-s5/{trade_date}/daily_report_sample.md`
- `artifacts/spiral-s5/{trade_date}/gui_export_manifest.json`
- `artifacts/spiral-s5/{trade_date}/gate_report.md`（含 §Design-Alignment-Fields：逐字段校验 GUI 核心 dataclass 与 `gui-data-models.md` 一致性）
- `artifacts/spiral-s5/{trade_date}/consumption.md`

---

## 7. review

- 复盘文件：`Governance/specs/spiral-s5/review.md`
- 必填结论：
  - GUI 7页启动与只读约束是否稳定成立
  - `daily_report` 导出链路是否完整可追溯
  - 展示参数是否与 S4b 防御基线一致且无手工覆盖
  - FreshnessMeta 三态是否可触发
  - FilterConfig 来源追溯是否可审计
  - pnl_color 红涨绿跌是否与 gui-data-models §5.2 一致
  - gate_report §Design-Alignment-Fields 字段级校验是否通过

---

## 8. 硬门禁

- 任一页面仍为"占位/不可渲染"，S5 不得标记 `completed`。
- FreshnessMeta 三态不可触发，状态必须置 `blocked`。
- FilterConfig.source 不可审计，状态必须置 `blocked`。
- pnl_color 不符合 A 股红涨绿跌，状态必须置 `blocked`。
- 日报导出链路缺失或不可追溯，不得推进 S6。
- `python -m scripts.quality.local_quality_check --contracts --governance` 未通过时，只允许进入 S5r 修复圈。

---

## 9. sync

- `Governance/specs/spiral-s5/final.md`
- `Governance/record/development-status.md`
- `Governance/record/debts.md`
- `Governance/record/reusable-assets.md`
- `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`

---

## 10. 失败回退

- 若 `gate = FAIL`：状态置 `blocked`，进入 `S5r` 修复子圈，不推进 S6。
- 若发现阶段B归因/防御参数失真：回退 S4b 重校准后再返回 S5。

---

## 11. 关联

- 微圈合同：`Governance/SpiralRoadmap/planA/SPIRAL-S5-S7A-EXECUTABLE-ROADMAP.md`
- 阶段模板：`Governance/SpiralRoadmap/SPIRAL-STAGE-TEMPLATES.md`
- 依赖图：`Governance/SpiralRoadmap/planA/DEPENDENCY-MAP.md`
- GUI 算法设计：`docs/design/core-infrastructure/gui/gui-algorithm.md`
- GUI 数据模型：`docs/design/core-infrastructure/gui/gui-data-models.md`
- GUI API 接口：`docs/design/core-infrastructure/gui/gui-api.md`
- GUI 信息流：`docs/design/core-infrastructure/gui/gui-information-flow.md`

---

## 12. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-02-26 | 升级至 S2c 同精度：新增 Scope、模块级补齐任务表（6模块）、硬门禁、质量检查命令、设计文档交叉引用（4篇）；run/test 改为 baseline+target 双层口径；页面范围扩展至全7页 |
| v0.3 | 2026-02-25 | 补充 FreshnessMeta/FilterConfig/pnl_color 验证要点与 §Design-Alignment-Fields |
| v0.2 | 2026-02-20 | 首版执行卡 |

---

---

## 历史债务挂载（2026-02-26 独立审计）

| 债务 ID | 类型 | 说明 | 处理策略 |
|---|---|---|---|
| TD-DA-009 | 历史债务（未清偿） | Enum 设计-实现对齐缺口（类名/成员/缺失枚举） | 执行本卡时必须在 gate_report.md 给出 Enum 对齐结论（resolved/deferred） |
| TD-DA-010 | 历史债务（后续） | Calculator/Repository 与设计 API 存在方法/签名差距（卡 B 仅完成试点） | 执行本卡时按 ARCH-DECISION-001 二选一：继续对齐实现或下修设计契约 |
| TD-DA-011 | 历史债务（后续） | Integration dual_verify/complementary 与设计语义存在冲突（共识因子/落库字段/权重语义） | 执行本卡时输出语义对齐结论并同步 docs + tests + debts |
| TD-ARCH-001 | 架构决策债务 | OOP 设计口径与 Pipeline 实现口径并存 | 执行本卡时引用 ARCH-DECISION-001，禁止新增口径漂移 |

（2026-02-26）

- `eq gui` 子命令已落地，`daily-report` 导出链路与基础合同测试已打通。
- ✅ 代码补齐完成：`src/gui/models.py`（全部 dataclass）、`src/gui/formatter.py`、`src/gui/data_service.py`、`src/gui/dashboard.py`（7页布局）。
- ✅ 测试补齐完成：35 条 GUI 测试全部通过（test_freshness_meta_contract / test_filter_config_contract / test_pnl_color_contract）。
- 待完成：端到端 artifact 产出 + review/sync 闭环。

