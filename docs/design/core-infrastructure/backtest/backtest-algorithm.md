# Backtest 回测算法设计

**版本**: v3.5.1（重构版）
**最后更新**: 2026-02-14
**状态**: 设计完成（闭环落地口径补齐；代码待实现）；与 MSS/IRS/PAS/Integration + Data Layer 对齐

---

## 1. 设计概述

### 1.0 实现状态（仓库现状）

- `src/backtest/` 当前仅有 `__init__.py` 占位；回测引擎与接口尚未落地。
- 本文档为设计口径；实现阶段需以此为准并同步更新记录。

### 1.1 核心定位

Backtest Layer 是 EmotionQuant 系统的策略验证层，核心职责：

1. **策略验证**：基于 L3 输出信号回放策略表现（不重算 MSS/IRS/PAS 因子）
2. **交易规则复刻**：A 股 T+1、涨跌停、100 股整手、费用模型
3. **模式回测**：Top-Down（传统默认）与 Bottom-Up（实验）对照验证
4. **绩效评估**：收益、回撤、风险调整收益与交易统计

### 1.2 关键原则（铁律对齐）

- **本地数据优先**：仅读取本地落库数据（L1/L3），不直连远端
- **单指标不得独立决策**：回测只消费上游信号与原始 OHLCV，不允许由单一技术指标直接触发交易
- **无未来函数**：严格按交易日顺序推进，禁止未来数据泄露
- **A 股专属**：严格执行 T+1、涨跌停、整手交易与费用规则
- **信号-执行日拆分**：信号在 `signal_date`（收盘后）生成，订单在下一交易日 `execute_date` 开盘执行

### 1.3 回测引擎选型

- **Qlib 主选（研究平台）**：用于研究回测、因子实验与实验管理。
- **向量化基线（执行口径）**：用于快速迭代与 A 股规则一致性回放。
- **backtrader 兼容适配**：保留兼容能力，不作为主选引擎。

### 1.4 CP-06 最小可运行闭环（P0）

```text
目标：先跑通 local_vectorized + top_down 单一主路径，再扩展其它模式/引擎。

最小命令（示意）：
python -m src.backtest.runner ^
  --engine local_vectorized ^
  --mode top_down ^
  --start 20250101 --end 20250228 ^
  --config-name cp06_smoke

最小验收：
1) 成功落库 backtest_results/backtest_trade_records
2) 输出 signal_date / execute_date 分离审计字段
3) 通过 Gate=FAIL / T+1 / 涨跌停 / RR<1 四组回放
```

---

## 2. 模式定义（传统 vs 实验）

| 模式 | 信号来源 | 状态 | 说明 |
|------|----------|------|------|
| **top_down** | integrated_recommendation（integration_mode=top_down） | 默认 | 传统主流程，风控优先 |
| **bottom_up** | integrated_recommendation（integration_mode=bottom_up） | 实验 | 结构性行情验证（不得突破 TD 上限） |
| **dual_verify** | TD/BU 双验证 | 可选 | 需回测验证后开启 |
| **complementary** | TD控仓 + BU选股 | 可选 | 需回测验证后开启 |

> **注意**：回测层不重算 MSS/IRS/PAS，只消费 Integration 输出的 `final_score / recommendation / position_size`。
> **三算法使用**：Top-Down 为传统流程（MSS→IRS→PAS）；Bottom-Up 为实验流程（PAS→IRS→MSS），回测层只读取集成结果与 PAS 广度派生，不跨层重算。

---

## 3. 信号生成与策略入口

### 3.0 信号与执行时间轴（避免未来函数）

```
T 日收盘后（signal_date = T）：
  Integration 已落库 integrated_recommendation
  回测信号生成（仅使用 T 日及之前数据）

T+1 交易日开盘（execute_date = T+1）：
  执行订单（集合竞价/开盘价）
```

### 3.1 Top-Down 信号流程（传统默认）

```text
输入：signal_date, integration_mode="top_down"
输出：List[BacktestSignal]

Step 0: 数据就绪检查（本地数据优先）
    gate = get_validation_gate_decision(signal_date)
    if gate.final_gate == "FAIL":
        set_backtest_state("blocked_gate_fail")
        log.warning(f"Gate=FAIL on {signal_date}, skip backtest signal generation")
        return []
    if gate.contract_version != "nc-v1":
        set_backtest_state("blocked_contract_mismatch")
        log.error(f"unsupported contract_version={gate.contract_version}")
        return []

    readiness = check_data_ready(signal_date)
    if not readiness.is_ready:
        set_backtest_state("warn_data_fallback")
        return []  # 缺口必须先落库/补全，不直连远端

Step 1: 读取集成推荐（Top-Down）
    recs = get_integrated_recommendation(
        signal_date,
        integration_mode="top_down",
        top_n=config.top_n
    )

Step 2: 软门控过滤（不做单点硬否决）
    recommendation_rank = {"AVOID": 0, "SELL": 1, "HOLD": 2, "BUY": 3, "STRONG_BUY": 4}
    min_rec_rank = recommendation_rank.get(config.min_recommendation, recommendation_rank["BUY"])

    filtered_recs = []
    for row in recs:
        if row.final_score < config.min_final_score:
            continue
        if recommendation_rank.get(row.recommendation, -1) < min_rec_rank:
            continue
        if row.direction == "neutral":
            continue  # 与 Trading 对齐：neutral 仅观望，不生成订单
        if row.risk_reward_ratio < 1.0:
            continue  # RR<1 信号在执行层软过滤，避免预期收益劣于风险
        filtered_recs.append(row)

Step 3: 构建回测信号（使用集成输出）
    for row in filtered_recs:
        signals.append(BacktestSignal(
            signal_id=f"SIG_{signal_date}_{row.stock_code}",
            signal_date=signal_date,
            stock_code=row.stock_code,
            stock_name=row.stock_name,
            industry_code=row.industry_code,
            entry=row.entry,
            stop=row.stop,
            target=row.target,
            risk_reward_ratio=row.risk_reward_ratio,
            position_size=row.position_size,  # 来自 Integration
            recommendation=row.recommendation,
            final_score=row.final_score,
            integration_mode=integration_mode,
            mss_score=row.mss_score,
            irs_score=row.irs_score,
            pas_score=row.pas_score,
            direction=row.direction,
            neutrality=row.neutrality,
            source="integrated",
            backtest_state="normal"
        ))
```

### 3.2 Bottom-Up 信号流程（实验）

```text
输入：signal_date, integration_mode="bottom_up"
输出：List[BacktestSignal]

Step 0: Validation Gate 检查
    gate = get_validation_gate_decision(signal_date)
    if gate.final_gate == "FAIL":
        set_backtest_state("blocked_gate_fail")
        log.warning(f"Gate=FAIL on {signal_date}, skip bottom_up signal generation")
        return []
    if gate.contract_version != "nc-v1":
        set_backtest_state("blocked_contract_mismatch")
        log.error(f"unsupported contract_version={gate.contract_version}")
        return []

Step 1: 读取集成推荐（Bottom-Up）
    recs = get_integrated_recommendation(
        signal_date,
        integration_mode="bottom_up",
        top_n=config.top_n
    )

Step 2: 结构性活跃度验证（pas_breadth_daily）
    pas_breadth = get_pas_breadth(signal_date)
    if pas_breadth.pas_sa_ratio < config.min_pas_breadth_ratio:
        set_backtest_state("warn_mode_fallback")
        return generate_top_down_signals(signal_date)  # BU 活跃度不足回退 TD

Step 3: 构建回测信号
    recommendation_rank = {"AVOID": 0, "SELL": 1, "HOLD": 2, "BUY": 3, "STRONG_BUY": 4}
    min_rec_rank = recommendation_rank.get(config.min_recommendation, recommendation_rank["BUY"])

    for row in recs:
        if row.final_score < config.min_final_score:
            continue
        if recommendation_rank.get(row.recommendation, -1) < min_rec_rank:
            continue
        if row.direction == "neutral":
            continue
        if row.risk_reward_ratio < 1.0:
            continue
        signals.append(BacktestSignal(..., integration_mode="bottom_up", signal_date=signal_date, backtest_state="normal"))

约束：BU 仓位不得突破同周期 TD 上限（Integration 已完成该约束）
说明：`recession` 周期的 PAS 折扣（×0.8）已在 Integration 协同约束完成，Backtest 仅消费 `final_score` 与执行字段。
```

### 3.3 模式切换策略（P2：配置化 -> 状态驱动）

```python
def resolve_backtest_mode(signal_date: str, config: BacktestConfig) -> str:
    if config.mode_switch_policy == "config_fixed":
        return config.integration_mode

    regime = get_market_regime(signal_date)  # risk_on / neutral / risk_off
    if config.mode_switch_policy == "regime_driven":
        return "bottom_up" if regime == "risk_on" else "top_down"

    # hybrid_weight：双轨同时运行，按状态权重融合净仓位
    return "hybrid_weight"
```

```text
hybrid_weight 融合示意：
final_target_position = td_target_position × td_weight + bu_target_position × bu_weight
其中 (td_weight, bu_weight) 由 regime 与 gate 状态决定，且 td_weight + bu_weight = 1
```

### 3.4 仓位计算

> **初始资金**：来自 `BacktestConfig.initial_cash`（默认 1,000,000 元）

```text
target_cash = equity × min(signal.position_size, max_position_pct)
shares = floor(target_cash / signal.entry / 100) × 100

约束：
- 单票最大仓位：max_position_pct
- 最大持仓数：max_positions
- 手数必须为 100 股整数倍
```

---

## 4. 交易执行模型（A 股约束）

### 4.1 核心规则

- **T+1 交割**：当日买入不可当日卖出
- **涨跌停限制**：涨停不可买入、跌停不可卖出
- **100 股整手**：买卖数量必须为 100 的整数倍
- **费用模型**：佣金、印花税、过户费、滑点
- **成交口径**：以 execute_date 开盘价为基准（集合竞价），并叠加滑点
- **停牌处理**：停牌日不成交、不计入可卖天数，持仓顺延

### 4.2 成交模拟（集合竞价 + 滑点）

```text
成交可行性模型（tiered_queue，P0）：
- limit_lock_factor：涨停开盘买单=0，跌停开盘卖单=0
- queue_factor = clip(volume_auction / max(order_amount, 1), 0, 1)
- participation_factor = clip(volume_day / max(free_float_shares, 1) / turnover_ref, 0, 1)
- fill_probability = limit_lock_factor × (0.45 × queue_factor + 0.55 × participation_factor)
- 若 fill_probability < config.min_fill_probability：订单记为 rejected（reason=auction_fail）

成交价：
- auction：开盘价 ± 滑点
- fixed/variable：固定或与量能相关的滑点
- tiered：按流动性分层映射 `slippage_bps` 与 `impact_cost_bps`
```

> Qlib 与本地向量化实现共享同一执行口径；backtrader 仅作为兼容适配实现。

### 4.3 信号执行日与成交日

```text
execute_date = next_trading_day(signal_date)
成交价以 execute_date 的开盘价为基准
```

### 4.4 费用模型（A 股）

```text
- 佣金：max(成交额 × commission_rate, min_commission)
- 印花税：仅卖出收取（成交额 × stamp_duty_rate）
- 过户费：买卖双边（成交额 × transfer_fee_rate）
- 滑点：按 slippage_type 计算并体现在成交价
```

### 4.5 涨跌停与成交可行性（无未来函数）

```text
- 若 execute_date 开盘价 = 涨停价：买入成交概率=0
- 若 execute_date 开盘价 = 跌停价：卖出成交概率=0
- 若 execute_date 未开盘/停牌：无成交
```

### 4.6 订单撮合策略（简化且可替换）

```text
- 默认：集合竞价开盘成交（auction）
- 可选：limit（以 signal.entry/stop/target 为限价）
- 订单优先级：卖出先于买入（避免资金占用）
```

### 4.7 资金与持仓更新时点

```text
- 执行成交后立即更新现金与持仓
- 当日净值基于 execute_date 收盘价估值
```

### 4.8 时限平仓规则（max_holding_days）

```text
每日收盘后（signal_date）检查全部持仓：
- holding_days = 已持有交易日数（停牌日不计）
- 若 holding_days >= config.max_holding_days：
  1) 生成强制卖出信号（reason="time_exit"）
  2) 在下一交易日 execute_date 开盘按 §4.2 规则撮合
  3) 若 execute_date 跌停/停牌无法成交，信号顺延到下一可成交日

说明：
- 时限平仓与止损/止盈并行，谁先触发谁先执行；
- 卖出优先级仍遵循 §4.6（卖出先于买入）。
```

### 4.9 止损/止盈退出规则（stop_loss_pct / take_profit_pct）

```text
每日收盘后（signal_date）对全部持仓执行价格风控扫描：

1) 止损触发条件
   drawdown_from_cost = (close_price - position.cost_price) / position.cost_price
   if drawdown_from_cost <= -config.stop_loss_pct:
       生成强制卖出信号（reason="stop_loss"）

2) 止盈触发条件
   gain_from_cost = (close_price - position.cost_price) / position.cost_price
   if gain_from_cost >= config.take_profit_pct:
       生成强制卖出信号（reason="take_profit"）

3) 执行时点与优先级
   - 风控信号在 signal_date 收盘后生成；
   - 在下一交易日 execute_date 开盘按 §4.2 撮合；
   - 若同一持仓同时触发多种退出条件，优先级：
     stop_loss > take_profit > time_exit；
   - 同日组合层面仍执行“先卖后买”。

4) 不可成交顺延
   - 若 execute_date 跌停或停牌导致卖出失败，保留该风控原因并顺延；
   - 次交易日继续按同一原因优先尝试卖出，直到可成交。
```

### 4.10 流动性分层成本模型（P1）

```text
按成交额与换手率分层：
- L1（高流动性）：impact_cost_bps = 5~12
- L2（中流动性）：impact_cost_bps = 12~25
- L3（低流动性）：impact_cost_bps = 25~45

总成本：
total_cost = commission + stamp_tax + transfer_fee + slippage_cost + impact_cost

约束：
- impact_cost_bps > config.impact_cost_bps_cap 时，买单降权或拒绝；
- 同一信号在 L3 档位下需降低 position_size（例如 ×0.6）。
```

---

## 5. 绩效计算口径

### 5.1 收益指标

```
日收益率:
    r_t = equity_t / equity_{t-1} - 1

总收益率:
    total_return = (equity_end - equity_start) / equity_start

年化收益率:
    annual_return = (equity_end / equity_start)^(252/N) - 1
```

### 5.2 风险指标

```
最大回撤:
    drawdown_t = (equity_t - peak_t) / peak_t
    max_drawdown = min(drawdown_t)

波动率:
    volatility = std(r_t) × sqrt(252)
```

### 5.3 风险调整收益

```
Sharpe Ratio:
    sharpe = sqrt(252) × (mean(r_t) - rf/252) / std(r_t)

Sortino Ratio:
    mar_daily = rf / 252
    downside_deviation = sqrt(mean(min(r_t - mar_daily, 0)^2))
    sortino = sqrt(252) × (mean(r_t) - mar_daily) / downside_deviation
    # downside_deviation = 0 时，sortino 置 0

Calmar Ratio:
    calmar = annual_return / abs(max_drawdown)

其中：
- rf = BacktestConfig.risk_free_rate（年化无风险利率，默认 0.015）
```

---

## 6. 数据就绪与降级策略

| 缺失数据 | 处理策略 |
|----------|----------|
| Validation Gate = FAIL | `backtest_state=blocked_gate_fail`，跳过当日信号生成 |
| contract_version 不兼容 | `backtest_state=blocked_contract_mismatch`，阻断并提示迁移 |
| L1 行情缺失 | `backtest_state=warn_data_fallback`，跳过该股票/交易日 |
| L3 集成信号缺失 | `backtest_state=warn_data_fallback`，仅在 Gate 非 FAIL 时退回上一可用日 |
| pas_breadth_daily 缺失 | `backtest_state=warn_mode_fallback`，禁用 BU 回退 TD |
| 涨跌停/停牌导致不可成交 | `backtest_state=blocked_untradable`，订单拒绝或顺延 |

> 降级仅使用“上次可用数据”，不得直连远端。

---

## 7. 回测调度流程

```text
1. 选择引擎（qlib / local_vectorized / backtrader_compat）
2. 解析模式（config_fixed / regime_driven / hybrid_weight）
3. 读取本地 L1/L3 数据
4. 以 signal_date 生成信号（T 日收盘后）
5. 在 execute_date 执行订单（T+1 开盘）
6. 执行成交可行性评估（queue/participation/fill_probability）
7. 执行成交模拟与持仓更新
8. 计算绩效并落库
```

---

## 8. 闭环验收（P0）

- 至少提供 1 条可运行命令：`local_vectorized + top_down`。
- 至少通过 4 组必测：`Gate=FAIL`、`T+1`、`涨跌停不可成交`、`RR<1 过滤`。
- 至少落库 3 类产物：`backtest_results`、`backtest_trade_records`、`state 统计`。
- 必须输出状态机字段：`normal/warn_data_fallback/warn_mode_fallback/blocked_gate_fail/blocked_contract_mismatch/blocked_untradable`。

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.5.1 | 2026-02-14 | 修复 R34（review-012）：增加 `contract_version` 前置兼容检查（当前 `nc-v1`）；不兼容时 `backtest_state=blocked_contract_mismatch` 并阻断 |
| v3.5.0 | 2026-02-14 | 对应 review-006 闭环修复：新增 CP-06 最小可运行闭环命令与验收；成交模型升级为 queue+volume+fill_probability；新增流动性分层成本模型；`blocked_by_gate/degraded/fallback` 统一为 `backtest_state` 状态机；模式切换增加 `regime_driven/hybrid_weight` 口径 |
| v3.4.8 | 2026-02-12 | 修复 R13：§3.1 Step 2 与 §3.2 Step 3 的 recommendation 过滤改为基于 `config.min_recommendation` 的等级比较（`STRONG_BUY > BUY > HOLD > SELL > AVOID`），消除硬编码集合造成的门槛偏差 |
| v3.4.7 | 2026-02-09 | 修复 R26：§3.1/§3.2 增加 Validation Gate FAIL 前置阻断；新增 `risk_reward_ratio < 1.0` 执行层软过滤；补充 recession 协同约束由 Integration 处理说明；§6 增补 Gate FAIL 降级策略 |
| v3.4.6 | 2026-02-09 | 修复 R20：§3.1/§3.2 增加 `direction=neutral` 过滤并与 Trading 对齐；§4 新增 `§4.9` 止损/止盈退出规则（触发条件、执行时点、优先级、不可成交顺延） |
| v3.4.5 | 2026-02-08 | 修复 R13：§4 新增 `max_holding_days` 时限平仓规则（每日检查、T+1 执行、不可成交顺延） |
| v3.4.4 | 2026-02-08 | 修复 R12：BacktestSignal `signal_id` 统一在回测侧生成，不再依赖 Integration 输出字段 |
| v3.4.3 | 2026-02-08 | 修复 R11：§3.1 Step 3 补齐 BacktestSignal 字段透传（`signal_id/stock_name/industry_code/mss_score/irs_score/pas_score/direction/neutrality/risk_reward_ratio/source`） |
| v3.4.2 | 2026-02-08 | 修复 R10：明确 `rf` 来源为 `BacktestConfig.risk_free_rate`，消除 Sharpe/Sortino 口径歧义 |
| v3.4.1 | 2026-02-07 | 修复 R8 P0：Sortino 改为标准下行偏差口径（Downside Deviation），替代 `std(min(r_t,0))` |
| v3.4.0 | 2026-02-07 | 统一选型：Qlib 主选 + 本地向量化执行基线 + backtrader 兼容 |
| v3.3.2 | 2026-02-06 | 明确实现状态；回测引擎选型仅保留 backtrader，qlib 设为规划项 |
| v3.3.1 | 2026-02-05 | 补充费用/滑点/停牌/撮合顺序与估值时点 |
| v3.3.0 | 2026-02-05 | 信号-执行日拆分，明确无未来函数约束；Top-Down/Bottom-Up 角色对齐 |
| v3.2.0 | 2026-02-05 | 对齐 Integration 双模式与 Data Layer：信号改为消费集成输出，明确 TD/BU 入口与 A 股约束 |
| v3.1.0 | 2026-02-05 | 对齐 backtrader/qlib 与双模式：新增 TD/BU 信号流程 |
| v3.0.0 | 2026-01-31 | 重构版：统一算法描述、明确公式 |

---

**关联文档**：
- 数据模型：[backtest-data-models.md](./backtest-data-models.md)
- API接口：[backtest-api.md](./backtest-api.md)
- 信息流：[backtest-information-flow.md](./backtest-information-flow.md)

