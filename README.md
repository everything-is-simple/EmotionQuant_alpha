# EmotionQuant

EmotionQuant 是面向中国 A 股的情绪驱动量化系统，执行模型为微圈闭环（R0-R9 Rebuild 路线）。

## 当前对齐状态（2026-02-28）

- 核心设计 SoT：`docs/design/**` + `docs/system-overview.md`
- 路线图 SoT：`docs/roadmap.md`（R0-R9）
- R0-R9 执行卡：`docs/cards/`
- Spiral 阶段行动卡已归档：`Governance/archive/archive-spiral-roadmap-v5-20260228/execution-cards/`
- 技术债总表：`Governance/record/debts.md`

## 核心原则（执行口径）

1. 情绪优先，技术指标不得独立触发交易。
2. 本地数据优先，远端仅补采，缺口先落库。
3. 路径/密钥必须通过 `Config.from_env()` 或环境变量注入。
4. A 股规则刚性执行（T+1、涨跌停、交易时段、申万行业）。
5. 每圈必须完成 `run/test/artifact/review/sync` 五件套。

## 关键入口（单一事实源）

- 系统总览：`docs/system-overview.md`
- 模块索引：`docs/module-index.md`
- 主计划：`docs/design/enhancements/eq-improvement-plan-core-frozen.md`
- 命名规范：`docs/naming-conventions.md`
- 命名契约 Schema：`docs/naming-contracts.schema.json`
- 治理规则：`Governance/steering/`
- 执行卡索引：`docs/cards/README.md`

## 数据下载（高速补采）

当前 L1 历史补采主工具：`scripts/data/bulk_download.py`

```bash
# 直接运行（推荐）
python scripts/data/bulk_download.py --start 20080101 --end 20260225 --skip-existing

# PowerShell 入口（支持后台、状态、重试）
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -Start 20080101 -End 20260225 -Background -SkipExisting
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -StatusOnly
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -RunnerStatus
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -StopRunner

# 双 Token 可用性检查 / 通道窗口基准
python scripts/data/check_tushare_dual_tokens.py --env-file .env --channels both
python scripts/data/benchmark_tushare_l1_channels_window.py --env-file .env --start 20250101 --end 20250131 --channels both
```

## 环境与质量门禁

```bash
# 运行时
pip install -r requirements.txt

# 开发依赖
pip install -r requirements-dev.txt

# 测试
pytest -v

# 契约/治理一致性门禁
python -m scripts.quality.local_quality_check --contracts --governance
```

## 目录导航

- `src/`：实现代码
- `tests/`：自动化测试
- `docs/`：设计与规范
- `Governance/`：路线图、执行卡、治理与记录
- `scripts/`：工程脚本（含数据下载、质量检查、工具链初始化）

## 仓库远端

- `origin`: `${REPO_REMOTE_URL}`（见 `.env.example`）
- `backup`: `${REPO_BACKUP_REMOTE_URL}`（见 `.env.example`）

## 许可证

MIT（以仓库 `LICENSE` 为准）
