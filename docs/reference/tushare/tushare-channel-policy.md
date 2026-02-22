# TuShare 通道策略（主备口径）

**版本**: v1.0.0  
**最后更新**: 2026-02-22  
**适用范围**: Data Layer L1 八类原始接口采集

---

## 1. 当前执行口径（已实现）

1. 主通道：10000 积分网关号（`TUSHARE_PRIMARY_*`）。
2. 兜底通道：5000 积分官方号（`TUSHARE_FALLBACK_*`）。
3. 切换策略：主通道调用失败时，自动切换到兜底通道。
4. 当前代码仅实现双 TuShare 通道；AKShare/BaoStock 仅为路线图预留底牌。

---

## 2. 环境变量约定

```dotenv
# 主通道：10000 网关
TUSHARE_PRIMARY_TOKEN=
TUSHARE_PRIMARY_SDK_PROVIDER=tushare
TUSHARE_PRIMARY_HTTP_URL=http://106.54.191.157:5000

# 兜底通道：5000 官方
TUSHARE_FALLBACK_TOKEN=
TUSHARE_FALLBACK_SDK_PROVIDER=tushare
TUSHARE_FALLBACK_HTTP_URL=

# 限速策略
TUSHARE_RATE_LIMIT_PER_MIN=120
TUSHARE_PRIMARY_RATE_LIMIT_PER_MIN=0
TUSHARE_FALLBACK_RATE_LIMIT_PER_MIN=0
```

说明：

1. `TUSHARE_PRIMARY_RATE_LIMIT_PER_MIN=0` 表示继承全局限速。
2. `TUSHARE_FALLBACK_RATE_LIMIT_PER_MIN=0` 表示继承全局限速。
3. 需要差异化限速时，分别给主/兜底通道设置非 0 值。

---

## 3. L1 八类接口（统一口径）

`daily / daily_basic / limit_list_d / index_daily / index_member / index_classify / stock_basic / trade_cal`

---

## 4. 验证命令

```powershell
# 双通道一键可用性验证（推荐，显式读取 .env，避免 shell 未导入环境变量时误判）
python scripts/data/check_tushare_dual_tokens.py --env-file .env --channels both

# 主通道可用性
python scripts/data/check_tushare_l1_token.py --token-env TUSHARE_PRIMARY_TOKEN --http-url http://106.54.191.157:5000

# 兜底通道可用性
python scripts/data/check_tushare_l1_token.py --token-env TUSHARE_FALLBACK_TOKEN

# 吞吐压测（主通道）
python scripts/data/benchmark_tushare_l1_rate.py --token-env TUSHARE_PRIMARY_TOKEN --http-url http://106.54.191.157:5000 --api daily --calls 500 --workers 50

# 吞吐压测（兜底通道）
python scripts/data/benchmark_tushare_l1_rate.py --token-env TUSHARE_FALLBACK_TOKEN --api daily --calls 500 --workers 50
```

补充说明（2026-02-22）：

1. `check_tushare_l1_token.py --token-env ...` 只读取当前进程环境变量，不会主动加载 `.env`。
2. 如果 shell 会话没有先导入 `.env`，脚本会按既有逻辑回退到 docs token 文件，可能造成“误判 fallback key 不可用”。
3. 因此主流程统一使用 `check_tushare_dual_tokens.py --env-file .env` 作为双 key 基线校验命令。

---

## 5. 未来预留（未实装）

1. AKShare 最终底牌适配。
2. BaoStock 最终底牌适配。
3. 多源统一映射与切源审计报告（`source_failover_report.md`）。
