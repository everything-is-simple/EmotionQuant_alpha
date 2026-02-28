# R9 增强包 + 稳定化 — 执行卡

**阶段目标**：ENH-01~11 落地 + 全链路一致性验证 + 文档收口。
**总工期**：7-10 天
**前置条件**：R8 完成
**SOS 覆盖**：docs/sos/enhancements 全部 15 项

---

## CARD-R9.1: 统一 CLI + 数据预检 + 失败产物

**工作量**：1.5 天
**优先级**：P1
**SOS 映射**：E-01, E-02, E-03, E-04, E-05, E-06

### 交付物

- [ ] ENH-01 统一 CLI 入口
  - `eq run` — 全链路运行
  - `eq mss` — 单独 MSS
  - `eq recommend` — Integration 推荐
  - `eq backtest` — 回测
  - `eq trade` — 纸上交易
  - `eq gui` — 启动 GUI
  - 保留现有 argparse（无需迁移到 Typer/Click）
  - 补齐 `--source mock` 路径：指向 `tests/fixtures/canary_10d/` parquet
- [ ] ENH-02 数据预检
  - `validate_token()`：`tushare.pro_api().trade_cal()` 轻量请求验证
  - token 无效 → 明确报错（非首次正式请求才暴露）
  - 限流守卫：重试策略改为指数退避（30s → 60s → 120s）
  - 异常类细化：`DataFetchError` / `RateLimitError` / `ConnectionError`（从当前单一 `FetchError` 拆分）
- [ ] ENH-03 失败产物协议
  - 统一 error_manifest 格式：`{error_level: "P0/P1/P2", step: "...", timestamp: "...", message: "..."}`
  - 创建 `src/core/error_manifest.py`：`write_error_manifest(path, errors)` 统一写入函数
  - 所有模块使用统一函数（删除各自 `_write_json()` 实现）

### 验收标准

1. `eq run --source mock` 可使用 canary parquet 运行全链路
2. token 无效时首个命令即报 `validate_token failed`
3. 重试间有退避等待（非 immediate retry）
4. error_manifest JSON 格式统一（含 error_level + timestamp）

---

## CARD-R9.2: 契约测试 + 金丝雀数据包

**工作量**：1.5 天
**优先级**：P1
**SOS 映射**：E-07, E-08

### 交付物

- [ ] ENH-05 金丝雀数据包
  - 创建 `tests/fixtures/canary_10d/` 目录
  - 生成 10 天 × 8 表 × 50-100 只股票的 parquet 文件：
    - raw_daily, raw_daily_basic, raw_limit_list, trade_cal
    - raw_moneyflow, raw_stk_factor, raw_index_daily, raw_adj_factor
  - 数据来源：从 SimulatedTuShareClient 导出或从真实数据脱敏
  - README.md 说明数据结构和使用方法
- [ ] ENH-04 契约测试目录
  - 迁移/确认 `tests/contracts/` 目录（R0.5 已创建）
  - 确保 7 组契约测试全部存在：
    - test_data_layer.py（28 字段）
    - test_mss.py（16 字段）
    - test_irs.py（18 字段）
    - test_pas.py（20 字段）
    - test_validation.py（12 字段）
    - test_integration.py（28 字段）
    - test_backtest.py
  - 补齐 IRS/PAS 的直接覆盖（当前仅间接覆盖）
  - 金丝雀测试 `tests/canary/` 目录：使用 canary_10d 数据运行端到端

### 验收标准

1. canary_10d 目录含 10 天 × 8 表 parquet 文件
2. `pytest tests/contracts/ -q` 全部通过
3. `pytest tests/canary/ -q` 端到端通过

---

## CARD-R9.3: 监控模块重建

**工作量**：2 天
**优先级**：P0（当前仅 16 行 NotImplementedError）
**SOS 映射**：E-14

### 交付物

- [ ] `src/monitoring/quality_monitor.py` 完整实现
  - 6 层监控：
    1. 数据层：market_snapshot 字段完整性 + 值域检查
    2. 因子层：MSS 温度 [0,100] + IRS/PAS 评分分布合理性
    3. Validation 层：Gate 状态 + IC/ICIR 趋势
    4. 集成层：final_score 分布 + recommendation 分布
    5. 交易层：持仓数 / 仓位比例 / 风控触发频率
    6. 系统层：DuckDB 大小 / 内存使用 / 运行耗时
  - 9 条关键指标与阈值：
    - data_completeness ≥ 0.95
    - mss_temperature ∈ [0, 100]
    - irs_score_std > 5.0
    - pas_score_std > 5.0
    - gate_fail_ratio < 0.3
    - final_score_mean ∈ [30, 70]
    - max_position_ratio ≤ 0.20
    - industry_concentration_hhi ≤ 0.25
    - system_runtime_seconds ≤ 600
  - P0/P1/P2 三级告警
    - P0：data_completeness < 0.80 或 gate_fail_ratio > 0.5 → 立即通知 + 阻断
    - P1：指标越限 → 通知 + 标记
    - P2：趋势异常 → 仅日志
  - 升级规则：P1 连续 3 天 → 升级为 P0
  - 统一通知路径：控制台 + 日志文件

### 验收标准

1. 6 层监控全部可运行
2. 构造异常数据 → 触发对应级别告警
3. P1 连续 3 天 → 自动升级为 P0

---

## CARD-R9.4: 设计冻结 + L4 产物标准化

**工作量**：1 天
**优先级**：P1
**SOS 映射**：E-09, E-10

### 交付物

- [ ] ENH-08 设计冻结检查
  - 实现 `freeze_check.py`（SHA256 hash 锚点）
  - 创建 `freeze_anchors.json`：所有设计文档的 SHA256 hash
  - CI 中运行：`python freeze_check.py` → 检测设计文档是否被未授权修改
  - 保留现有 `design_traceability_check.py`（两者互补）
- [ ] ENH-07 L4 产物标准化
  - 定义产物目录结构：`artifacts/{module}/{trade_date}/`
  - 每次运行输出：manifest.json（产物清单 + 版本 + 时间戳）
  - 产物类型：parquet（数据）+ markdown（报告）+ json（快照）

### 验收标准

1. `freeze_check.py` 检测到文档修改时报错
2. freeze_anchors.json 覆盖所有 design/ 目录文件
3. 每次运行生成 manifest.json

---

## CARD-R9.5: 调度器 + 全链路重跑

**工作量**：1.5 天
**优先级**：P1
**SOS 映射**：E-12, E-13

### 交付物

- [ ] ENH-11 定时调度器
  - 补齐 `_run_all()` 缺失步骤：Backtest / Trading / Analysis / GUI
  - MSS/IRS/PAS 并行能力（可选，使用 concurrent.futures）
  - `blocked_by_dependency` 失败补偿：上游失败 → 标记下游 blocked
  - 重试策略对齐设计：5 次指数退避 (30s→60s→120s→240s→480s)
  - 4 个调度窗口时段限制（可选）
- [ ] 全链路重跑一致性验证
  - 使用 R1 修复后的数据运行完整链路：
    Data → MSS → IRS → PAS → Validation → Integration → Backtest → Trading → Analysis → GUI
  - 检查每一层输出正确性
  - 输出一致性报告：`artifacts/r9-full-pipeline-report.md`

### 验收标准

1. `_run_all()` 跑完整 10 个步骤
2. 上游失败时下游标记 blocked（不尝试运行）
3. 全链路重跑无异常

---

## CARD-R9.6: 文档收口 + 技术债清偿

**工作量**：1.5 天
**优先级**：P1（收口）
**前置依赖**：CARD-R9.1~R9.5

### 交付物

- [ ] 设计文档最终收口
  - information-flow 文档：全部与重建后代码对齐
  - data-models 文档：全部与重建后表结构对齐
  - api 文档：全部与重建后 OOP 接口对齐
  - algorithm 文档：确认公式与代码 100% 一致
- [ ] 技术债清偿记录
  - 更新 `Governance/record/debts.md`
  - 标记已清偿项（R0-R9 过程中修复的）
  - 标记遗留项（如 MSS baseline parquet、权限系统等）
  - 记录每项的清偿阶段和日期
- [ ] Governance 同步
  - `Governance/record/development-status.md`：标记 R9 完成
  - `Governance/record/reusable-assets.md`：登记所有新建共享模块
  - `AGENTS.md` / `CLAUDE.md` / `WARP.md` / `README.md`：更新路径和流程
- [ ] 最终验证清单
  - 所有模块 `mypy` 通过
  - 所有契约测试通过
  - 全链路重跑通过
  - 设计冻结检查通过
  - 监控模块运行正常
  - 输出最终验收报告：`artifacts/r9-final-acceptance-report.md`

### 验收标准

1. 设计文档与代码零偏差（或已标注为有意偏离 + 原因）
2. 技术债账本更新完毕
3. 最终验收报告 6 项全部通过

---

## R9 阶段验收总览

完成以上 6 张卡后，需满足：

1. **CLI 统一**：`eq run/mss/recommend/backtest/trade/gui` 全部可用
2. **预检完整**：token 验证 + 限流守卫 + 异常分类
3. **监控可用**：6 层监控 + 9 条指标 + 3 级告警
4. **金丝雀**：10 天 × 8 表 parquet + 端到端测试
5. **设计冻结**：SHA256 锚点守卫
6. **全链路闭环**：Data → GUI 10 步全部通过
7. **文档收口**：设计 ↔ 代码零偏差
8. **技术债清偿**：已清偿/遗留项全部登记

**全系统重建完成。**

---

## 全局统计

| 阶段 | 卡数 | 工期 | 文件 |
|------|------|------|------|
| R0 工程基座 | 5 | 3-4天 | R0-foundation-cards.md |
| R1 数据层 | 6 | 5-7天 | R1-data-layer-cards.md |
| R2 MSS | 4 | 4-5天 | R2-mss-cards.md |
| R3 IRS+PAS | 8 | 12-15天 | R3-irs-pas-cards.md |
| R4 Valid+Integ | 7 | 10-12天 | R4-validation-integration-cards.md |
| R5 Backtest | 9 | 12-14天 | R5-backtest-cards.md |
| R6 Trading | 5 | 7-8天 | R6-trading-cards.md |
| R7 Analysis | 5 | 6-8天 | R7-analysis-cards.md |
| R8 GUI | 6 | 8-10天 | R8-gui-cards.md |
| R9 增强+稳定 | 6 | 7-10天 | R9-enhancements-cards.md |

**总计：61 张卡，75-93 工作日。**
