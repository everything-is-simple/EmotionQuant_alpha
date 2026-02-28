# Integration（三系统集成推荐）— SOS 审计总览

**范围**: `src/integration/pipeline.py` vs `docs/design/core-algorithms/integration/` 四份设计文档
**总差异**: 19 项（P0×7 / P1×3 / P2×5 / P3×4）

---

## 核心矛盾

Integration 接收 MSS/IRS/PAS 三系统输出产出 final_score 和推荐信号。7 项 P0 意味着核心算法公式有多处实质性偏差：

1. **strength_factor 未应用**：方向分歧(divergent)时 final_score 应削弱 20%，代码完全未执行
2. **IRS 方向来源错误**：设计从 rotation_status 映射，代码从 recommendation 映射
3. **仓位计算缺失三类调整因子**：MSS连续温度因子/IRS配置因子/PAS等级因子全部缺失
4. **单股仓位上限(per-grade cap)未实现**
5. **neutrality 未加权聚合**：设计要求三系统 neutrality 加权取最大，代码仅从 MSS 取
6. **IRS 行业分协同调整缺失**：设计要求根据 allocation_advice 调整 PAS 评分
7. **complementary 模式评分逻辑错误**：设计用 TD 评分，代码用 TD*0.4+BU*0.6

## 已确认一致的部分

- ✅ BASELINE_WEIGHTS = 1/3 × 3，MAX_MODULE_WEIGHT = 0.60
- ✅ 推荐等级映射阈值（75/70/50/30）与 STRONG_BUY 周期条件
- ✅ Gate=FAIL → 阻断集成
- ✅ 每日最多20只、每行业最多5只硬约束
- ✅ 方向判定公式 avg > 0.3 → bullish, < -0.3 → bearish

## 文件索引

- [01-gap-inventory.md](01-gap-inventory.md) — 19 项差异逐项清单
- [02-risk-assessment.md](02-risk-assessment.md) — 风险评估
- [03-remediation-plan.md](03-remediation-plan.md) — 修复方案
