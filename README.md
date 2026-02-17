# EmotionQuant

EmotionQuant 是面向中国 A 股的情绪驱动量化系统，执行模型为 Spiral 闭环（非线性流水线）。

## 当前状态（Truth First）

- 仓库现状：`Skeleton + 文档治理基线`
- 执行口径：已统一为 `Spiral + Capability Pack (CP)`
- 实现入口：从 `S0` 数据最小闭环开始

## 核心原则

1. 情绪优先，单指标不得独立决策。
2. 本地数据优先，远端仅补采。
3. 路径/密钥禁止硬编码。
4. A 股规则刚性执行。
5. 每圈闭环五证据：`run/test/artifact/review/sync`。

## 架构概览（实现口径）

- Data
- Signal（MSS / IRS / PAS）
- Validation（因子+权重 Gate）
- Integration
- Backtest
- Trading
- Analysis
- GUI

入口文档：

- `docs/system-overview.md`
- `docs/module-index.md`
- `docs/naming-conventions.md`
- `docs/naming-contracts.schema.json`
- `docs/naming-contracts-glossary.md`
- `docs/design/`（`docs/design/core-algorithms/` + `docs/design/core-infrastructure/` + `docs/design/enhancements/`）
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`
- `Governance/SpiralRoadmap/VORTEX-EVOLUTION-ROADMAP.md`（实现总路线） + `Governance/SpiralRoadmap/DEPENDENCY-MAP.md`（跨圈依赖与外挂排布）

## 开发模型（Spiral）

- 默认 7 天一圈，单圈仅 1 个主目标。
- 单圈只取 1-3 个 CP Slice。
- 缺任一闭环证据不得收口。
- 默认流程：`Scope -> Build -> Verify -> Sync`。
- 高风险改动才升级 Strict 6A。

关键流程文件：

- `Governance/steering/6A-WORKFLOW.md`
- `Governance/Capability/SPIRAL-TASK-TEMPLATE.md`

## 快速开始

### 1) 环境准备

- Python `>=3.10`
- 建议使用虚拟环境
- TuShare Token（如需拉取数据）

### 2) 安装依赖

```bash
pip install -r requirements.txt
pip install -e ".[dev]"
```

可选依赖：

```bash
pip install -e ".[backtest]"
pip install -e ".[visualization]"
```

### 3) 基础检查

```bash
pytest -v
python -m scripts.quality.local_quality_check --contracts --governance
```

说明：当前仓库仍在实现早期，需按 S0-S6 逐圈收口。

### 4) 开发工具链初始化（MCP + Skills + Hooks）

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup/bootstrap_dev_tooling.ps1
```

如只需单项配置：
- MCP：`powershell -ExecutionPolicy Bypass -File scripts/setup/configure_mcp.ps1`
- Hooks：`powershell -ExecutionPolicy Bypass -File scripts/setup/configure_git_hooks.ps1`
- Skills 检查：`powershell -ExecutionPolicy Bypass -File scripts/setup/check_skills.ps1`
- MCP 默认写入项目级 `.tmp/codex-home`；如需自定义位置可加 `-CodexHome <path>`

详情见：`docs/reference/dev-tooling-setup.md`

## 目录导航

- `docs/`：系统设计与规范
- `Governance/Capability/`：螺旋路线与能力包
- `Governance/SpiralRoadmap/`：实现路线与跨圈依赖桥梁
- `Governance/steering/`：铁律、原则、工作流
- `Governance/record/`：开发状态、技术债、复用资产
- `.reports/`：批判报告与审视记录

## 关键文档入口

- `docs/system-overview.md`
- `docs/module-index.md`
- `docs/naming-conventions.md`
- `docs/naming-contracts.schema.json`
- `docs/naming-contracts-glossary.md`
- `Governance/steering/系统铁律.md`
- `Governance/steering/CORE-PRINCIPLES.md`
- `Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md`
- `Governance/steering/CROSS-DOC-CHANGE-LINKAGE-TEMPLATE.md`

## 仓库地址

- `origin`: `${REPO_REMOTE_URL}`（定义见 `.env.example`）
- `backup`: `${REPO_BACKUP_REMOTE_URL}`（定义见 `.env.example`）

## 许可证

MIT（以仓库实际 LICENSE 文件为准）。



