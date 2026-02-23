# Plan A 路线修订（Reborn 增强版）

**创建时间**: 2026-02-23  
**更新时间**: 2026-02-23  
**目标**: 不推倒现有 Plan A，在原路线内恢复“真螺旋闭环”  
**状态**: Active（执行合同）

---

## 1. 修订原则（吸收危机报告 + Plan B）

本修订直接吸收 `.reports/crisis-diagnosis-20260223.md` 与 `Governance/SpiralRoadmap/planB/` 的方法，但不切换主线。

1. 不再用“任务完成”代替“闭环完成”。
2. 每个螺旋必须端到端：`本地数据 -> 算法集成 -> 回测 -> 归因 -> 可见成果`。
3. 每个螺旋都必须回答三句话：
   - 这圈做成了什么？
   - 效果如何？
   - 下一圈凭什么能进？
4. 继续复用现有 S0-S7 执行卡，不做重构式推翻。
5. 上位 SoT 仍是 `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`。

---

## 2. Plan A 三大螺旋（Reborn 口径）

### 螺旋 1：Canary 闭环（2-3 个月）

- 对应圈位：`S0a -> S0b -> S0c -> S1a -> S1b -> S2a -> S2b -> S2c -> S3(min) -> S3b(min)`
- 主目标：先证明“情绪主线策略可运行、可回测、可解释”。
- 入口硬条件：
  - 本地 DuckDB 可读写，`Config.from_env()` 注入有效。
  - 交易日历可用，A 股规则字段可追溯。
- 圈内必须交付：
  - canary 数据落地（建议先 `2022-01-01` 到 `2024-12-31`）。
  - MSS/IRS/PAS/Validation/Integration 主链可运行。
  - 简单回测（本地引擎）可复现。
  - 最小归因（`signal/execution/cost` 三分解）可导出。
- 出口硬门禁（全部满足才可进入螺旋 2）：
  - `data_coverage >= 99%`（目标窗口内）。
  - `eq run` 与 `eq backtest` 在同一窗口可重复运行。
  - 至少 1 份 canary 收益曲线 + 1 份归因报告。
  - `Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md` 完成一轮更新。

### 螺旋 2：Full 闭环（3-4 个月）

- 对应圈位：`S3a -> S3ar -> S3 -> S4 -> S3b -> S3c -> S3d -> S3e -> S4b`
- 主目标：在 16 年历史数据上完成完整算法验证与归因闭环。
- 入口硬条件：
  - 螺旋 1 门禁全部通过。
  - `validation_weight_plan` 桥接链路稳定可审计。
- 圈内必须交付：
  - 16 年历史数据落地（目标：`2008-01-01` 至 `2024-12-31`）。
  - 多窗口完整回测（至少 1y/3y/5y + 典型牛熊段）。
  - A/B/C 对照 + 实盘-回测偏差归因完整化。
  - SW31 全行业语义校准、MSS adaptive、Validation 生产校准闭环。
- 出口硬门禁（全部满足才可进入螺旋 3）：
  - 全市场历史数据落库完成并通过质量检查。
  - 回测报告覆盖多窗口且可复现。
  - 归因报告可回答“收益主要来自哪里”。
  - 极端防御参数来源可追溯到 `S3b + S3e` 联合证据。

### 螺旋 3：Production 闭环（2-3 个月）

- 对应圈位：`S5 -> S6 -> S7a`（必要时 `S5r/S6r/S7ar`）
- 主目标：把可验证策略升级为可运行系统（纸上交易/运营口径）。
- 入口硬条件：
  - 螺旋 2 门禁全部通过。
  - 关键风险项无 P0 未闭环阻断。
- 圈内必须交付：
  - GUI/日报消费 L3 真实产物，不允许手工覆盖。
  - 全链路重跑一致性报告。
  - 自动调度、运行历史、失败重试可审计。
- 出口硬门禁：
  - 7x24 运维口径可监控。
  - 关键流程可回放、可追责、可恢复。
  - 生产就绪评估报告明确 `GO/NO_GO`。

---

## 3. Plan A P0 增强（立即执行，不破坏主线）

### P0-1 本地数据止血

```bash
eq fetch-batch --start 20220101 --end 20241231 --batch-size 365 --workers 3
eq fetch-retry
eq data-quality-check --comprehensive
```

目标：先让 canary-3y 数据可用，再持续扩窗至 16 年。

### P0-2 端到端可运行证据

```bash
eq run --date 20241220 --full-pipeline --validate-each-step
eq backtest --start 20240101 --end 20241220 --engine local
eq analysis --start 20240101 --end 20241220 --ab-benchmark
```

目标：至少产出一组“数据->算法->回测->归因”完整证据包。

### P0-3 成果可见化

每圈必须同步业务看板：`Governance/SpiralRoadmap/planA/PLANA-BUSINESS-SCOREBOARD.md`

最低字段：

- 数据覆盖率、缺失率、最近交易日一致性
- 回测窗口、收益/回撤/夏普
- 归因结论（signal/execution/cost）
- 当前 `GO/NO_GO`

---

## 4. 禁止事项（防“做完但没做成”）

以下任一出现，禁止标记“螺旋完成”：

1. 未落库本地数据，只跑模拟或临时数据。
2. 只有单元测试通过，没有可复现回测产物。
3. 有回测结果但无归因结论。
4. 有技术报告但无法回答“本圈业务价值是什么”。
5. `--contracts --governance` 未通过仍推进下一圈。

---

## 5. 与 Plan B 的关系

1. Plan A 仍是执行主线；Plan B 是方法来源与备选。
2. 本次修订已把 Plan B 的三螺旋思想吸收进 Plan A。
3. 若螺旋 1 连续两个评审周期无法通过出口门禁，再触发是否切换 Plan B 的治理评审。

---

## 6. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v2.0 | 2026-02-23 | 重写为 Reborn 增强版：三大螺旋闭环、P0 止血动作、成果可见看板与禁止事项落地 |
| v1.0 | 2026-02-23 | 初版增强建议 |
