# Enhancements 模块 — 修复方案

> 原则: AD-01 设计为权威（合理代码偏差通过修订设计认可）

---

## 1. 前置裁决点

### D-1 Qlib 路径裁决（阻塞 E-11）

AD-03 裁决 Qlib 为唯一回测引擎，但代码中零 Qlib 代码。需在 R0 阶段裁决:

- **选项 A**: 实现 `src/adapters/qlib_adapter.py`（to_qlib_signal + from_qlib_result），
  保留本地引擎作为 fallback/快速验证。工程量大。
- **选项 B**: 修订 AD-03，本地向量化引擎为主引擎，Qlib 标记为远期增强。
  需更新路线图所有 Qlib 引用。

---

## 2. 分批修复任务

### 第一批：P0 致命

#### FIX-01 Qlib 适配层或 AD-03 修订 (E-11)

取决于 D-1 裁决。若选项 A:
- 创建 `src/adapters/qlib_adapter.py`
- 实现 `to_qlib_signal(integrated_recommendation) → Qlib Signal DataFrame`
- 实现 `from_qlib_result(qlib_backtest_result) → 标准格式`
- 在 `src/backtest/pipeline.py` 中增加 `--engine qlib` 路径

若选项 B:
- 修订 AD-03
- 更新路线图 CARD-R3/R4 中 Qlib 相关描述
- 设计文档 ENH-09 标记为"远期增强"

#### FIX-02 监控告警模块实现 (E-14)

重建 `src/monitoring/quality_monitor.py`:
- 6 层监控接口（数据/因子/Validation/集成/交易/系统）
- P0/P1/P2 告警分级
- 升级规则（P1 连续 3 次 → P0，P2 连续 10 次 → P1）
- 整合散落的监控能力（quality_gate, validation gate, scheduler log）
- 通知路径: 至少控制台 + 日志文件

#### FIX-03 SHA256 冻结检查 (E-10)

新建 `scripts/quality/freeze_check.py`:
- 对核心设计文件计算 SHA256 hash
- 与 `freeze_anchors.json` 基线比对
- 变化文件标记为需审查

保留现有 `design_traceability_check.py` 作为互补功能。
**注**: 建议重建完成后再锚定基线，重建期间此检查暂不阻断。

#### FIX-04 validate_token() 预检 (E-03)

在 `TuShareFetcher.__init__()` 中增加:
```python
def _validate_token(self):
    """轻量 trade_cal 请求验证 token 有效性"""
    try:
        self.api.trade_cal(exchange='SSE', start_date='20260101', end_date='20260101')
    except Exception as e:
        raise FetchError(f"Token 验证失败: {e}") from e
```

#### FIX-05 金丝雀 parquet 数据包 (E-07)

从 `SimulatedTuShareClient` 导出固化 parquet:
- 创建 `tests/fixtures/canary_10d/` 目录
- 生成 10 天 × 8 表的 parquet 文件
- 实现 `--source mock` 从文件读取路径
- 保留 `SimulatedTuShareClient` 作为第二离线方案

---

### 第二批：P1 重要

#### FIX-06 重试策略统一 (E-04, E-13)

统一为指数退避:
- `fetcher.py`: 重试循环增加 `time.sleep(min(30 * 2**n, 480))`
- `scheduler.py`: `MAX_RETRY_COUNT` 改为 5，重试策略改为指数退避

#### FIX-07 error_manifest 统一 (E-06)

抽取公共函数 `src/pipeline/error_manifest.py`:
- 统一格式: 增加 `error_level`(P0/P1/P2)、`timestamp`、`step` 字段
- 各模块改为调用公共函数
- 保留 per-module artifacts 路径（更实用，修订设计认可）

#### FIX-08 C 组等权持有 (E-09)

`src/analysis/benchmark_comparison.py`:
- 新增 `generate_buyhold_signals()` — 等权买入持有策略
- `BenchmarkComparisonResult` 增加 `buyhold_result` 字段
- 技术基线改回 D 组

#### FIX-09 DAG 编排完善 (E-12)

`src/pipeline/main.py` `_run_all()`:
- 补齐 Backtest → Trading → Analysis → GUI 步骤
- MSS/IRS/PAS 并行（ThreadPoolExecutor）
- `blocked_by_dependency` 失败补偿
- 数据就绪检查点超时机制

#### FIX-10 异常类补齐 (E-05)

在 `src/data/` 下补齐 `RateLimitError` 和 `ConnectionError` 子类，
`FetchError` 作为基类保留。

---

### 第三批：P2 规范性

#### FIX-11 目录结构同步 (E-15)

修订设计文档:
- `src/adapters/` → `src/data/adapters/`
- `tests/contracts/` → `tests/unit/`
- `tests/canary/` → `tests/fixtures/canary/`

#### FIX-12 设计文档回写

- ENH-01: CLI 框架 argparse + 完整 19 个子命令
- ENH-03: per-module artifacts 路径
- ENH-08: 补充 DESIGN_TRACE 溯源作为扩展能力
- `eq recommend` 补充 `--mode` 必填参数
- `eq run-all` 确认 `--date` vs `--start/--end` 差异

---

## 3. 依赖关系

```
D-1 (Qlib 裁决) → FIX-01 (适配层或 AD-03 修订)

FIX-02 (监控) → FIX-07 (error_manifest 统一，监控需读取 error_level)

FIX-05 (金丝雀 parquet) → 独立
FIX-04 (validate_token) → 独立
FIX-06 (重试) → 独立
FIX-08 (C 组) → 独立
FIX-09 (DAG) → FIX-02 (需监控来检测步骤失败)
```

**关键路径**: D-1 裁决 → FIX-01 是最大不确定性。其余项均可并行推进。
