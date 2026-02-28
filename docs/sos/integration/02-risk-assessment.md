# Integration — 风险评估

---

## 总体风险等级：高

Integration 是 MSS/IRS/PAS 三系统的汇合点，其错误直接体现在最终推荐信号中。但 Integration 本身的算法框架大体正确（权重基线、等级映射、方向判定等已一致），问题集中在精细化调整机制的缺失。

---

## 关键风险判断

### 仓位风控失效（INT-P0-3 + P0-4，极高风险）

三类调整因子全部缺失意味着：C 级股在回避行业中获得的仓位与 S 级股在超配行业中完全相同。设计中 ×0.09 的极端压缩 vs 代码中 ×1.0 无缩减——这是风控层面的根本性失效。

### strength_factor 缺失（INT-P0-1，高风险）

方向分歧时不削弱评分，可能产出矛盾信号下的错误买入建议。divergent 场景下设计会从 BUY 降为 HOLD，代码不会。

### IRS 方向来源（INT-P0-2，中高风险）

rotation_status(IN/OUT) 和 recommendation(BUY/HOLD) 是两个不同维度。IN+HOLD（轮入中但当前推荐持有）是正常状态，代码误判为中性会影响一致性检查和 strength_factor。

### complementary 模式（INT-P0-7 + P1-3，中风险）

BU 权重 60% 倒挂违背"TD 做风控框架"的设计初衷。但 complementary 模式在实际使用中不是默认模式（默认 top_down），影响范围受限。

### P2/P3 项（低-中风险）

- 推荐列表缺 55 分门槛和排序差异影响展示质量
- 权重回退缺失在 IRS 数据异常时放大风险
- Regime 参数系统影响极端市场下的表现

---

## 风险优先级排序

1. **INT-P0-3 + P0-4** — 仓位风控（最紧急：无调整因子 + 无 per-grade cap）
2. **INT-P0-1** — strength_factor 应用
3. **INT-P0-2** — IRS 方向来源修正
4. **INT-P0-5 + P0-6** — neutrality 聚合 + IRS 协同调整
5. **INT-P0-7 + P1-1~P1-3** — 模式语义修正
6. **INT-P2-4** — 权重回退
7. **其余 P2/P3** — 筛选排序、字段对齐、Regime 参数
