# ARCH-DECISION-001: Pipeline vs OOP 架构决策

**日期**: 2026-02-26
**状态**: 已决策（执行选项 B）
**关联债务**: TD-ARCH-001

---

## 1. 背景

独立审计（Spiral 1+2+3 路线图质量验证）发现：

- 6 份 `*-api.md` 设计文档定义了 OOP 接口（Calculator + Repository 类），但所有模块代码均采用 **过程式 Pipeline + DuckDB 直写** 模式。
- MSS Calculator 接口匹配度 1/7，IRS Repository 接口匹配度 1/6，其余模块类似。
- 此偏差贯穿 MSS/IRS/PAS/Validation/Integration/Trading/Analysis 全部核心模块。

---

## 2. 两个选项

### 选项 A：按设计改代码（OOP 重构）

- 为每个模块引入 Calculator/Repository 类，将 pipeline 函数拆分为方法
- 引入依赖注入容器，Repository 统一抽象 DuckDB 读写
- 优势：可测试性提升、接口可替换、设计-代码一致
- 风险：工作量大（估计 3-5 天），可能引入回归，当前 Pipeline 模式已稳定运行
- 适合时机：S6+ 有 Repository 复用需求时

### 选项 B：按代码改设计（文档对齐 Pipeline）✅ 已选

- 更新 6 份 `*-api.md`，使其反映真实的 Pipeline 函数入口
- Calculator/Repository 接口保留为"未来扩展口径"附录
- 优势：工作量小（1-2 天）、零代码风险、消除设计-代码认知失调
- 风险：推迟 OOP 重构，但当前 Spiral 阶段无强需求

---

## 3. 决策理由

1. **当前 Pipeline 模式功能完整**：7 个模块的 Pipeline 函数均已通过合同测试、产出可复现
2. **单开发者项目**：OOP 带来的可替换性/多态性目前 ROI 低
3. **文档服务实现（铁律 7）**：优先消除认知偏差，不为重构而重构
4. **TD-DA-001 试点已完成**：MSS+IRS 的 Calculator/Repository 薄封装已落地，证明 OOP 迁移可行但非紧急

---

## 4. 执行计划

- **Step 1**（本次）：更新 6 份 api.md + 登记 TD-ARCH-001
- **Step 2**（后续）：修复 Spiral 2 业务缺口（S3b 归因、S3e 因子验证）
- **Step 3**（后续）：升级 Spiral 3 执行卡精度

---

## 5. 选项 A 存档（供未来参考）

若未来需要执行选项 A，推荐路径：

1. 为每个模块创建 `calculator.py` + `repository.py`
2. Calculator 封装业务逻辑，Repository 封装 DuckDB 读写
3. Pipeline 函数退化为 Calculator + Repository 的编排胶水
4. 引入 `Protocol` 定义接口约束，允许 mock 测试
5. 估计工作量：3-5 天（含测试迁移）
6. 前置条件：有多个消费方需要不同的 Repository 实现（如内存/文件/远端）

```
# 目标结构示例（以 MSS 为例）
src/algorithms/mss/
├── calculator.py      # MssCalculator: 业务逻辑
├── repository.py      # MssRepository: DuckDB 读写
├── engine.py          # 核心计算（已有）
├── pipeline.py        # 编排胶水（已有，退化为调用 Calculator）
└── probe.py           # 探针（已有）
```

---

## 变更记录

| 日期 | 变更内容 |
|------|----------|
| 2026-02-26 | 初始创建 |
