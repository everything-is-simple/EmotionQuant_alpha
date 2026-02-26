# Integration API 接口

**版本**: v4.0.0
**最后更新**: 2026-02-26
**状态**: Pipeline 模式已落地（Python 模块/CLI；当前仓库无 Web API）

---

## 实现状态（仓库现状）

- **现行架构**：过程式 Pipeline + DuckDB 直写。主入口 `run_integrated_daily()`（`src/integration/pipeline.py:573`），CLI 由 `eq recommend --mode integrated --with-validation-bridge` 触发。
- Integration 暂无 IntegrationEngine/IntegrationRepository 类封装。设计中的 OOP 接口为未来扩展口径，详见附录 A。
- 架构决策 ARCH-DECISION-001：选项 B（文档对齐代码）。
- 接口演进需与 CP-05 同步更新。

---

## 1. 接口定位

当前仓库不包含 Web 后端。Integration 以 **Python 模块接口/CLI** 形式对外提供能力；
如需 HTTP 服务，由 GUI/服务层另行封装。

---

## 2. 模块接口（Python）— Pipeline 模式

### 2.1 Pipeline 编排入口

```python
def run_integrated_daily(
    *,
    trade_date: str,
    config: Config,
    with_validation_bridge: bool = False,
    integration_mode: str = "top_down",
) -> IntegrationRunResult:
    """
    Integration 日级 Pipeline 入口（src/integration/pipeline.py:573）

    职责：
    1. 从 DuckDB 读取 MSS(mss_panorama) / IRS(irs_industry_daily) / PAS(stock_pas_daily)
    2. 读取 Validation Gate 决策(validation_gate_decision) 与权重方案(validation_weight_plan)
    3. 执行三算法加权集成 + 状态机分类 + RR 过滤
    4. 持久化 `integrated_recommendation`(L3) + `quality_gate_report`
    5. 支持模式：top_down / dual_verify / complementary

    Returns:
        IntegrationRunResult（frozen dataclass）
    Raises:
        FileNotFoundError: duckdb_not_found
        ValueError: required_tables_missing / mss_panorama_empty / irs/pas_empty / validation_gate_empty
    """
```

### 2.2 返回类型

```python
@dataclass(frozen=True)
class IntegrationRunResult:
    trade_date: str
    count: int                    # 集成推荐总数
    integration_mode: str         # top_down / dual_verify / complementary
    frame: pd.DataFrame           # 集成推荐 DataFrame
    quality_status: str           # PASS / WARN / FAIL
    quality_frame: pd.DataFrame   # 质量门禁报告
    validation_gate: str          # 上游 Validation Gate 决策
    integration_state: str        # normal / warn_* / blocked_*
    go_nogo: str                  # GO / NO_GO
    rr_filtered_count: int        # RR 过滤数量
    quality_message: str
```

### 2.3 Validation 桥接调用约定

当 `with_validation_bridge=True` 时，Pipeline 内部从 `validation_weight_plan` 解析权重方案；
`selected_weight_plan` -> `WeightPlan` 的桥接责任在 Pipeline 内部函数 `_resolve_weight_plan()`。

---

## 3. 错误处理

- 权重违规：抛出 `WeightViolationError`。
- 输入数据缺失：抛出 `ValueError` 或进入统一状态机 `warn_*`。
- Gate=FAIL：抛出 `ValidationGateError` 并阻断集成输出。
- 契约版本不兼容（`contract_version != "nc-v1"`）：抛出 `ContractVersionError` 并阻断输出。
- 若 IRS 输入全部为 `quality_flag="cold_start"`：不抛异常，强制回退 baseline 权重并按 WARN 继续输出（用于下游识别低置信度）。
- 若候选方案执行约束不达标（可成交性/冲击成本）：不抛异常，回退 baseline，并标记 `warn_candidate_exec`。
- 详细错误码与处理策略见：
  - `docs/design/core-algorithms/integration/integration-algorithm.md`
  - `Governance/archive/archive-capability-v8-20260223/CP-05-integration.md`

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.0.0 | 2026-02-26 | ARCH-DECISION-001：接口定义改为反映实际 Pipeline 模式（`run_integrated_daily`）；IntegrationEngine/IntegrationRepository 移入附录 A |
| v3.5.1 | 2026-02-14 | 修复 R34：`calculate()` 增加 `contract_version` 输入；契约版本不兼容阻断 |
| v3.5.0 | 2026-02-14 | 新增 `resolve_regime_parameters/classify_integration_state/check_candidate_executability` |
| v3.4.4 | 2026-02-09 | 补充 Validation -> Integration 权重桥接调用约定 |
| v3.4.3 | 2026-02-09 | 错误处理补充 `Gate=FAIL` 与“全行业 cold_start” |
| v3.4.0 | 2026-02-07 | 接入 Validation Gate 与 weight_plan |
| v3.3.1 | 2026-02-05 | 移除 HTTP 接口示例 |
| v3.0.0 | 2026-01-31 | 重构版 |

---

## 附录 A：IntegrationEngine/IntegrationRepository 接口（未来扩展口径）

当前 Integration 未落地 OOP 封装。以下为规划接口，供未来推广参考：

```python
class IntegrationEngine:
    MAX_MODULE_WEIGHT = 0.60
    def calculate(self, mss_input, irs_inputs, pas_inputs, weight_plan, validation_gate_decision, contract_version="nc-v1") -> List[IntegratedRecommendation]: ...
    def verify_weight_plan(self, weight_plan: WeightPlan) -> bool: ...
    def classify_integration_state(self, gate, irs_quality_flag: str) -> str: ...

class IntegrationRepository:
    def save_batch(self, recommendations) -> int: ...
    def get_by_date(self, trade_date: str) -> List[IntegratedRecommendation]: ...
```

---

**关联文档**：
- 算法设计：[integration-algorithm.md](./integration-algorithm.md)
- 数据模型：[integration-data-models.md](./integration-data-models.md)
- 信息流：[integration-information-flow.md](./integration-information-flow.md)
- 架构决策：[ARCH-DECISION-001](../../../Governance/record/ARCH-DECISION-001-pipeline-vs-oop.md)



