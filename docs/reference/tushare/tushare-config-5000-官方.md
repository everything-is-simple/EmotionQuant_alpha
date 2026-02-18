# TuShare 官方配置（5000 积分口径）

**定位**: 官方 `tushare` SDK 标准接入说明

## 1. 环境变量配置

```bash
TUSHARE_TOKEN=<your_official_tushare_token>
TUSHARE_SDK_PROVIDER=tushare
TUSHARE_RATE_LIMIT_PER_MIN=120
```

## 2. 运行验证

```bash
python -m src.pipeline.main run --date 20260213 --source tushare --l1-only
python -m src.pipeline.main run --date 20260213 --source tushare --to-l2
```

## 3. 注意事项

- Token 仅写入 `.env`，不要出现在文档和代码。
- 主链路默认走本地数据落库，远端仅用于补录与更新。
