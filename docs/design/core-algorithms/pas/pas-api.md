# PAS API 接口

**版本**: v4.0.0
**最后更新**: 2026-02-26
**状态**: Pipeline 模式已落地（Python 模块/CLI；当前仓库无 Web API）

---

## 实现状态（仓库现状）

- **现行架构**：过程式 Pipeline + DuckDB 直写。主入口 `run_pas_daily()`（`src/algorithms/pas/pipeline.py:122`），CLI 由 `eq recommend --mode mss_irs_pas --with-validation` 统一触发。
- PAS 暂无 Calculator/Repository 试点封装（仅 MSS/IRS 已完成 TD-DA-001 试点）。设计中的 PasCalculator/PasRepository 为未来扩展口径，详见附录 A。
- 架构决策 ARCH-DECISION-001：选项 B（文档对齐代码）。
- 接口演进需与 CP-04 同步更新。

---

## 1. 接口定位

当前仓库不包含 Web 后端。PAS 以 **Python 模块接口/CLI** 形式对外提供能力；
如需 HTTP 服务，由 GUI/服务层另行封装。

---

## 2. 模块接口（Python）— Pipeline 模式

### 2.1 Pipeline 编排入口

```python
def run_pas_daily(
    *,
    trade_date: str,
    config: Config,
    artifacts_dir: Path | None = None,
) -> PasRunResult:
    """
    PAS 日级 Pipeline 入口（src/algorithms/pas/pipeline.py:122）

    职责：
    1. 从 DuckDB `raw_daily`(L1) 加载当日行情数据
    2. 加载个股历史行情
    3. 执行三因子评分 + 方向判定 + RR 计算 + 自适应窗口
    4. 持久化结果到 DuckDB `stock_pas_daily`(L3) + `pas_factor_intermediate`
    5. 产出 artifacts（factor_intermediate_sample）

    Returns:
        PasRunResult（frozen dataclass）
    Raises:
        FileNotFoundError: duckdb_not_found
        ValueError: raw_daily_table_missing / raw_daily_empty_for_trade_date
    """
```

### 2.2 返回类型

```python
@dataclass(frozen=True)
class PasRunResult:
    trade_date: str
    count: int                           # 输出股票数
    frame: pd.DataFrame                  # 评分结果（含 pas_score/pas_direction/risk_reward_ratio/opportunity_grade 等）
    factor_intermediate_frame: pd.DataFrame
    factor_intermediate_sample_path: Path
```

---

## 3. 错误处理

### 3.1 降级与异常语义

- 非交易日：抛出 `ValueError`。
- 关键字段缺失（无法计算结构/风险）：抛出 `ValueError`。
- 历史样本不足：允许计算，但返回 `quality_flag="cold_start"`。
- 数据滞后（`stale_days > 0`）：允许返回观察结果，但标记 `quality_flag="stale"`，执行层不得入场。

### 3.2 返回契约关键字段（StockPasDaily）

- 名义与执行双口径：`risk_reward_ratio`（分析）+ `effective_risk_reward_ratio`（执行）。
- 成交约束透明化：`liquidity_discount`、`tradability_discount`。
- 质量治理字段：`quality_flag`、`sample_days`、`adaptive_window`。

### 3.3 契约漂移处理

- `run_contract_checks()` 失败时返回失败明细并阻断当日执行链路（Backtest/Trading）。
- 详细规则与处理策略见：
  - `docs/design/core-algorithms/pas/pas-algorithm.md`
  - `docs/design/core-algorithms/pas/pas-data-models.md`
  - `Governance/archive/archive-capability-v8-20260223/CP-04-pas.md`

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.0.0 | 2026-02-26 | ARCH-DECISION-001：接口定义改为反映实际 Pipeline 模式（`run_pas_daily`）；PasCalculator/PasRepository 移入附录 A |
| v3.2.0 | 2026-02-14 | 修复 review-003：API 契约补齐 `effective_risk_reward_ratio` 与质量字段语义 |
| v3.1.3 | 2026-02-08 | 修复 R19：补充 `get_by_grade` |
| v3.1.2 | 2026-02-08 | 修复 R17：`get_by_industry` 迁移到 Repository |
| v3.1.1 | 2026-02-05 | 移除 HTTP 接口示例 |
| v3.1.0 | 2026-02-04 | 同步 PAS v3.1.0 |
| v3.0.0 | 2026-01-31 | 重构版 |

---

## 附录 A：PasCalculator/PasRepository 接口（未来扩展口径）

当前 PAS 未落地 Calculator/Repository 封装（仅 MSS/IRS 已完成 TD-DA-001 试点）。以下为规划接口，供未来推广参考：

```python
class PasCalculator(Protocol):
    def calculate(self, trade_date: str, stock_code: str) -> StockPasDaily: ...
    def batch_calculate(self, trade_date: str, stock_codes: List[str] = None) -> List[StockPasDaily]: ...

class PasRepository(Protocol):
    def save_batch(self, pas_dailies: List[StockPasDaily]) -> int: ...
    def get_by_date(self, trade_date: str) -> List[StockPasDaily]: ...
    def get_by_stock(self, stock_code: str, limit: int = 30) -> List[StockPasDaily]: ...
    def get_by_industry(self, trade_date: str, industry_code: str) -> List[StockPasDaily]: ...
    def get_by_grade(self, trade_date: str, grades: List[str]) -> List[StockPasDaily]: ...
```

---

**关联文档**：
- 算法设计：[pas-algorithm.md](./pas-algorithm.md)
- 数据模型：[pas-data-models.md](./pas-data-models.md)
- 信息流：[pas-information-flow.md](./pas-information-flow.md)
- 架构决策：[ARCH-DECISION-001](../../../Governance/record/ARCH-DECISION-001-pipeline-vs-oop.md)



