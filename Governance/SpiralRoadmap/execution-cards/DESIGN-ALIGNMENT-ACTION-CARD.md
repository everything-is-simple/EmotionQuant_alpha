# 设计-代码对齐行动卡（Design Alignment Action Card）

**状态**: Completed (P0+P1 已修复, P2 已登记债务)  
**更新时间**: 2026-02-25  
**触发**: 双路线图评审（Plan A & Plan B 对齐核心设计）  
**定位**: S0-S2c 已落地代码与核心设计文档的偏差修订行动卡  
**审计范围**: MSS / IRS / PAS / Validation / Integration 五大核心算法模块

---

## 1. 审计总览

| 级别 | 数量 | 含义 |
|---|---|---|
| P0 Critical | 2 | 影响计算正确性，必须立即修 |
| P1 Important | 6 | 设计契约未执行，应尽快修 |
| P2 Structural | 8 | 接口/结构偏差，可登记债务 |
| 合计 | 16 | — |

---

## 2. P0 Critical（必须修，阻断后续圈位）

### P0-1: MSS Z-Score 归一化公式偏离设计

- **设计基线**: `docs/design/core-algorithms/mss/mss-algorithm.md` §7
- **设计公式**: `score = max(0, min(100, (z + 3) / 6 × 100))`（映射 [-3σ,+3σ] → [0,100]）
- **代码位置**: `src/algorithms/mss/engine.py` L80-89
- **代码公式**: `score = 50 + 15 × z`（映射 [-3.33σ,+3.33σ] → [0,100]）
- **影响**: z=±3 时偏差 ±5 分，极端区域周期判定和仓位建议产生偏移
- **修复方案**: 将 `engine.py` 中 `_zscore_normalize` 改为设计公式 `(z+3)/6*100`，移除 `Z_SCORE_CENTER` 和 `Z_SCORE_SCALE` 常量
- **验收**: `z=0→50, z=3→100, z=-3→0`；所有 MSS 单测通过

### P0-2: 跨模块 Z-Score 公式不一致

- **MSS** `engine.py:88`: `50 + 15*z` ❌
- **IRS** `pipeline.py:146`: `((z+3)/6)*100` ✅
- **PAS** `pipeline.py:147`: `((z+3)/6)*100` ✅
- **影响**: 三算法"同权协同"的前提（情绪口径一致）被打破
- **修复方案**: 修复 P0-1 后自动解决
- **验收**: 三模块对同一 z-score 输出相同分数

---

## 3. P1 Important（应修，设计契约未执行）

### P1-1: stale_days > 3 不阻断主流程

- **设计基线**: `mss-algorithm.md` §10.5, `irs-api.md` §3
- **设计要求**: `stale_days > 3` 时抛 `DataNotReadyError`，阻断计算
- **代码位置**: `src/algorithms/mss/engine.py`（`calculate_mss_score`）、`src/algorithms/irs/pipeline.py`（`run_irs_daily`）
- **代码现状**: 仅透传 `stale_days`，无阻断逻辑；`DataNotReadyError` 异常类不存在
- **修复方案**:
  1. 在 `src/algorithms/` 或 `src/config/` 下新增 `DataNotReadyError` 异常类
  2. MSS `calculate_mss_score` 入口检查 `snapshot.stale_days > 3` 时 raise
  3. IRS `run_irs_daily` 入口检查行业快照 `stale_days > 3` 时 raise
- **验收**: stale_days=4 时抛 `DataNotReadyError`；stale_days=3 时正常计算并标记质量

### P1-2: IRS rotation_detail 枚举语言偏离

- **设计基线**: `irs-data-models.md` §3.4 `IrsRotationDetail` 枚举（中文）
- **代码位置**: `src/algorithms/irs/pipeline.py` L218-227
- **代码现状**: 使用英文字符串；缺少"风格转换"分支
- **修复方案**: 将英文值改为设计定义的中文值，补充"风格转换"逻辑
- **验收**: `rotation_detail` 输出值严格落在设计枚举集合内

### P1-3: PAS 涨停判定使用硬编码阈值（违反铁律 #5）

- **设计基线**: A 股规则（铁律 #5）：主板 10% / 创业板科创板 20% / ST 5%
- **代码位置**: `src/algorithms/pas/pipeline.py` L266
- **代码现状**: `pct_chg >= 0.095` 固定 9.5%
- **影响**: 创业板/科创板涨停漏判，ST 正常涨幅误判
- **修复方案**: 引入板块制度映射（需从 `raw_stock_basic` 获取上市板块），按 `board_limit` 分别判定
- **验收**: 创业板股票 pct_chg=15% 不判为涨停；ST 股票 pct_chg=4.8% 判为涨停

### P1-4: MssInputSnapshot 缺少设计必备字段

- **设计基线**: `mss-data-models.md` §2.1 `MssMarketSnapshot`
- **代码位置**: `src/algorithms/mss/engine.py` L158-216 `MssInputSnapshot`
- **缺失字段**: `fall_count`、`flat_count`
- **影响**: 输入验证规则 `rise_count + fall_count ≤ total_stocks` 无法执行
- **修复方案**: 在 `MssInputSnapshot` 中新增 `fall_count`、`flat_count`（默认 0），`from_record` 中解析
- **验收**: 字段存在且可参与输入校验

### P1-5: IRS factor_intermediate 缺少 capital_flow 的 mean/std

- **设计基线**: `irs-data-models.md` §4.2（6 因子全部有独立 mean/std）
- **代码位置**: `src/algorithms/irs/pipeline.py` L602-629
- **代码现状**: factor_rows 中只有 5 组 mean/std
- **修复方案**: 在 `_score_with_history` 中捕获 capital_flow 的 mean/std 并写入 factor_rows
- **验收**: `irs_factor_intermediate` 表包含 `capital_flow_mean` 和 `capital_flow_std` 列

### P1-6: Integration MAX_MODULE_WEIGHT 约束未实际校验

- **设计基线**: `integration-api.md` §2.1（`MAX_MODULE_WEIGHT = 0.60`）
- **代码位置**: `src/integration/pipeline.py`（`run_integrated_daily`）
- **代码现状**: 常量存在但未调用校验
- **修复方案**: 在权重解析后校验 `max(w_mss, w_irs, w_pas) <= 0.60`，违反时回退 baseline
- **验收**: 权重方案含 0.65 时自动回退 baseline 且标记 `warn_weight_violation`

---

## 4. P2 Structural（登记债务，螺旋收口前清理）

### P2-1: Calculator/Repository 类不存在

- **设计**: 每模块定义 OOP 接口（`MssCalculator`, `MssRepository`, ...）
- **现状**: 函数式 API
- **处置**: 登记债务，不阻塞当前修订

### P2-2: Enum 类不存在

- **设计**: `MssCycle(Enum)`, `MssTrend(Enum)`, `PositionAdvice(Enum)`, `IrsRotationStatus(Enum)`, ...
- **现状**: 纯字符串集合
- **处置**: 登记债务

### P2-3: 输出模型命名偏差

- **设计**: `MssPanorama`（无前缀）
- **现状**: `MssScoreResult`（`mss_` 前缀）
- **处置**: 登记债务

### P2-4: 工具函数大量重复

- **现状**: `_table_exists` / `_persist` / `_duckdb_type` 在 5 个模块各复制一遍
- **处置**: 登记债务，后续抽取到 `src/utils/duckdb_helpers.py`

### P2-5: PAS discount 字段未持久化

- **设计**: `liquidity_discount` / `tradability_discount` 为返回契约关键字段
- **现状**: 计算后丢弃，未写入 `stock_pas_daily`
- **处置**: 登记债务

### P2-6: Validation 丰富 API 未实现

- **设计**: 12 个接口（`validate_factor`, `evaluate_candidate`, `build_dual_wfa_windows`, ...）
- **现状**: 仅 `run_validation_gate()`
- **处置**: 登记债务

### P2-7: Integration 模式文档缺失

- **现状**: `dual_verify` / `complementary` 代码已实现
- **设计**: 未明确定义这两种模式
- **处置**: 登记债务，补充设计文档

### P2-8: MSS mss_score 冗余字段

- **设计**: 无此字段（只有 `temperature`）
- **现状**: `mss_score = temperature` 的别名
- **处置**: 登记债务，不急删（有消费方依赖）

---

## 5. 执行顺序

| 轮次 | 项目 | 预估工作量 | 依赖 |
|---|---|---|---|
| 第1轮 | P0-1 + P0-2（MSS Z-Score 公式修复） | 10 分钟 | 无 |
| 第2轮 | P1-1（stale_days 阻断 + DataNotReadyError） | 20 分钟 | 无 |
| 第3轮 | P1-4（MssInputSnapshot 补字段） | 10 分钟 | 无 |
| 第4轮 | P1-3（PAS 涨停板块归一） | 30 分钟 | 需 raw_stock_basic 板块信息 |
| 第5轮 | P1-2（IRS rotation_detail 枚举修正） | 15 分钟 | 无 |
| 第6轮 | P1-5（IRS capital_flow mean/std） | 10 分钟 | 无 |
| 第7轮 | P1-6（Integration 权重上限校验） | 15 分钟 | 无 |
| 登记 | P2-1 ~ P2-8 → debts.md | 10 分钟 | 无 |

---

## 6. run（验证命令）

```bash
pytest tests/unit/algorithms/mss/ -q
pytest tests/unit/algorithms/irs/ -q
pytest tests/unit/algorithms/pas/ -q
pytest tests/unit/algorithms/validation/ -q
pytest tests/unit/integration/ -q
python -m scripts.quality.local_quality_check --contracts --governance
```

---

## 7. 验收标准

- P0：MSS/IRS/PAS 对相同 z-score 输出一致分数
- P1：所有修复项通过对应单测
- P2：全部登记到 `Governance/record/debts.md`
- 全局：`local_quality_check --contracts --governance` 通过

---

## 8. 关联文档

- 设计基线: `docs/design/core-algorithms/mss/mss-algorithm.md` §7
- 设计基线: `docs/design/core-algorithms/irs/irs-algorithm.md`
- 设计基线: `docs/design/core-algorithms/pas/pas-algorithm.md`
- 设计基线: `docs/design/core-algorithms/validation/factor-weight-validation-algorithm.md`
- 设计基线: `docs/design/core-algorithms/integration/integration-algorithm.md`
- 路线状态: `Governance/SpiralRoadmap/planA/VORTEX-EVOLUTION-ROADMAP.md`
- 债务登记: `Governance/record/debts.md`

---

## 9. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-02-25 | 首版：审计 16 项偏差，按 P0/P1/P2 分级，定义执行顺序与验收标准 |
