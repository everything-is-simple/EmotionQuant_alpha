# 路线图与核心设计覆盖分析（实现深度版）

**状态**: Active  
**更新时间**: 2026-02-20  
**文档角色**: 路线图完整性审计报告（覆盖率 + 实现深度双口径）

---

## 0. 分析目标

本报告不再只回答“路线是否覆盖了设计目录”，而是同时回答两件事：

1. 路线是否有对应圈位（Coverage）
2. 对应圈位是否已在代码层实现到设计口径（Implementation Depth）

覆盖对象：

- 核心算法：`docs/design/core-algorithms/`
- 核心基础设施：`docs/design/core-infrastructure/`
- 外挂增强：`docs/design/enhancements/`

---

## 1. 总结结论（先给结论）

1. **目录覆盖率仍为 100%**：S0-S7a 路线对设计模块与 ENH 项均有落位。
2. **实现深度不是 100%**：存在“最小闭环已完成，但核心设计完整实现未完成”的缺口。
3. 缺口集中在阶段B，已在主控路线新增 `S3c/S3d/S3e` 三个专项圈进行闭环：
   - `S3c`：行业语义校准（SW31 映射）
   - `S3d`：MSS 自适应校准（adaptive + 真实收益 probe）
   - `S3e`：Validation 生产校准（future_returns + 双窗口 WFA）
4. 只有 `S3c + S3d + S3e + S4b` 全部收口后，才能声明“核心设计 full 实现完成”。

---

## 2. 已完成能力（保持不回退）

以下能力按“最小闭环”已成立并有代码/测试证据：

- S1a/S1b：MSS 打分与消费链闭环
- S2a/S2b/S2c：IRS/PAS/Validation/Integration 最小闭环与桥接门禁闭环
- S3a/S3ar：采集增强与稳定性修复闭环
- S3/S4：回测与纸上交易主链已可运行并具备收口证据

说明：上述结论仅表示“可运行、可测试、可追溯”成立，不自动推导为“设计细项全部完成”。

---

## 3. 设计缺口矩阵（核心）

| 缺口ID | 设计要求（SoT） | 当前实现现状 | 影响 | 路线处置圈 |
|---|---|---|---|---|
| GAP-ALGO-01 | `industry_snapshot` 应按 SW31 聚合，IRS 需 31 行业全覆盖映射 | `src/data/l2_pipeline.py` 当前输出 `industry_code=ALL` 单条聚合；IRS 实际输入粒度不足 | 行业轮动解释力与配置建议完整性不足 | S3c |
| GAP-ALGO-02 | MSS 周期阈值默认 `adaptive`（T30/T45/T60/T75），趋势判定 `EMA+slope+trend_band` | `src/algorithms/mss/engine.py` 仍使用固定阈值 `30/45/60/75` 与三点单调趋势 | 极端行情下周期判定稳健性不足 | S3d |
| GAP-ALGO-03 | MSS probe 应基于真实收益序列验证，不得用代理替代 | `src/algorithms/mss/probe.py` 当前用 `mss_temperature` 前后差构造 `forward_5d` 代理 | `top_bottom_spread_5d` 可交易解释力不足 | S3d |
| GAP-ALGO-04 | Validation 因子验证需 `factor_series × future_returns` 对齐；权重验证需双窗口 WFA + OOS/成本/可成交性指标 | `src/algorithms/validation/pipeline.py` 仍以当日启发式与代理指标为主，未完成生产口径对齐 | 回测-实盘解释一致性不足，权重替换稳健性不足 | S3e |
| GAP-INFRA-01 | A股细撮合规则需覆盖连续跌停/流动性枯竭等极端场景参数化 | S4 基础链路已完成，细粒度压力参数仍待专项校准 | 极端市况回撤控制存在偏差风险 | S4b |

关联债务条目：

- `TD-S0-006`（SW31 映射）
- `TD-S1-007`（MSS adaptive）
- `TD-S1-008`（probe 真实收益口径）
- `TD-S0-002`（Validation 生产级统计校准）
- `TD-S0-004`（极端撮合细则）

---

## 4. 路线修订结果（阶段B）

阶段B由原 `S3b -> S4b` 修订为：

```text
S3b -> S3c -> S3d -> S3e -> S4b
```

新增圈位职责：

1. `S3c`（行业语义校准）
   - 收口目标：SW31 行业映射 + IRS 31 行业覆盖门禁
2. `S3d`（MSS 自适应校准）
   - 收口目标：adaptive 阈值 + 趋势抗抖 + probe 真实收益
3. `S3e`（Validation 生产校准）
   - 收口目标：future_returns 对齐 + 双窗口 WFA + OOS 成本与可成交性指标

---

## 5. 判定规则更新

原判定（已废弃）：

- “路线覆盖 100% => 当前无覆盖性缺口”

新判定（现行）：

1. 目录覆盖 100% 仅表示“路线有落位”。
2. 只有当缺口矩阵中的 `GAP-*` 被对应圈位收口，并通过 `run/test/artifact/review/sync` 五件套验证后，才可判定“实现深度完成”。
3. 对核心算法（MSS/IRS/PAS/Validation/Integration），`S2c` 表示“最小语义闭环”；`S3c/S3d/S3e` 完成后才可声明“full 实现完成”。

---

## 6. 变更记录

| 版本 | 日期 | 变更说明 |
|---|---|---|
| v1.2 | 2026-02-20 | 将报告从“纯覆盖率口径”升级为“覆盖率 + 实现深度”双口径；新增缺口矩阵与 `S3c/S3d/S3e` 修订结论，撤销“当前无覆盖性缺口”结论 |
| v1.1 | 2026-02-17 | 去重重复章节；修正 ENH-05 落位为 S0c；统一阶段覆盖矩阵口径 |
| v1.0 | 2026-02-17 | 首版：路线图与核心设计覆盖分析（100%） |

