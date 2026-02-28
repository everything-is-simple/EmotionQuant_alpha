# CLI Contract（S0a）

**合同版本**: nc-v1  
**生效日期**: 2026-02-15  
**来源微圈**: S0a

## 1. 入口命令

- 统一入口: `eq`
- 临时模块入口: `python -m src.pipeline.main`

## 2. 必备参数契约

- 全局参数:
  - `--env-file` 指定环境文件
  - `--print-config` 输出生效配置快照
- 子命令:
  - `run --date YYYYMMDD [--source tushare] [--dry-run] [--l1-only] [--to-l2]`
  - `version`

## 3. 语义约束

- 配置读取必须走 `Config.from_env()`。
- `--dry-run` 不允许触发业务写入。
- 参数缺失或非法时必须返回非零退出码。

## 4. 回归入口

- `tests/unit/pipeline/test_cli_entrypoint.py`
