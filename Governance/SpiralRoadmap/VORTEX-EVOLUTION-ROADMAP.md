# EmotionQuant VORTEX 演进路线图（执行主视图）

**状态**: Active  
**更新时间**: 2026-02-14  
**定位**: SpiralRoadmap 总览入口（实战执行版）。

---

## 1. 口径说明

1. 该文档给出 Spiral 进度看板与顺序约束。
2. 详细执行合同请看：
   - `Governance/SpiralRoadmap/SPIRAL-S0-S2-EXECUTABLE-ROADMAP.md`
   - `Governance/SpiralRoadmap/SPIRAL-PRODUCTION-ROUTES.md`
3. 上位 SoT 仍为：`Governance/Capability/SPIRAL-CP-OVERVIEW.md`。

---

## 2. 前置里程碑（已完成）

| 里程碑 | 说明 | 完成时间 | 状态 |
|---|---|---|---|
| R0 设计闭环 | `.reports/design-review-sandbox` 12 份评审与修订完成；命名契约 Schema/术语/模板落地 | 2026-02-14 | completed |
| R0 质量门禁 | 本地 `--contracts --governance` 与 CI `quality-gates` 门禁落地 | 2026-02-14 | completed |

---

## 3. Spiral 进度看板（默认路线 A）

| Spiral | 名称 | 目标 | 预算 | 状态 |
|---|---|---|---:|---|
| S0a | 入口与配置 | 统一入口、配置注入 | 2d | planned |
| S0b | L1 入库 | 原始采集与入库 | 3d | planned |
| S0c | L2 快照 | 快照与失败链路 | 3d | planned |
| S1a | MSS 评分 | 温度/周期可复现 | 3d | planned |
| S1b | MSS 消费 | 探针消费与结论 | 2d | planned |
| S2a | IRS+PAS+Validation | 多算法与门禁闭环 | 4d | planned |
| S2b | 集成推荐 | TopN 推荐可追溯 | 3d | planned |
| S2r | 修复子圈 | FAIL 修复重验 | 1-2d | conditional |
| S3a | 数据采集增强 | ENH-10 分批+断点续传+多线程 | 2.5d | planned |
| S3 | 回测闭环 | Qlib + 本地口径对照 | 4d | planned |
| S4 | 纸上交易 | 订单/持仓/风控可重放 | 4d | planned |
| S5 | 展示闭环 | GUI + 日报导出 | 3d | planned |
| S6 | 稳定化 | 全链路重跑一致 | 3d | planned |
| S7a | 自动调度 | ENH-11 日更与开机自启 | 1.5d | planned |

---

## 4. 关键顺序约束

1. S2b FAIL 时只能进入 S2r，禁止跳过。
2. S3a 必须在 S3 前执行（默认路线），否则 S3 数据准备效率不可控。
3. S7a 必须在 S6 后执行，避免运维能力先于稳定化落地。
4. S2->S3 迁移前必须通过 `python -m scripts.quality.local_quality_check --contracts --governance`。

---

## 5. 风险矩阵（核心）

| 风险 | 级别 | 触发条件 | 应对 |
|---|---|---|---|
| 推荐链路缺 A 股规则门禁 | P0 | T+1/涨跌停/交易时段字段缺失 | 阻断收口，进入修复圈 |
| 数据拉取耗时过长 | P1 | 历史数据下载持续失败或过慢 | 启动 S3a，启用 ENH-10 |
| 自动调度误触发重复下载 | P1 | 非交易日或重复任务未去重 | 启用交易日判断+幂等校验 |
| 文档与执行漂移 | P1 | 路线文档与实际圈序不一致 | 强制同步 5 文件并记录 debt；执行 `--contracts --governance` 一致性检查 |

---

## 6. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.1 | 2026-02-14 | 新增 R0 前置里程碑（设计闭环+质量门禁）；关键顺序约束补充 S2->S3 契约门禁；风险矩阵补充一致性检查措施 |
| v1.0 | 2026-02-13 | 重建执行主视图；纳入 S3a/ENH-10 与 S7a/ENH-11 |
