# TuShare 官方 5000 积分号（兜底通道）

## 1. 定位

- 角色：系统数据采集兜底通道（fallback）。
- 用途：当第三方 10000 积分试用号主路不可用或波动时，保障 L1 采集可持续运行。

## 2. 配置入口（单点）

统一在 `.env` 配置，不在代码或文档中保存明文 token：

```bash
TUSHARE_FALLBACK_TOKEN=<official_5000_token>
TUSHARE_FALLBACK_SDK_PROVIDER=tushare
```

## 3. 使用边界

- 官方号优先用于系统刚需链路（S0/S3a L1 拉取）。
- 高积分专题或试验性接口优先放在主路试用号，官方号负责兜底。

## 4. 安全要求

- 禁止在文档、代码、Issue、提交历史中写入明文 token。
- token 仅允许放入本地 `.env`（或等价密钥管理器）。

## 5. 关联文档

- [总配置入口](./tushare-config.md)
- [10000 积分第三方试用号](./tushare-config-10000积分-第三方-试用号.md)
