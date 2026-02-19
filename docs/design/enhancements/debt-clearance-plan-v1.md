# EmotionQuant 技术债清偿与落地对齐方案（v1）

**状态**: 可执行草案（建议纳入，已对齐当前 SoT）  
**创建日期**: 2026-02-19  
**适用范围**: S3ar -> S3b -> S5 -> S6 -> S7a

---

## 0. 文档定位（防止设计-实现脱节）

1. 本文是 `eq-improvement-plan-core-frozen.md` 的辅助执行清单，不替代主计划。
2. 本文只做债务收敛和实现排期，不改 `docs/design/**` 核心语义。
3. 每项债务必须落到 `run + test + artifact + review + sync` 五件套。

权威入口：

- 核心计划：`docs/design/enhancements/eq-improvement-plan-core-frozen.md`
- 路线主控：`Governance/Capability/SPIRAL-CP-OVERVIEW.md`
- 债务账本：`Governance/record/debts.md`
- TuShare 通道口径：`docs/reference/tushare/tushare-channel-policy.md`

---

## 1. 采纳结论

结论：**可以采纳，但必须按本版修订口径执行**。

已修订的关键对齐点：

1. 通道策略统一为双 TuShare：`10000 网关主通道` + `5000 官方兜底通道`。
2. AKShare/BaoStock 明确为最后底牌预留，当前圈不实装。
3. 圈号改为当前有效路线：`S3ar -> S3b -> S5 -> S6 -> S7a`。
4. 所有债务项增加 CP 映射、闭环证据、阻断条件与退出条件。
5. S3ar/S3b 四列表执行拆解见 `Governance/SpiralRoadmap/S3AR-S3B-EXECUTABLE-TASKLIST.md`。

---

## 2. 当前债务全景（与 `Governance/record/debts.md` 对齐）

| 债务 ID | 优先级 | 当前状态 | 计划圈 | CP 映射 | 说明 |
|---|---|---|---|---|---|
| TD-S3A-014 | P0 | 🔄 处理中 | S3ar | CP-01 | DuckDB 锁恢复证据链不完整 |
| TD-S0-004 | P1 | 🔄 处理中 | S3b/S5 | CP-06, CP-07 | 一字板/流动性细则待补齐 |
| TD-S0-006 | P1 | ⏳ 待处理 | S5 | CP-01, CP-03 | SW 行业映射聚合未接入 |
| TD-S0-002 | P2 | ⏳ 待处理 | S3b | CP-10, CP-06 | Validation 统计校准待收口 |
| TD-S1-008 | P2 | ⏳ 待处理 | S3b | CP-02, CP-10 | 探针收益口径待真实化 |
| TD-GOV-012 | P2 | 🔄 处理中 | S5/S6 | 全 CP | DESIGN_TRACE 覆盖未全量 |
| TD-S0-005 | P2 | ⏳ 待处理 | S6 | 治理层 | Phase 历史措辞残留 |
| TD-S1-007 | P2 | ⏳ 待处理 | S6 | CP-02 | MSS 固定阈值待自适应增强 |
| TD-S3A-015 | P2 | ⏳ 待处理 | S7a | CP-01 | AK/Bao 适配器预留未实装 |

---

## 3. 路线图（只排可执行项）

### 3.1 S3ar（当前进行中，先收口）

目标：先解阻断项，保证后续 S3b 归因数据可稳定复现。

1. 完成 `TD-S3A-014`：锁等待、重试、失败证据链完整落袋。
2. 固化双 TuShare 主备压测基准（主：10000 网关；备：5000 官方）。
3. 输出可审计采集证据：`fetch_progress`、`fetch_retry_report`、限速实测报告。

### 3.2 S3b（紧随 S3ar）

目标：先补解释力，再做更大范围扩展。

1. `TD-S0-002`：回测收益与统计收益校准对齐。
2. `TD-S1-008`：探针收益改为真实收益序列口径（含 T+1/成本）。
3. `TD-S0-004`：先交付日线保守版一字板/流动性规则（可运行版本）。

### 3.3 S5（展示前补齐数据粒度）

1. `TD-S0-006`：接入 SW 行业映射聚合，打通 IRS 行业粒度输入。
2. `TD-GOV-012`：补齐 Data/Signal/Backtest/Trading 模块 DESIGN_TRACE 覆盖。
3. `TD-S0-004`：如分钟级数据能力稳定，再做增强版撮合细则。

### 3.4 S6（稳定化清偿圈）

1. `TD-S1-007`：MSS 自适应阈值（固定阈值保留 fallback）。
2. `TD-S0-005`：清理无效 Phase 措辞并同步治理文档。
3. `TD-GOV-012`：全仓复核，补齐漏网模块。

### 3.5 S7a（运维增强圈）

1. `TD-S3A-015`：AKShare/BaoStock 作为最后底牌接入适配层。
2. 保持主链不变：主链仍是双 TuShare，AK/Bao 仅兜底。

---

## 4. 数据采集主备策略（执行口径）

1. 主通道：`TUSHARE_PRIMARY_*`（10000 网关，覆盖广，速度较慢）。
2. 兜底通道：`TUSHARE_FALLBACK_*`（5000 官方，速度快）。
3. 切换触发：主通道失败、超时、连接重置、重试耗尽。
4. 限速策略：默认全局 `TUSHARE_RATE_LIMIT_PER_MIN`，主备可单独覆盖。
5. 当前不引入第三主线数据源；AK/Bao 仅登记为 S7a 预留。

---

## 5. 每项债务的最小交付定义（DoD）

### TD-S3A-014（P0）

1. run：历史窗口采集重跑可通过，不因锁冲突整体阻断。
2. test：锁重试/超时/恢复单测通过。
3. artifact：锁等待指标、失败重试记录、恢复结果三件套。
4. sync：更新 `debts.md`、`development-status.md`、当圈 `final.md/review.md`。

### TD-S0-004（P1）

1. 先交付日线保守版规则（不等待分钟级前置条件）。
2. 分钟级增强只在通道能力验证通过后启用。
3. 回测与纸上交易两侧规则一致，禁止双口径。

### TD-S0-006（P1）

1. 至少覆盖申万一级行业全量映射。
2. 产出行业聚合快照并通过 IRS 合同测试。
3. 数据缺口要可追踪，不能静默回退为全市场聚合。

### TD-S0-002 / TD-S1-008（P2）

1. 真实收益口径纳入 T+1、交易成本、可成交约束。
2. 统计校准报告需包含偏差分解和容差判定。
3. 校准未达标时必须在 Gate 侧给出 WARN/FAIL 依据。

### TD-S1-007（P2）

1. 自适应阈值可配置、可回退固定阈值。
2. 回归测试必须证明“自适应关闭时行为不变”。

### TD-GOV-012 / TD-S0-005 / TD-S3A-015

1. DESIGN_TRACE 覆盖和 Phase 清理必须有自动检查命令。
2. AK/Bao 接入前先完成字段映射与契约测试，不直接入主链。

---

## 6. 风险与缓解

| 风险 | 影响 | 缓解策略 |
|---|---|---|
| 网关高并发超时/连接重置 | 采集中断，S3b 证据不稳定 | 主备分流 + 重试退避 + 批次断点续传 |
| 分钟级数据能力不稳定 | TD-S0-004 增强版延期 | 先上日线保守版，保证规则闭环 |
| SW 映射缺口 | IRS 行业解释力不足 | 映射表版本化，缺口显式记录 |
| 多源适配引入字段漂移 | 契约破坏 | 先做适配层契约测试，再开放兜底 |

---

## 7. 执行检查清单（每圈收口必做）

1. `python -m scripts.quality.local_quality_check --contracts --governance`
2. 更新 `Governance/specs/spiral-s{N}/final.md`
3. 更新 `Governance/record/development-status.md`
4. 更新 `Governance/record/debts.md`
5. 更新 `Governance/record/reusable-assets.md`
6. 更新 `Governance/Capability/SPIRAL-CP-OVERVIEW.md`（仅状态）

---

## 8. 最终判定标准

满足以下条件才可声明“债务清偿方案落地有效”：

1. P0/P1 债务全部有明确圈号与可复现证据。
2. 数据采集主备策略在真实窗口可稳定重跑。
3. 设计与实现双向可追溯：设计条目可定位到代码与测试，代码可定位回设计条目。
4. 没有“文档已更新但代码未落地”或“代码已改但路线图未同步”的漂移项。

---

## 版本记录

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-02-19 | v1.0 | 首版修订：对齐双 TuShare 主备策略、当前 Spiral 路线与五件套闭环口径 |
