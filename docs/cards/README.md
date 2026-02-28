# 执行卡索引

本目录包含 R0-R9 十个阶段的细粒度执行卡，每张卡 1-3 天工作量。

## 已生成卡片

- [x] **R0-foundation-cards.md** — 工程基座（5 张卡，3-4 天）
- [x] **R1-data-layer-cards.md** — 数据层重建（6 张卡，5-7 天）
- [x] **R2-mss-cards.md** — MSS 重建（4 张卡，4-5 天）
- [x] **R3-irs-pas-cards.md** — IRS + PAS 重建（8 张卡，12-15 天）
- [x] **R4-validation-integration-cards.md** — Validation + Integration 重建（7 张卡，10-12 天）
- [x] **R5-backtest-cards.md** — Backtest 重建（9 张卡，12-14 天）
- [x] **R6-trading-cards.md** — Trading 重建（5 张卡，7-8 天）
- [x] **R7-analysis-cards.md** — Analysis 重建（5 张卡，6-8 天）
- [x] **R8-gui-cards.md** — GUI 重建（6 张卡，8-10 天）
- [x] **R9-enhancements-cards.md** — 增强包 + 稳定化（6 张卡，7-10 天）

## 卡片结构说明

每张卡包含：
1. **工作量估算**：天数
2. **优先级**：P0/P1/P2/P3
3. **前置依赖**：需先完成的卡号
4. **SOS 映射**：对应 docs/sos/ 中的具体问题
5. **交付物清单**：checkbox 格式
6. **验收标准**：明确的成功标准
7. **技术要点**：实现提示

## 使用方式

1. 按卡号顺序执行（如 CARD-R0.1 → CARD-R0.2 → ...）
2. 完成一张卡后勾选所有 checkbox
3. 满足验收标准后进入下一张
4. 每个阶段完成后提交 PR（branch: `rebuild/r{N}-{module}`）

## 快速导航

| 阶段 | 卡数 | 工期 | 核心产出 | 文件 |
|------|------|------|----------|------|
| R0 | 5 | 3-4天 | 骨架+共享层 | R0-foundation-cards.md |
| R1 | 6 | 5-7天 | L1/L2数据可信 | R1-data-layer-cards.md |
| R2 | 4 | 4-5天 | MSS温度可信 | R2-mss-cards.md |
| R3 | 8 | 12-15天 | IRS/PAS评分可信 | R3-irs-pas-cards.md |
| R4 | 7 | 10-12天 | Gate+信号可信 | R4-validation-integration-cards.md |
| R5 | 9 | 12-14天 | 回测可信(Qlib) | R5-backtest-cards.md |
| R6 | 5 | 7-8天 | 纸上交易 | R6-trading-cards.md |
| R7 | 5 | 6-8天 | 绩效非零+日报 | R7-analysis-cards.md |
| R8 | 6 | 8-10天 | GUI完整 | R8-gui-cards.md |
| R9 | 6 | 7-10天 | 全链路闭环 | R9-enhancements-cards.md |

**总计**：61 张卡，75-93 工作日。
