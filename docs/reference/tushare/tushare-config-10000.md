# TuShare 非官方替代配置（tinyshare）

**定位**: 非官方替代接入说明（仅供本地验证与应急）

## 1. 适用场景

- 官方 `tushare` token 不可用，但需要继续验证数据链路
- 需要以最小改动复用现有 `source=tushare` 入口

## 2. 环境变量配置

```bash
TUSHARE_TOKEN=<your_tinyshare_auth_code>
TUSHARE_SDK_PROVIDER=tinyshare
TUSHARE_RATE_LIMIT_PER_MIN=120
```

> 安全要求：授权码只写入 `.env`，禁止写入文档、代码和提交历史。

## 3. 运行验证

```bash
python -m src.pipeline.main run --date 20260213 --source tushare --l1-only
python -m src.pipeline.main run --date 20260213 --source tushare --to-l2
```

## 4. 说明

- 代码侧通过 `TUSHARE_SDK_PROVIDER` 动态选择 `tushare` / `tinyshare`。
- `trade_cal` 响应已做 `cal_date -> trade_date` 归一，兼容现有门禁检查。
