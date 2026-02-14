# 命名/契约变更模板（Naming Contracts）

**用途**：用于记录阈值、枚举、字段边界变更，防止跨模块漂移。

---

## 1. 变更信息

- Spiral：`S{N}`
- 变更类型：`enum / threshold / field / boundary`
- 变更摘要：
- 风险等级：`P0 / P1 / P2`

---

## 2. Schema 变更

- 文件：`docs/naming-contracts.schema.json`
- 变更项：
  - [ ] 枚举更新
  - [ ] 阈值更新
  - [ ] 字段边界更新
- 变更前后对照：

---

## 3. 联动文档清单

| 文件路径 | 需同步内容 | 是否完成 |
|---|---|---|
| `docs/naming-conventions.md` | 规范正文与边界示例 | `yes/no` |
| `docs/naming-contracts-glossary.md` | 术语映射与影响模块 | `yes/no` |
| `docs/design/core-algorithms/*` | 阈值/枚举契约 | `yes/no` |
| `docs/design/core-infrastructure/*` | 执行边界与过滤规则 | `yes/no` |
| `scripts/quality/naming_contracts_check.py` | 自动检查规则 | `yes/no` |
| `tests/unit/scripts/test_naming_contracts_check.py` | 回归测试 | `yes/no` |

---

## 4. 兼容性与阻断策略

- `contract_version` 是否变化：`yes/no`
- 若变化，兼容策略：
  - [ ] Integration 前置检查
  - [ ] Trading 前置检查
  - [ ] Backtest 前置检查
- 不兼容处理：`拒绝执行 + 提示迁移`

---

## 5. 闭环证据

- run：
- test：
- artifact：
- review：
- sync：
