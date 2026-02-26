# IRS API 接口

**版本**: v4.0.0
**最后更新**: 2026-02-26
**状态**: Pipeline 模式已落地（Python 模块/CLI；当前仓库无 Web API）

---

## 实现状态（仓库现状）

- **现行架构**：过程式 Pipeline + DuckDB 直写。主入口 `run_irs_daily()`（`src/algorithms/irs/pipeline.py:301`），CLI 由 `eq recommend --mode mss_irs_pas --with-validation` 统一触发。
- **TD-DA-001 试点**：`calculator.py`（`IrsCalculator` Protocol + `DefaultIrsCalculator`）与 `repository.py`（`IrsRepository` Protocol + `DuckDbIrsRepository`）已落地为薄封装，当前非主链调用路径。详见附录 A。
- 架构决策 ARCH-DECISION-001：选项 B（文档对齐代码）。
- 接口演进需与 CP-03 同步更新。

---

## 1. 接口定位

当前仓库不包含 Web 后端。IRS 以 **Python 模块接口/CLI** 形式对外提供能力；
如需 HTTP 服务，由 GUI/服务层另行封装。

---

## 2. 模块接口（Python）— Pipeline 模式

### 2.1 Pipeline 编排入口

```python
def run_irs_daily(
    *,
    trade_date: str,
    config: Config,
    artifacts_dir: Path | None = None,
    require_sw31: bool = False,
) -> IrsRunResult:
    """
    IRS 日级 Pipeline 入口（src/algorithms/irs/pipeline.py:301）

    职责：
    1. 从 DuckDB `industry_snapshot`(L2) 加载当日行业快照
    2. 加载行业快照历史、基准指数历史、IRS 评分历史
    3. 执行六因子评分 + 轮动状态 + 配置建议
    4. 持久化结果到 DuckDB `irs_industry_daily`(L3) + `irs_factor_intermediate`
    5. 产出 artifacts（coverage_report / factor_intermediate_sample）

    Returns:
        IrsRunResult（frozen dataclass）
    Raises:
        FileNotFoundError: duckdb_not_found
        ValueError: industry_snapshot_table_missing / industry_snapshot_empty_for_trade_date
        DataNotReadyError: stale_days > config.stale_hard_limit_days
    """
```

### 2.2 返回类型

```python
@dataclass(frozen=True)
class IrsRunResult:
    trade_date: str
    count: int                           # 输出行业数
    frame: pd.DataFrame                  # 评分结果（含 irs_score/quality_flag/rotation_status 等）
    factor_intermediate_frame: pd.DataFrame
    factor_intermediate_sample_path: Path
    coverage_report_path: Path
```

---

## 3. 错误处理

- 非交易日或数据缺失：抛出 `ValueError`。
- 冷启动降级：当 `sample_days < 60` 时，输出 `quality_flag="cold_start"` 与对应 `sample_days`（合法输出，不抛异常）。
- 陈旧数据阻断：当 `stale_days > 3` 时，抛出 `DataNotReadyError`，阻断 IRS 主流程。
- 陈旧数据降级：当 `stale_days <= 3` 但样本不足时，可输出 `quality_flag="stale"`（合法输出，不抛异常）。
- 详细错误码与处理策略见：
  - `docs/design/core-algorithms/irs/irs-algorithm.md`
  - `Governance/archive/archive-capability-v8-20260223/CP-03-irs.md`

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.0.0 | 2026-02-26 | ARCH-DECISION-001：接口定义改为反映实际 Pipeline 模式（`run_irs_daily`）；Calculator/Repository 移入附录 A |
| v3.3.0 | 2026-02-14 | 落地 review-002 修复：`calculate()` 返回契约补充 `allocation_mode/rotation_slope`；新增 `get_allocation_mode()`；错误处理增加 `stale_days > 3` 阻断规则 |
| v3.2.2 | 2026-02-09 | 修复 R27：`calculate()` 返回契约补充 `quality_flag/sample_days`；错误处理补充 `cold_start/stale` 降级语义 |
| v3.2.1 | 2026-02-05 | 移除 HTTP 接口示例，改为模块接口定义 |
| v3.2.0 | 2026-02-04 | 同步 IRS v3.2.0：动量斜率改为连续性因子 |
| v3.0.0 | 2026-01-31 | 重构版 |

---

## 附录 A：Calculator/Repository 接口（未来扩展口径）

TD-DA-001 试点已在 `src/algorithms/irs/calculator.py` 与 `src/algorithms/irs/repository.py` 落地。

```python
@runtime_checkable
class IrsCalculator(Protocol):
    def score(self, source: pd.DataFrame, history: pd.DataFrame, *, trade_date: str, baseline_map: dict | None = None, benchmark_history: pd.DataFrame | None = None, irs_history: pd.DataFrame | None = None) -> pd.DataFrame: ...

@runtime_checkable
class IrsRepository(Protocol):
    def load_industry_snapshot(self, trade_date: str) -> pd.DataFrame: ...
    def load_industry_history(self, trade_date: str) -> pd.DataFrame: ...
    def load_irs_history(self, trade_date: str) -> pd.DataFrame: ...
    def save_daily(self, frame: pd.DataFrame, trade_date: str) -> int: ...
    def save_factor_intermediate(self, frame: pd.DataFrame, trade_date: str) -> int: ...
```

默认实现：`DefaultIrsCalculator`、`DuckDbIrsRepository`。

---

**关联文档**：
- 算法设计：[irs-algorithm.md](./irs-algorithm.md)
- 数据模型：[irs-data-models.md](./irs-data-models.md)
- 信息流：[irs-information-flow.md](./irs-information-flow.md)
- 架构决策：[ARCH-DECISION-001](../../../Governance/record/ARCH-DECISION-001-pipeline-vs-oop.md)



