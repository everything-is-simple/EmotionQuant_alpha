# Reborn 第二螺旋：Full 闭环（Plan B）

**螺旋编号**: Reborn-Spiral-2  
**更新时间**: 2026-02-24  
**周期**: 3-4个月  
**定位**: 全历史数据与完整校准闭环，不允许“局部通过即宣告完成”

---

## 1. 螺旋目标

1. 在全市场与16年历史窗口验证策略稳健性。
2. 完成从归因到校准到极端防御的完整证据链。
3. 产出可审计 `GO/NO_GO`，作为进入生产螺旋的唯一依据。

---

## 2. 设计文档绑定（必须对应）

| 设计域 | 文档目录 | 螺旋2要求 |
|---|---|---|
| Data | `docs/design/core-infrastructure/data-layer/` | 2008-2024 落库 + 质量报告 |
| Backtest | `docs/design/core-infrastructure/backtest/` | 多窗口回测 + 主线引擎口径一致 |
| Trading | `docs/design/core-infrastructure/trading/` | 纸上交易记录可复盘 |
| Analysis | `docs/design/core-infrastructure/analysis/` | A/B/C + 偏差归因完整 |
| IRS | `docs/design/core-algorithms/irs/` | S3c SW31 语义校准 |
| MSS | `docs/design/core-algorithms/mss/` | S3d adaptive + probe 收益校准 |
| Validation | `docs/design/core-algorithms/validation/` | S3e 生产校准 + 双窗口WFA |
| Integration | `docs/design/core-algorithms/integration/` | 产物消费链持续有效 |

---

## 3. 范围与圈位映射

- 圈位范围：`S3a -> S3ar -> S3 -> S4 -> S3b -> S3c -> S3d -> S3e -> S4b`
- 窗口范围：`2008-01-01 ~ 2024-12-31`

---

## 4. 关键闭环

### 4.1 数据闭环（S3a/S3ar）

- 16年数据落库
- 采集稳定性可审计（重试、限流、锁恢复）

### 4.2 回测与归因闭环（S3/S4/S3b）

- 多窗口回测可复现
- A/B/C 对照齐备
- `signal/execution/cost` 偏差分解齐备

### 4.3 校准与防御闭环（S3c/S3d/S3e/S4b）

- S3c 行业语义校准
- S3d MSS adaptive 校准
- S3e Validation 生产校准
- S4b 极端防御参数追溯

---

## 5. S3c/S3d/S3e 双档量化门禁

| 圈位 | MVP（最小可用） | FULL（完整生产口径） |
|---|---|---|
| S3c | 31行业覆盖齐全，允许可解释 WARN | 近3窗口稳定覆盖，告警闭环 |
| S3d | 自适应阈值可运行，样本不足可回退固定阈值 | 关键窗口无负spread，probe可复跑 |
| S3e | 双窗口WFA可运行，`final_gate` 不得 FAIL | `factor_gate_raw` 不得 FAIL，OOS指标达标 |

补充规则：

1. 准备可并行，收口宣告必须串行 `S3c -> S3d -> S3e`。
2. 未达到 `MVP`：不得进入 S4b。
3. 未达到 `FULL`：不得宣称螺旋2生产就绪。

---

## 6. 螺旋2门禁

### 6.1 入口门禁

- 螺旋1 `GO`
- `validation_weight_plan` 桥接链稳定

### 6.2 出口门禁

- [ ] 16年数据落库完成并通过质量检查
- [ ] 多窗口回测与A/B/C对照齐备
- [ ] 完整归因可回答收益来源
- [ ] S3c/S3d/S3e 的 MVP/FULL 均通过
- [ ] S4b 参数可追溯到 S3b + S3e
- [ ] `PLAN-B-READINESS-SCOREBOARD.md` 更新并给 `GO/NO_GO`

---

## 7. 失败处理

1. 任一出口项未通过：`NO_GO`。
2. `NO_GO` 时只允许在螺旋2范围修复，不得推进螺旋3。
3. 若校准链连续卡住，允许回到对应圈位重验，不得跳圈宣告完成。

---

## 8. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v2.2 | 2026-02-24 | 重写为设计绑定执行合同，保留同精度门禁并强化闭环证据链 |
| v2.1 | 2026-02-23 | 新增双档量化门禁 |
