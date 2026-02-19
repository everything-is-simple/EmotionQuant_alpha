# TuShare 配置总入口（单点）

## 1. 目标

- 主路：第三方 10000 积分试用号（可频繁更换）。
- 兜底：官方 5000 积分号（稳定保底）。
- 要求：所有切换集中在 `.env` 一处完成。

## 2. 推荐配置

```bash
# 主路（试用号）
TUSHARE_PRIMARY_TOKEN=
TUSHARE_PRIMARY_SDK_PROVIDER=tinyshare

# 兜底（官方号）
TUSHARE_FALLBACK_TOKEN=
TUSHARE_FALLBACK_SDK_PROVIDER=tushare

# 全局限流
TUSHARE_RATE_LIMIT_PER_MIN=120
```

兼容旧字段（可选）：

```bash
TUSHARE_TOKEN=
TUSHARE_SDK_PROVIDER=tushare
```

说明：旧字段会被视为主路配置；建议逐步迁移到 `TUSHARE_PRIMARY_*` + `TUSHARE_FALLBACK_*`。

## 3. 代码行为

- 同一 API 请求默认先走主路。
- 主路失败时自动回退兜底。
- 两路都失败时按现有重试机制上报 `FetchError`。

## 4. 关联文档

- [官方 5000 积分兜底号](./tushare-config-5000积分-官方-兜底号.md)
- [第三方 10000 积分试用号](./tushare-config-10000积分-第三方-试用号.md)
- [专题接口索引](./tushare-topic-index.md)

## 5. 安全要求

- 禁止将 token 写入文档、代码或提交历史。
- token 仅允许放入本地 `.env`（或密钥管理器）。
