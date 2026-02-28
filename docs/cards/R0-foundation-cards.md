# R0 工程基座 — 执行卡

**阶段目标**：建立标准化项目骨架，所有后续模块在此骨架上实现。
**总工期**：3-4 天
**前置条件**：无

---

## CARD-R0.1: 创建核心基础设施层

**工作量**：1 天
**优先级**：P0（阻塞所有后续模块）
**前置依赖**：无

### 交付物

- [ ] `src/core/base.py`
  - `BasePipeline` 抽象基类（定义 `run()` 接口）
  - `BaseService` 抽象基类（构造函数注入 `config` + `repository`）
  - `BaseRepository` 抽象基类（定义 `connect()` / `close()` / `execute_query()` 接口）
- [ ] `src/core/protocols.py`
  - `ConfigProtocol`（类型化配置接口）
  - `RepositoryProtocol`（依赖注入接口）
  - `EngineProtocol`（纯计算引擎接口）
- [ ] `src/core/exceptions.py`
  - 从 `src/config/exceptions.py` 迁移现有异常
  - 新增：`DataNotReadyError`, `GateFailError`, `ValidationError`, `IntegrationError`, `BacktestError`, `TradingError`
  - 异常体系层级：`EmotionQuantError` → 模块级异常 → 具体异常
- [ ] `src/core/types.py`
  - 类型别名：`TradeDate = str`, `StockCode = str`, `Score = float`
  - 工具函数：`validate_trade_date()`, `validate_stock_code()`

### 验收标准

1. 所有基类可被其他模块继承且不报类型错误
2. `mypy src/core/` 通过
3. 异常体系可被 `except EmotionQuantError` 统一捕获

### 技术要点

- `BasePipeline.run()` 返回 `RunResult` dataclass（含 `state`, `artifacts`, `errors`）
- `BaseRepository` 使用上下文管理器协议 `__enter__` / `__exit__`
- Protocol 用于依赖注入，不强制继承

---

## CARD-R0.2: 创建共享计算模块

**工作量**：1 天
**优先级**：P0（Trading/Backtest 依赖）
**前置依赖**：CARD-R0.1

### 交付物

- [ ] `src/shared/zscore.py`
  - `normalize_zscore(series: pd.Series, baseline_mean: float, baseline_std: float) -> pd.Series`
  - 统一公式：`(z + 3) / 6 × 100`
  - 处理边界：`std=0` 时返回 50（中性分）
- [ ] `src/shared/execution_model.py`
  - `calculate_fill_probability(queue_ratio: float, participation_ratio: float, limit_lock: bool) -> float`
  - `calculate_fill_ratio(queue_ratio: float, capacity_ratio: float) -> float`
  - 公式对齐 backtest-algorithm.md §4.2
- [ ] `src/shared/fee_calculator.py`
  - `calculate_commission(amount: float, rate: float = 0.0003) -> float`
  - `calculate_stamp_tax(amount: float, direction: str) -> float`（卖出 0.001，买入 0）
  - `calculate_impact_cost(amount: float, liquidity_tier: str) -> float`（L1/L2/L3 → 8/18/35 bps）

### 验收标准

1. 单元测试覆盖 3 个边界场景（正常/极值/零值）
2. Trading 和 Backtest 可通过 `from src.shared import zscore, execution_model, fee_calculator` 导入
3. 所有函数带完整 docstring + 类型注解

### 技术要点

- `fill_probability` 公式：`limit_lock_factor × (0.45 × queue + 0.55 × participation)`
- `impact_cost` 返回基点（bps），调用侧需 `× amount / 10000`

---

## CARD-R0.3: 完善全局枚举

**工作量**：0.5 天
**优先级**：P1（多模块依赖）
**前置依赖**：CARD-R0.1

### 交付物

- [ ] `src/models/enums.py` 补齐以下枚举：
  - `ValidatedFactor(Enum)`：15 个因子（mss_market_coefficient, mss_profit_effect 等）
  - `PositionAdvice(Enum)`：OVERWEIGHT, STANDARD, UNDERWEIGHT, AVOID
  - `CycleState(Enum)`：8 个周期状态（EXPLOSIVE_BULL 等）
  - `IntegrationMode(Enum)`：TOP_DOWN, BOTTOM_UP, DUAL_VERIFY, COMPLEMENTARY
  - `BacktestState(Enum)`：NORMAL, WARN_DATA_FALLBACK, BLOCKED_GATE_FAIL 等
  - `LiquidityTier(Enum)`：L1, L2, L3
  - `RejectReason(Enum)`：11 个拒单原因
- [ ] 保留现有：`RecommendationGrade`, `GateDecision`, `RotationStatus`

### 验收标准

1. 所有枚举值有文档字符串说明语义
2. `ValidatedFactor` 15 个值与 validation-data-models.md §1.1 完全一致
3. IDE 自动补全可正确提示所有枚举值

---

## CARD-R0.4: 搭建模块目录骨架

**工作量**：0.5 天
**优先级**：P2（组织结构）
**前置依赖**：CARD-R0.1

### 交付物

- [ ] 创建以下空文件（带 `# TODO: R{N} 阶段实现` 占位符）：
  - `src/data/service.py`
  - `src/algorithms/mss/service.py` + `models.py` + `repository.py`
  - `src/algorithms/irs/service.py` + `models.py` + `repository.py`
  - `src/algorithms/pas/service.py` + `engine.py` + `models.py` + `repository.py`
  - `src/algorithms/validation/service.py` + `engine.py` + `models.py` + `repository.py`
  - `src/algorithms/integration/service.py` + `engine.py` + `models.py` + `repository.py`（从 `src/integration/` 移动目录结构）
  - `src/backtest/service.py` + `engine.py` + `models.py` + `repository.py` + `adapters/qlib_adapter.py` + `adapters/local_engine.py`
  - `src/trading/service.py` + `engine.py` + `models.py` + `repository.py` + `risk/risk_manager.py`
  - `src/analysis/service.py` + `engine.py` + `models.py` + `repository.py` + `reports/daily_report.py`
  - `src/gui/services/data_service.py` + `services/cache_service.py` + `services/filter_service.py` + `services/chart_service.py` + `services/export_service.py`
- [ ] 所有 `__init__.py` 文件补齐（空文件或简单 `__all__` 导出）

### 验收标准

1. `python -c "import src.algorithms.mss.service"` 不报 ImportError
2. 目录树符合路线图 §1.1 规范
3. `src/integration/` 已移动到 `src/algorithms/integration/`

---

## CARD-R0.5: 标准化测试目录 + CI 配置

**工作量**：1 天
**优先级**：P1（质量保障）
**前置依赖**：CARD-R0.4

### 交付物

- [ ] 重组 `tests/` 目录：
  - `tests/unit/{module}/` — 现有单元测试迁移
  - `tests/contracts/{module}/` — 契约测试（新建占位文件）
  - `tests/canary/` — 金丝雀数据包（新建 README.md 说明预期结构）
- [ ] `tests/contracts/` 模板：
  - `test_data_layer.py`（检查 market_snapshot 28 字段）
  - `test_mss.py`（检查 mss_panorama 16 字段）
  - `test_irs.py`（检查 irs_industry_daily 18 字段）
  - `test_pas.py`（检查 stock_pas_daily 20 字段）
  - `test_validation.py`（检查 validation_gate_decision 12 字段）
  - `test_integration.py`（检查 integrated_recommendation 28 字段）
- [ ] CI 配置（选一个）：
  - `.github/workflows/ci.yml`（GitHub Actions）或
  - `.gitlab-ci.yml`（GitLab CI）
  - 内容：`lint` (ruff) → `typecheck` (mypy) → `test` (pytest)
- [ ] `pyproject.toml` 或 `setup.cfg` 整理：
  - 确保 `pytest`, `mypy`, `ruff` 配置项存在
  - 添加 `src/` 到 Python path

### 验收标准

1. `pytest tests/unit/ -q` 跑通（现有测试不回归）
2. `pytest tests/contracts/ -q` 报 skip（占位测试尚未实现）
3. `mypy src/ --ignore-missing-imports` 通过（仅检查 R0 新代码）
4. CI 推送后自动触发（可手动触发一次验证）

### 技术要点

- 契约测试使用 `pytest.mark.contract` 标记，可通过 `-m contract` 单独运行
- 金丝雀 README 说明：10 日 × 8 表 × 50-100 只，parquet 格式
- CI 先跑 lint/typecheck（快速失败），再跑 test（耗时）

---

## R0 阶段验收总览

完成以上 5 张卡后，需满足：

1. **可导入性**：所有 `src/core/`, `src/shared/`, `src/models/` 模块可被导入且不报错
2. **类型正确性**：`mypy src/core/ src/shared/ src/models/` 零错误
3. **测试框架可用**：`pytest tests/unit/` 能跑（即使部分 skip）
4. **CI 自动化**：推送代码触发 lint → typecheck → test 流水线
5. **目录规范**：所有后续模块的占位文件已就位，import 路径正确

**下一步**：进入 R1 数据层重建（修复 14 项 P0/P1/P2 偏差）。
