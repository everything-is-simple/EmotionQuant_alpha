# 归档说明：Spiral Roadmap 体系 (v5)

**归档日期**: 2026-02-28
**归档原因**: 被 R0-R9 重建路线图体系全面取代

---

## 被取代的内容

| 旧文件/目录 | 被什么取代 | 原因 |
|---|---|---|
| `planA/VORTEX-EVOLUTION-ROADMAP.md` | `docs/roadmap.md` (R0-R9) | 旧路线图基于 Spiral 渐进模型，含大量错误和不一致；新路线图基于 SOS 审计全覆盖 183 项偏差重新设计 |
| `planA/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md` | `docs/cards/R0-*.md` ~ `docs/cards/R2-*.md` | 旧的分阶段执行路线被更精确的执行卡替代 |
| `planA/SPIRAL-S3A-S4B-EXECUTABLE-ROADMAP.md` | `docs/cards/R3-*.md` ~ `docs/cards/R4-*.md` | 同上 |
| `planA/SPIRAL-S5-S7A-EXECUTABLE-ROADMAP.md` | `docs/cards/R5-*.md` ~ `docs/cards/R9-*.md` | 同上 |
| `planB/` | 无（从未执行） | Plan B 备选方案从未被采纳执行 |
| `execution-cards/S0A~S7AR` | `docs/cards/R0~R9-*-cards.md` | 旧执行卡30+张，含重复和错误；新执行卡61张，基于 SOS 审计精确对应 |
| `EXECUTION-CARDS-INDEX.md` | `docs/cards/README.md` | 新索引与新卡体系匹配 |
| `SPIRAL-STAGE-TEMPLATES.md` | 执行卡内嵌标准格式 | 模板内容已融入新卡片格式 |

## 核心淘汰原因

1. **SOS 审计暴露 183 项偏差**：旧 Spiral 路线图未能覆盖全部问题，存在系统性遗漏
2. **文档-代码不一致**：旧执行卡和路线图与实际代码状态存在大量偏差
3. **结构臃肿**：planA/planB 双线、30+ 执行卡分散管理，难以维护和追踪
4. **新体系优势**：R0-R9 路线图 + 61 张执行卡完整覆盖所有 SOS 偏差，采用统一标准格式

## 新的权威文档

- **路线图**: `docs/roadmap.md`
- **执行卡**: `docs/cards/` (10 个文件，61 张卡)
- **SOS 审计**: `docs/sos/` (11 个模块)
- **卡索引**: `docs/cards/README.md`

---

> ⚠️ 本目录内容仅供历史参考，不得作为执行依据。
