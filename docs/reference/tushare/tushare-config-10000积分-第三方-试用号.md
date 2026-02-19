# TuShare 第三方 10000 积分试用号（主路通道）

## 1. 定位

- 角色：主路通道（primary）。
- 用途：优先承载系统数据采集与高积分接口试验。
- 特点：账号可能频繁更换，因此必须集中在 `.env` 单点配置。

## 2. 配置入口（单点）

```bash
TUSHARE_PRIMARY_TOKEN=<trial_token>
TUSHARE_PRIMARY_SDK_PROVIDER=tinyshare
# 可选：第三方网关地址（若服务方提供）
TUSHARE_PRIMARY_HTTP_URL=http://106.54.191.157:5000
TUSHARE_RATE_LIMIT_PER_MIN=120
```

> 主路变更时，只改 `.env` 这一处即可生效。

## 3. 与官方 5000 号组合策略

- 主路：`TUSHARE_PRIMARY_*`（建议第三方 10000 试用号）。
- 兜底：`TUSHARE_FALLBACK_*`（建议官方 5000 号）。
- 代码策略：同一请求先走主路；主路失败自动回退兜底。

## 4. 当前 L1 采集范围（S0/S3a）

- `daily` -> `raw_daily`
- `daily_basic` -> `raw_daily_basic`
- `limit_list_d` -> `raw_limit_list`
- `index_daily` -> `raw_index_daily`
- `index_member` -> `raw_index_member`
- `index_classify` -> `raw_index_classify`
- `stock_basic` -> `raw_stock_basic`
- `trade_cal` -> `raw_trade_cal`

## 5. PowerShell 示例（主路+兜底）

```powershell
$env:DATA_PATH="G:/EmotionQuant_data"
$env:DUCKDB_DIR="G:/EmotionQuant_data/duckdb"
$env:PARQUET_PATH="G:/EmotionQuant_data/parquet"

$env:TUSHARE_PRIMARY_TOKEN="<trial_token>"
$env:TUSHARE_PRIMARY_SDK_PROVIDER="tinyshare"
$env:TUSHARE_PRIMARY_HTTP_URL="http://106.54.191.157:5000"
$env:TUSHARE_FALLBACK_TOKEN="<official_5000_token>"
$env:TUSHARE_FALLBACK_SDK_PROVIDER="tushare"
$env:TUSHARE_RATE_LIMIT_PER_MIN="120"

python -m src.pipeline.main fetch-batch --start 20200101 --end 20260218 --batch-size 365 --workers 3
python -m src.pipeline.main fetch-status
python -m src.pipeline.main fetch-retry
```

## 6. 安全要求

- 不在文档中记录任何明文 token。
- 仅在本地 `.env`（或密钥管理器）保存凭据。

## 7. 关联文档

- [总配置入口](./tushare-config.md)
- [官方 5000 积分兜底号](./tushare-config-5000积分-官方-兜底号.md)
