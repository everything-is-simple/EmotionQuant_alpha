# TuShare 配置索引

## 配置入口

- 官方口径（5000 积分）: `tushare-config-5000-官方.md`
- 非官方替代（tinyshare）: `tushare-config-10000.md`

## 当前仓库实现

- 统一通过 `.env` 注入 `TUSHARE_TOKEN`
- 通过 `TUSHARE_SDK_PROVIDER` 切换 SDK:
  - `tushare`（官方）
  - `tinyshare`（非官方替代）

## 安全约束

- 禁止在文档、代码、提交记录中出现明文 Token/授权码。
