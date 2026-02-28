# R4 Validation + Integration 重建 — 执行卡

**阶段目标**：Validation 从"启发式代理"重写为"真实截面验证 + WFA"；Integration 修复评分和模式语义。
**总工期**：10-12 天
**前置条件**：R2 + R3 完成（依赖正确的 MSS/IRS/PAS 输出）
**SOS 覆盖**：docs/sos/validation 全部 14 项 + docs/sos/integration 全部 19 项

---

## CARD-R4.1: Validation 因子验证核心重写

**工作量**：3 天
**优先级**：P0（核心算法根本性错位）
**SOS 映射**：GAP-01, GAP-02, GAP-03

### 交付物

- [ ] 实现 `ValidatedFactor` 枚举（15 个因子）
  - MSS(6): mss_market_coefficient, mss_profit_effect, mss_loss_effect, mss_continuity_factor, mss_extreme_factor, mss_volatility_factor
  - IRS(6): irs_relative_strength, irs_continuity_factor, irs_capital_flow, irs_valuation, irs_leader_score, irs_gene_score
  - PAS(3): pas_bull_gene_score, pas_structure_score, pas_behavior_score
  - 删除 4 个虚构因子名（irs_pas_coupling 等）
- [ ] 重写 IC 计算
  - 逐日截面：`factor_series` vs `future_returns` 按 `(trade_date, stock_code)` 对齐
  - Pearson IC + Spearman RankIC
  - `mean_ic = mean(daily_ic_series)`
  - `mean_rank_ic = mean(daily_rank_ic_series)`
- [ ] 重写 ICIR
  - **正确**：`icir = mean(ic_series) / std(ic_series)`
  - 删除错误公式 `abs(IC) * sqrt(N)`
- [ ] 实现真实衰减
  - decay_1d / decay_3d / decay_5d / decay_10d
  - 每个持有期独立计算 IC（future_return_Nd）
  - 删除代理公式 `abs(IC) * 2.5`
- [ ] 实现 positive_ic_ratio
  - `positive_ic_ratio = count(daily_ic > 0) / total_days`
- [ ] 实现 coverage_ratio
  - `coverage_ratio = count(non_null_factor) / total_stocks`
- [ ] 修正 ValidationConfig 阈值
  - 对齐设计默认值：icir_pass=0.20（非 1.00），ic_warn=0.00（非 0.01）
  - 补齐缺失参数：min_sample_count, positive_ic_ratio_pass/warn, coverage_pass/warn
  - 补齐 6 个 WFA 窗口参数
  - 删除设计中不存在的参数：rank_ic_pass/warn, sharpe_pass/warn 等

### 验收标准

1. 15 个因子各自独立验证，输出 mean_ic / mean_rank_ic / icir / decay / positive_ic_ratio / coverage_ratio
2. IC 计算的是"因子 vs 未来收益"（非"IRS vs PAS 相关性"）
3. ICIR = mean/std（非 abs*sqrt(N)）
4. 单元测试：构造已知因子序列 + 已知收益序列 → 验证 IC 值

### 技术要点

- future_returns 需从 raw_daily 读取 T+1 / T+3 / T+5 / T+10 收益率
- 截面对齐：每日 factor 和 return 按 stock_code join，缺失值排除
- IC 使用 scipy.stats.pearsonr / spearmanr 或 pandas corr

---

## CARD-R4.2: Validation Regime + WFA + Gate

**工作量**：2.5 天
**优先级**：P0（Regime 反转 + WFA 缺失）
**前置依赖**：CARD-R4.1
**SOS 映射**：GAP-04, GAP-05, GAP-06

### 交付物

- [ ] 修正 Regime 分类逻辑 (GAP-04)
  - `hot_or_volatile`: temperature >= 70 **OR** volatility >= 0.035
  - `neutral`: 40 <= temp < 70 **AND** 0.020 <= vol < 0.035
  - `cold_or_quiet`: temperature < 40 **OR** volatility < 0.020
  - 删除当前 hot_stable / cold_or_volatile 反转逻辑
- [ ] 修正 Regime 阈值调整策略 (GAP-05)
  - `hot_or_volatile`：放宽 ic_warn/coverage_warn，**提高** icir_pass
  - `cold_or_quiet`：**提高** positive_ic_ratio_pass 与 coverage_pass
  - 删除当前"热→全面收紧，冷→全面放宽"的反向策略
- [ ] 实现真实双窗口 WFA (GAP-06)
  - long_cycle：train=252d, validation=63d, test=63d
  - short_cycle：train=126d, validation=42d, test=42d
  - 用真实 signals + prices 做 OOS 回测
  - 比较 candidate vs baseline：oos_return, max_drawdown, sharpe, turnover, impact_cost_bps, tradability_pass_ratio
  - 投票规则：两组均 PASS→PASS, 一 PASS 一 WARN→WARN, 任一 FAIL→FAIL
  - 候选约束：非负、归一、max≤0.60
- [ ] Gate 4 维判定
  - IC ≥ ic_pass → PASS; ≥ ic_warn → WARN; else → FAIL
  - ICIR ≥ icir_pass → PASS; ≥ icir_warn → WARN; else → FAIL
  - positive_ic_ratio ≥ pass → PASS; ≥ warn → WARN; else → FAIL
  - coverage_ratio ≥ pass → PASS; ≥ warn → WARN; else → FAIL
  - 综合：全 PASS→PASS, 有 WARN→WARN, 有 FAIL→FAIL
- [ ] 修正 GateDecision 风控语义 (GAP-11)
  - 核心数据缺失 → `failure_class=data_failure`, `position_cap_ratio=0.00`（硬阻断）
  - 删除当前 factor_failure + 0.50 的风控漏洞

### 验收标准

1. temperature=80, volatility=0.04 → regime=hot_or_volatile（非 hot_stable）
2. hot_or_volatile regime → icir_pass 提高（非全面收紧）
3. WFA 使用真实 OOS 回测结果（非启发式公式）
4. 核心数据缺失 → position_cap_ratio=0.00（完全阻断）

### 技术要点

- WFA OOS 回测可复用 R5 的 BacktestEngine（简化版：仅跑信号→收益，不需要完整撮合）
- 如果 R5 未完成，WFA 先用简化版（逐日截面收益计算），R5 完成后替换
- 投票逻辑：long_vote + short_vote 分别判定，再合并

---

## CARD-R4.3: Validation OOP + 表结构对齐

**工作量**：1.5 天
**优先级**：P1（架构 + 数据契约）
**前置依赖**：CARD-R4.1, CARD-R4.2
**SOS 映射**：GAP-07, GAP-08, GAP-09, GAP-10, GAP-12, GAP-13, GAP-14

### 交付物

- [ ] 创建 OOP 层
  - `src/algorithms/validation/service.py` — ValidationService
  - `src/algorithms/validation/engine.py` — FactorValidator + WeightValidator + ValidationGate
  - `src/algorithms/validation/models.py` — FactorReport, WeightReport, GateDecision, RunManifest, WeightPlan
  - `src/algorithms/validation/repository.py` — ValidationRepository
- [ ] Factor Report 表结构对齐 (GAP-07)
  - 补齐：factor_source, window_id, start_date, end_date, positive_ic_ratio, decay_1d/3d/10d, coverage_ratio, reason
  - 命名对齐：sample_size→sample_count, ic→mean_ic, rank_ic→mean_rank_ic, gate→decision
- [ ] Weight Report 表结构对齐 (GAP-08)
  - 补齐：window_id, long_vote, short_vote, w_mss/w_irs/w_pas, cost_sensitivity, impact_cost_bps, vs_baseline, reason
  - 命名对齐：plan_id→candidate_id, expected_return→oos_return, gate→decision
- [ ] RunManifest 重建 (GAP-09)
  - 对齐设计字段：run_type, command, test_command, artifact_dir, started_at, finished_at, status, failed_reason
- [ ] WeightPlan 桥接表对齐 (GAP-10)
  - 补齐 source_candidate_id
- [ ] Baseline 权重修正 (GAP-14)
  - `[1/3, 1/3, 1/3]`（非 0.34/0.33/0.33）

### 验收标准

1. 所有表结构与设计 DDL 一致
2. ValidationService 可被 Integration 调用
3. `mypy src/algorithms/validation/` 通过

---

## CARD-R4.4: Integration P0 算法修正（7 项）

**工作量**：2 天
**优先级**：P0（核心评分错误）
**SOS 映射**：INT-P0-1~P0-7

### 交付物

- [ ] P0-1：strength_factor 应用
  - consistency=divergent → `final_score *= 0.8`
  - consistency=partial → `final_score *= 0.9`
  - 位置：`pipeline.py:944-945`
- [ ] P0-2：IRS 方向映射来源修正
  - 从 `rotation_status`（IN/OUT/HOLD）映射方向
  - 删除从 `recommendation` 映射的逻辑
  - 更新 SQL 查询读取 rotation_status
  - 位置：`pipeline.py:878`, `_direction_from_recommendation():239-245`
- [ ] P0-3：仓位计算三类调整因子
  - mss_factor = `1 - |temperature-50|/100`（连续函数）
  - irs_factor: 超配×1.2, 标配×1.0, 减配×0.7, 回避×0.3
  - pas_factor: S×1.2, A×1.0, B×0.7, C/D×0.3
  - `position = base × mss_factor × irs_factor × pas_factor × cap`
  - 位置：`pipeline.py:948-954`
- [ ] P0-4：单股仓位上限（per-grade cap）
  - S 级 max 10%, A 级 max 8%, B 级 max 5%, C/D 级 max 3%
- [ ] P0-5：neutrality 加权聚合
  - `neutrality = max(w_mss×mss_neutrality, w_irs×irs_neutrality, w_pas×pas_neutrality)`
  - 更新 SQL 读取 IRS/PAS 的 neutrality 字段
  - 位置：`pipeline.py:957`
- [ ] P0-6：IRS 行业分协同调整
  - 超配 → PAS 评分 ×1.05
  - 回避 → PAS 评分 ×0.85（已有，确认位置正确）
- [ ] P0-7：complementary 模式评分来源修正
  - `final_score = td_result.final_score`（TD 做风控框架）
  - BU 仅影响选股排序，不加权到 final_score
  - 位置：`pipeline.py:937-942`

### 验收标准

1. divergent + td=72 → final_score=57.6（非 72）
2. rotation_status=IN + recommendation=HOLD → 方向=涨(+1)（非中性）
3. C 级股 + 回避行业 → position ×0.3×0.3=×0.09
4. complementary 模式：td=50(HOLD) + bu=85 → final_score=50（非 71）

---

## CARD-R4.5: Integration 模式语义 + 筛选排序

**工作量**：1 天
**优先级**：P1-P2
**前置依赖**：CARD-R4.4
**SOS 映射**：INT-P1-1~P1-3, INT-P2-1~P2-5

### 交付物

- [ ] P1-1：dual_verify consensus_factor
  - 弱共识 → final_score ×0.9
  - 矛盾 → final_score ×0.7 + HOLD 上限
  - 双中性 → HOLD 上限
- [ ] P1-2：dual_verify position_size
  - `min(td_result.position_size, bu_result.position_size)`（非 cycle_cap）
- [ ] P2-1：推荐列表 final_score≥55 门槛
  - 在 `_apply_recommendation_limits()` 添加 `final_score >= 55` 筛选
- [ ] P2-2：排序规则对齐
  - 第 1 维 final_score 降序 → 第 2 维 opportunity_score → 第 3 维 allocation_advice
- [ ] P2-4：IRS cold_start/stale 回退
  - cold_start/stale 时强制使用 BASELINE_WEIGHTS
- [ ] P2-5：Gate fallback 修正
  - gate_status 缺失 → 回退为 **WARN**（非 PASS）+ baseline 权重

### 验收标准

1. dual_verify 弱共识时 final_score 缩减 10%
2. 推荐列表不含 final_score < 55 的标的
3. gate_status 缺失 → WARN 级别（非 PASS）

---

## CARD-R4.6: Integration OOP + 数据模型

**工作量**：1 天
**优先级**：P1（架构）+ P3（模型）
**前置依赖**：CARD-R4.4
**SOS 映射**：INT-P3-1~P3-4

### 交付物

- [ ] 目录迁移：`src/integration/` → `src/algorithms/integration/`
- [ ] 创建 OOP 层
  - `src/algorithms/integration/service.py` — IntegrationService
  - `src/algorithms/integration/engine.py` — 评分计算逻辑
  - `src/algorithms/integration/models.py` — IntegratedRecommendation, RegimeParameters 等
  - `src/algorithms/integration/repository.py` — IntegrationRepository
- [ ] 输出表字段对齐 (P3-1)
  - 补齐：position_cap_ratio, tradability_pass_ratio, impact_cost_bps, stock_name
  - 保留合理扩展字段并反向更新设计文档
- [ ] 输入字段读取补齐 (P3-2)
  - MSS 补读：position_advice, neutrality
  - IRS 补读：rotation_status, sample_days, neutrality（删除 recommendation）
  - PAS 补读：stock_name, industry_code, entry/stop/target, neutrality
- [ ] RegimeParameters 实现 (P3-3)
  - 创建 `RegimeParameters` dataclass
  - 实现 risk_on/neutral/risk_off 三档 profile 动态切换
- [ ] 更新信息流文档 (P3-4)
  - 删除虚构的 OOP 组件依赖图
  - 更新为实际 Pipeline → Service 架构

### 验收标准

1. `src/integration/` 不再存在（已迁移）
2. IntegrationService 可被 Backtest/Trading/GUI 导入
3. RegimeParameters 三档 profile 根据 MSS 温度动态切换

---

## CARD-R4.7: 端到端信号链测试

**工作量**：1 天
**优先级**：P0（全链路验证）
**前置依赖**：CARD-R4.1~R4.6

### 交付物

- [ ] 端到端信号链测试
  - Data(R1) → MSS(R2) → IRS(R3) → PAS(R3) → Validation(R4) → Integration(R4)
  - 检查 `integrated_recommendation` 表 28 字段完整性
  - 检查 final_score 分布合理（均值 ≈ 50-60，有区分度）
  - 检查 recommendation 分布（不全是 BUY 或全是 HOLD）
  - 检查 position_size > 0 的标的数量合理
- [ ] 契约测试
  - `tests/contracts/test_validation.py`：检查 validation_gate_decision 12 字段
  - `tests/contracts/test_integration.py`：检查 integrated_recommendation 28 字段
- [ ] strength_factor 验证
  - 构造 divergent 场景 → 验证 final_score 被缩减
  - 构造 aligned 场景 → 验证 final_score 不变
- [ ] 模式验证
  - dual_verify 矛盾场景 → 验证 HOLD 上限
  - complementary 场景 → 验证 TD 主导评分
- [ ] 验证报告
  - 输出：`artifacts/r4-validation-report.md`
  - 覆盖 Gate 判定 + 模式语义 + 评分分布 + 字段完整性

### 验收标准

1. 全链路无异常运行
2. 28 字段全部非空
3. strength_factor 和模式语义与设计一致
4. Gate FAIL 时 position_cap_ratio=0.00

---

## R4 阶段验收总览

完成以上 7 张卡后，需满足：

1. **Validation 重写**：15 因子真实验证 + 真实 WFA + 4 维 Gate
2. **Regime 修正**：分类逻辑与阈值调整策略与设计一致
3. **Integration P0 清零**：7 项算法错误全部修复
4. **模式语义**：dual_verify / complementary 行为与设计一致
5. **OOP 架构**：ValidationService + IntegrationService 可用
6. **风控完整**：数据缺失→硬阻断，Gate FAIL→仅跳过当日
7. **全链路可信**：Data → MSS/IRS/PAS → Validation → Integration 输出正确

**下一步**：进入 R5 Backtest 重建（19 项偏差，Qlib 主线引擎）。
