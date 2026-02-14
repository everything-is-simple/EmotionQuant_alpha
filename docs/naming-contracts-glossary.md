# 命名与契约术语字典

**版本**: v1.0.0  
**最后更新**: 2026-02-14  
**状态**: 生效

---

| 术语 | 权威定义 | 受影响模块 |
|---|---|---|
| `MssCycle` | `emergence/fermentation/acceleration/divergence/climax/diffusion/recession/unknown` | MSS / Integration / GUI |
| `Trend` | `up/down/sideways`（禁用 `flat`） | MSS / Integration |
| `PasDirection` | `bullish/bearish/neutral` | PAS / Integration |
| `RotationStatus` | `IN/OUT/HOLD` | IRS / Integration |
| `ValidationGate` | `PASS/WARN/FAIL` | Validation / Integration / Trading / Backtest |
| `risk_reward_ratio` | 执行门槛 `>=1.0`，`rr_ratio` 禁用 | PAS / Trading / Backtest |
| `stock_code` / `ts_code` | L1 用 `ts_code`，L2+ 用 `stock_code` | Data Layer / 全链路 |
| `contract_version` | 当前 `nc-v1`，执行前必须做兼容校验 | Integration / Trading / Backtest |

---

## 变更流程

1. 先更新 `docs/naming-contracts.schema.json`。
2. 再更新 `docs/naming-conventions.md` 与受影响模块文档。
3. 执行 `python -m scripts.quality.local_quality_check --contracts`。
4. 使用 `Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md` 记录联动清单。
