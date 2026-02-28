# R2 MSS 重建 — 执行卡

**阶段目标**：MSS 代码 OOP 化 + 文档修正 + 补齐缺失防御，温度/周期/趋势可信。
**总工期**：4-5 天
**前置条件**：R1 完成（依赖正确的 market_snapshot）
**SOS 覆盖**：docs/sos/mss 全部 12 项

---

## CARD-R2.1: 修复 P0 文档矛盾（3 项）

**工作量**：1 天
**优先级**：P0（文档是权威口径，矛盾会误导开发）
**SOS 映射**：MSS-P0-1, MSS-P0-2, MSS-P0-3

### 交付物

- [ ] 重写 `mss-information-flow.md` §2.6 Step 6
  - 删除"3日严格递增/递减"描述
  - 替换为正式方案：EMA(3) vs EMA(8) 交叉 + 5日斜率 + 动态 trend_band
  - 明确标注冷启动回退方案（<8日样本时使用3日递增/递减）
- [ ] 重写 `mss-information-flow.md` §6.1 异常处理
  - 删除"数据缺失时使用前一日数据"
  - 替换为实际行为：total_stocks≤0 → 回退中性分 50；stale_days>3 → 抛 DataNotReadyError
  - 明确"禁止沿用前一日 temperature/cycle/trend"的安全约束
- [ ] 重写 `mss-information-flow.md` §3 组件架构图
  - 删除虚构的 7 类 OOP 架构（MssController/MssService 等）
  - 替换为实际 Pipeline 模式：`run_mss_scoring()` → `calculate_mss_score()`
  - 标注"OOP 架构为 R2 目标，当前为 Pipeline 模式"

### 验收标准

1. information-flow §2.6 与 algorithm §5.4 描述一致
2. information-flow §6.1 与 algorithm §10.5 描述一致
3. information-flow §3 架构图与实际代码结构一致

---

## CARD-R2.2: MssService OOP 门面 + 输入验证

**工作量**：1.5 天
**优先级**：P0（架构对齐）+ P1（输入验证）
**前置依赖**：CARD-R0.1（BaseService 基类）
**SOS 映射**：MSS-P0-3（OOP 化）, MSS-P1-2（输入验证）

### 交付物

- [ ] 创建 `src/algorithms/mss/service.py`
  - `MssService(BaseService)` 类
  - 构造函数注入 `config: Config`, `repository: MssRepository`
  - 方法：
    - `calculate(trade_date: str) -> MssPanorama`
    - `get_panorama(trade_date: str) -> MssPanorama`
    - `get_temperature_history(start_date: str, end_date: str) -> pd.DataFrame`
- [ ] 创建 `src/algorithms/mss/repository.py`
  - `MssRepository(BaseRepository)` 类
  - 方法：`read_market_snapshot()`, `write_panorama()`, `read_panorama_history()`
- [ ] 补齐 6 条零容忍输入验证（`engine.py` / `MssInputSnapshot`）
  - `total_stocks > 0`（已有）
  - `rise_count <= total_stocks`
  - `fall_count <= total_stocks`
  - `limit_up_count <= touched_limit_up`
  - `strong_up_count <= rise_count`
  - `strong_down_count <= fall_count`
  - 违反时抛 `ValidationError` 而非静默返回 0
- [ ] 修复 `_to_int` / `_to_float` 静默吞零问题
  - 改为：缺失字段 → 抛 `DataNotReadyError`（而非默认 0）
  - 仅对真正可选字段保留默认值

### 验收标准

1. `MssService` 可被 Integration/GUI 模块导入使用
2. 输入脏数据（rise_count > total_stocks）触发 ValidationError
3. 单元测试可 mock `MssRepository` 独立测试 service 逻辑
4. `mypy src/algorithms/mss/` 通过

### 技术要点

- `MssRepository` 读写 DuckDB `mss_panorama` 表
- `MssService.calculate()` 内部调用 `engine.calculate_mss_score()`，service 负责数据获取和持久化

---

## CARD-R2.3: 修复 P1-P3 代码与模型问题

**工作量**：1 天
**优先级**：P1-P3
**前置依赖**：CARD-R2.2
**SOS 映射**：MSS-P1-1, MSS-P2-1, MSS-P2-2, MSS-P3-1~P3-5

### 交付物

- [ ] P1-1：Z-Score baseline 技术债登记
  - 在 `engine.py:46-53` 添加注释标注当前为硬编码冷启动状态
  - 在 `Governance/record/debts.md` 登记："MSS Z-Score baseline parquet 加载为 Phase-2 目标"
  - 在 `MssService` 中预留 `load_baseline(path: Path)` 方法签名（空实现 + TODO）
- [ ] P2-1：修复返回类型注解
  - `engine.py:462` 注解从 `-> MssScoreResult` 改为 `-> MssPanorama`
  - 删除 `pipeline.py:28` 的 `MssScoreResult = MssPanorama` 别名
  - 全局替换所有 `MssScoreResult` 引用为 `MssPanorama`
- [ ] P2-2：更新 `mss-data-models.md`
  - 输入模型补齐：`data_quality`, `stale_days`, `source_trade_date`
  - 输出模型补齐：`data_quality`, `stale_days`, `contract_version`, `created_at`
  - 字段命名对齐：`temperature` ↔ `mss_temperature` 选定一个规范名并全局统一
- [ ] P3-1：预警规则标注
  - 在 `engine.py` 添加 `# TODO R9: 实现 4 种预警（过热/过冷/尾部活跃/趋势背离）`
  - 在 `MssService` 预留 `check_alerts(panorama: MssPanorama) -> list[Alert]` 签名
- [ ] P3-2：PositionAdvice 枚举替换
  - 将字符串映射改为 `from src.models.enums import PositionAdvice` 枚举
- [ ] P3-5：补齐 `yesterday_limit_up_today_avg_pct` 字段
  - 在 `MssInputSnapshot` 中添加字段定义（可选，默认 None）
  - 标注为观测字段，不参与评分计算

### 验收标准

1. `mypy src/algorithms/mss/` 无 NameError
2. PositionAdvice 使用枚举而非字符串
3. 数据模型文档与代码字段 1:1 对齐

---

## CARD-R2.4: 契约测试 + 温度验证

**工作量**：1 天
**优先级**：P1（质量闭环）
**前置依赖**：CARD-R2.1~R2.3

### 交付物

- [ ] 契约测试 `tests/contracts/test_mss.py`
  - 检查 `mss_panorama` 表 16 字段完整性
  - 检查 temperature 值在 [0, 100] 范围
  - 检查 cycle_state 为 8 种合法状态之一
  - 检查 trend_direction 为 UP/DOWN/SIDEWAYS 之一
  - 检查 neutrality = `1 - |temperature - 50| / 50`
- [ ] 温度曲线 3 日重跑验证
  - 选择 3 个代表性交易日
  - 对比重建前后 MSS 输出（温度/周期/趋势/仓位建议）
  - 输出验证报告：`artifacts/r2-validation-report.md`
- [ ] 重构 `mss/pipeline.py`
  - pipeline 仅保留编排代码（加载配置 → 调用 MssService → 输出日志）
  - 业务逻辑全部在 MssService + engine.py 中

### 验收标准

1. 契约测试在 3 个交易日上全部通过
2. 温度曲线与 R1 修复后的快照数据一致（无 cascade 污染）
3. `pipeline.py` 代码行数减少 50%+
4. 13/13 核心公式保持正确（无回归）

### 技术要点

- 契约测试使用 `pytest.mark.contract` 标记
- 验证报告格式：每个字段一行 [实际值 / 预期值 / 偏差 / 判定]
- 重跑时对比的基准是 `mss-algorithm.md` 的公式，不是旧代码输出

---

## R2 阶段验收总览

完成以上 4 张卡后，需满足：

1. **P0 文档修正**：information-flow 3 处矛盾全部消除
2. **OOP 架构**：MssService + MssRepository 可用，pipeline 仅做编排
3. **输入验证**：6 条零容忍约束全部实现，脏数据不再静默通过
4. **类型正确**：mypy 零错误，返回类型注解正确
5. **质量闭环**：契约测试通过 + 3 日温度验证无偏差

**下一步**：进入 R3 IRS + PAS 重建（24+ 项偏差，本路线图最大工作量阶段）。
