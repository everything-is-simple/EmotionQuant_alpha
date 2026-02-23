# 跨文档变更联动模板（Spiral）

**用途**：当出现“数据契约 / 风控规则 / 数据边界”变更时，作为本圈联动同步清单，防止总览、治理、设计与 CP 口径漂移。

---

## 1. 变更摘要

- Spiral：`S{N}`
- 变更类型：`data_contract / risk_rule / data_boundary`
- 变更描述（1-3 句）：
- 影响模块：
- 风险等级：`P0 / P1 / P2`

---

## 2. 联动文件清单（必填）

| 文件路径 | 变更点 | 是否完成 |
|---|---|---|
| `docs/system-overview.md` |  | `yes/no` |
| `Governance/steering/TRD.md` |  | `yes/no` |
| `Governance/steering/系统铁律.md`（如涉及） |  | `yes/no` |
| `Governance/steering/CORE-PRINCIPLES.md`（如涉及） |  | `yes/no` |
| `Governance/archive/archive-capability-v8-20260223/CP-*.md`（如涉及） |  | `yes/no` |
| `docs/design/**/algorithm.md` |  | `yes/no` |
| `docs/design/**/data-models.md` |  | `yes/no` |
| `docs/naming-conventions.md`（命名变更时） |  | `yes/no` |

---

## 3. 一致性校验

1. 枚举/阈值/字段名在上下游文档中一致。
2. FAIL/WARN/PASS 或阻断语义在治理与实现文档中一致。
3. 本地数据优先边界未被破坏（远端仅补采）。
4. `run/test/artifact/review/sync` 证据可追溯。

---

## 4. 闭环证据

- run：
- test：
- artifact：
- review：
- sync：

---

## 5. 结论

- 联动状态：`完成 / 未完成`
- 是否允许收口：`yes/no`
- 若 `no`，阻断原因：
