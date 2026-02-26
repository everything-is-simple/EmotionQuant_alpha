# MSS API 接口

**版本**: v4.0.0
**最后更新**: 2026-02-26
**状态**: Pipeline 模式已落地（Python 模块/CLI；当前仓库无 Web API）

---

## 实现状态（仓库现状）

- **现行架构**：过程式 Pipeline + DuckDB 直写。主入口 `run_mss_scoring()`（`src/algorithms/mss/pipeline.py:334`），核心计算 `calculate_mss_score()`（`src/algorithms/mss/engine.py:440`）。CLI 由 `eq mss`/`eq mss-probe` 提供。
- **TD-DA-001 试点**：`calculator.py`（`MssCalculator` Protocol + `DefaultMssCalculator`）与 `repository.py`（`MssRepository` Protocol + `DuckDbMssRepository`）已落地为薄封装，当前非主链调用路径。详见附录 A。
- 架构决策 ARCH-DECISION-001：选项 B（文档对齐代码），Calculator/Repository 为未来扩展口径。
- 接口演进需与 CP-02 同步更新。

---

## 1. 接口定位

当前仓库不包含 Web 后端。MSS 以 **Python 模块接口/CLI** 形式对外提供能力；
如需 HTTP 服务，由 GUI/服务层另行封装。

---

## 2. 模块接口（Python）— Pipeline 模式

### 2.1 Pipeline 编排入口

```python
def run_mss_scoring(
    *,
    trade_date: str,
    config: Config,
    threshold_mode: str = "adaptive",
    artifacts_dir: Path | None = None,
) -> MssRunResult:
    """
    MSS 日级 Pipeline 入口（src/algorithms/mss/pipeline.py:334）

    职责：
    1. 从 DuckDB `market_snapshot`(L2) 加载当日快照
    2. 从 `mss_panorama` 加载历史温度序列
    3. 解析周期阈值（adaptive/fixed）
    4. 调用 calculate_mss_score() 执行核心计算
    5. 持久化结果到 DuckDB `mss_panorama`(L3)
    6. 产出 artifacts（factor_trace / threshold_snapshot / gate_report / consumption）

    Returns:
        MssRunResult（frozen dataclass）
    Raises:
        RuntimeError: duckdb_not_found / market_snapshot_table_missing
    """
```

### 2.2 核心计算函数

```python
def calculate_mss_score(
    snapshot: MssInputSnapshot,
    *,
    temperature_history: Sequence[float] | None = None,
    threshold_mode: str = "adaptive",
    stale_hard_limit_days: int = 3,
) -> MssPanorama:
    """
    纯计算函数（src/algorithms/mss/engine.py:440）

    输入：MssInputSnapshot + 历史温度序列
    输出：MssPanorama（含 temperature/cycle/trend/rank/percentile 等全量字段）
    Raises:
        DataNotReadyError: stale_days > stale_hard_limit_days 时阻断
    """
```

### 2.3 返回类型

```python
@dataclass(frozen=True)
class MssRunResult:
    trade_date: str
    artifacts_dir: Path
    mss_panorama_count: int
    threshold_mode: str
    has_error: bool
    error_manifest_path: Path
    factor_trace_path: Path
    sample_path: Path
    factor_intermediate_sample_path: Path
    threshold_snapshot_path: Path
    adaptive_regression_path: Path
    gate_report_path: Path
    consumption_path: Path
```

---

## 3. 错误处理

| 场景 | 行为 | 说明 |
|------|------|------|
| 非交易日 | 抛 `ValueError` | 输入非法，拒绝计算 |
| 必备字段缺失 | 抛 `ValueError` | 不允许“沿用前值”兜底 |
| `stale_days > 3` | 抛 `DataNotReadyError` | 依赖数据未就绪，阻断主流程 |
| `stale_days <= 3` | 允许计算（降级） | 结果可用，但必须打质量标记 |
| 统计参数缺失（mean/std） | 对缺失因子回退 50 分 | 不抛错，记录告警 |
| 趋势输入异常 | 输出 `cycle=unknown` | 属于合法降级，不抛异常 |

强制约束：
- 不允许沿用上一交易日 `temperature/cycle/trend` 作为兜底输出。
- 详细错误码与处理策略见：
  - `docs/design/core-algorithms/mss/mss-algorithm.md`
  - `Governance/archive/archive-capability-v8-20260223/CP-02-mss.md`

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.0.0 | 2026-02-26 | ARCH-DECISION-001：接口定义改为反映实际 Pipeline 模式（`run_mss_scoring` / `calculate_mss_score`）；Calculator/Repository 移入附录 A |
| v3.2.0 | 2026-02-14 | 落地 review-001 修复：增加 `get_extreme_direction_bias()` 读取接口；错误处理改为矩阵化定义，明确 `stale_days` 分层处理与“禁止沿用前值”约束 |
| v3.1.2 | 2026-02-09 | 修复 R27：`get_cycle()` 返回值文档补充 `unknown` 合法降级语义；错误处理补充 `unknown` 与 `DataNotReadyError` 的边界 |
| v3.1.1 | 2026-02-05 | 移除 HTTP 接口示例，改为模块接口定义；与路线图/仓库架构对齐 |
| v3.1.0 | 2026-02-04 | 同步 MSS v3.1.0：补齐验收口径（count→ratio→zscore）；factors 示例补充 final_weight/inverse_score 并与温度公式一致 |
| v3.0.0 | 2026-01-31 | 重构版：统一API风格、添加枚举映射、完善错误处理 |

---

## 附录 A：Calculator/Repository 接口（未来扩展口径）

TD-DA-001 试点已在 `src/algorithms/mss/calculator.py` 与 `src/algorithms/mss/repository.py` 落地为 Protocol 薄封装，当前非主链调用路径。若未来需要多实现替换（如内存桨/文件桨），可提升为主链。

```python
# Protocol 定义（src/algorithms/mss/calculator.py）
@runtime_checkable
class MssCalculator(Protocol):
    def calculate(self, snapshot: MssInputSnapshot, *, temperature_history: Sequence[float] | None = None, threshold_mode: str = "adaptive", stale_hard_limit_days: int = 3) -> MssPanorama: ...

# Protocol 定义（src/algorithms/mss/repository.py）
@runtime_checkable
class MssRepository(Protocol):
    def load_snapshot(self, trade_date: str) -> MssInputSnapshot: ...
    def load_temperature_history(self, trade_date: str, *, limit: int = 252) -> list[float]: ...
    def save_panorama(self, panorama: MssPanorama, trade_date: str) -> int: ...
```

默认实现：`DefaultMssCalculator`（委托 `calculate_mss_score`）、`DuckDbMssRepository`（DuckDB 读写）。

---

**关联文档**：
- 算法设计：[mss-algorithm.md](./mss-algorithm.md)
- 数据模型：[mss-data-models.md](./mss-data-models.md)
- 信息流：[mss-information-flow.md](./mss-information-flow.md)
- 架构决策：[ARCH-DECISION-001](../../../Governance/record/ARCH-DECISION-001-pipeline-vs-oop.md)



