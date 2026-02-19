# MSS API 接口

**版本**: v3.2.0（重构版）
**最后更新**: 2026-02-14
**状态**: 设计完成并已落地（Python 模块/CLI；当前仓库无 Web API）

---

## 实现状态（仓库现状）

- 当前仓库已落地 `src/algorithms/mss/engine.py`、`src/algorithms/mss/pipeline.py`、`src/algorithms/mss/probe.py`，并由 `eq mss`/`eq mss-probe` 提供统一入口。
- 本文档为设计规格与实现对照基线，接口演进需与 CP-02 同步更新（历史线性编号 02，仅兼容说明）。

---

## 1. 接口定位

当前仓库不包含 Web 后端。MSS 以 **Python 模块接口/CLI** 形式对外提供能力；
如需 HTTP 服务，由 GUI/服务层另行封装。

---

## 2. 模块接口（Python）

### 2.1 计算器接口

```python
class MssCalculator:
    """MSS 计算器接口"""
    
    def calculate(self, trade_date: str) -> MssPanorama:
        """
        计算指定日期的 MSS 全景数据
        
        Args:
            trade_date: 交易日期 YYYYMMDD
        Returns:
            MssPanorama 对象
        Raises:
            ValueError: 非交易日或输入数据缺失
            DataNotReadyError: 依赖数据未就绪
        """
        pass
    
    def batch_calculate(self, start_date: str, end_date: str) -> List[MssPanorama]:
        """
        批量计算日期范围内的 MSS 数据
        
        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
        Returns:
            MssPanorama 列表（按日期升序）
        """
        pass
    
    def get_latest(self) -> MssPanorama:
        """获取最新一日的 MSS 数据"""
        pass
    
    def get_temperature(self, trade_date: str) -> float:
        """获取指定日期的温度值"""
        pass
    
    def get_cycle(self, trade_date: str) -> str:
        """
        获取指定日期的周期阶段

        Returns:
            str: 周期代码（emergence/fermentation/acceleration/divergence/climax/diffusion/recession/unknown）
                其中 `unknown` 表示历史数据不足以识别周期，为合法降级输出
        """
        pass
    
    def get_position_advice(self, trade_date: str) -> str:
        """获取指定日期的仓位建议"""
        pass

    def get_extreme_direction_bias(self, trade_date: str) -> float:
        """获取指定日期的极端方向偏置（-1~1）"""
        pass
```

### 2.2 数据仓库接口

```python
class MssRepository:
    """MSS 数据仓库接口"""
    
    def save(self, panorama: MssPanorama) -> None:
        """保存单条记录（幂等）"""
        pass
    
    def save_batch(self, panoramas: List[MssPanorama]) -> int:
        """批量保存，返回实际插入/更新条数"""
        pass
    
    def get_by_date(self, trade_date: str) -> Optional[MssPanorama]:
        """按日期查询"""
        pass
    
    def get_by_date_range(self, start_date: str, end_date: str) -> List[MssPanorama]:
        """按日期范围查询"""
        pass
    
    def get_latest_n(self, n: int = 30) -> List[MssPanorama]:
        """获取最近N条记录"""
        pass
```

---

## 3. 错误处理

| 场景 | 行为 | 说明 |
|------|------|------|
| 非交易日 | 抛 `ValueError` | 输入非法，拒绝计算 |
| 必备字段缺失 | 抛 `ValueError` | 不允许“沿用前值”兜底 |
| `stale_days > 3` | 抛 `DataNotReadyError` | 依赖数据未就绪，阻断主流程 |
| `stale_days <= 3` | 允许计算（降级） | 结果可用，但必须打质量标记 |
| 统计参数缺失（mean/std） | 对缺失因子回退 50 分 | 不抛错，记录告警 |
| 趋势输入异常 | 输出 `cycle=unknown` | 属于合法降级，不抛异常 |

强制约束：
- 不允许沿用上一交易日 `temperature/cycle/trend` 作为兜底输出。
- 详细错误码与处理策略见：
  - `docs/design/core-algorithms/mss/mss-algorithm.md`
  - `Governance/Capability/CP-02-mss.md`

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.2.0 | 2026-02-14 | 落地 review-001 修复：增加 `get_extreme_direction_bias()` 读取接口；错误处理改为矩阵化定义，明确 `stale_days` 分层处理与“禁止沿用前值”约束 |
| v3.1.2 | 2026-02-09 | 修复 R27：`get_cycle()` 返回值文档补充 `unknown` 合法降级语义；错误处理补充 `unknown` 与 `DataNotReadyError` 的边界 |
| v3.1.1 | 2026-02-05 | 移除 HTTP 接口示例，改为模块接口定义；与路线图/仓库架构对齐 |
| v3.1.0 | 2026-02-04 | 同步 MSS v3.1.0：补齐验收口径（count→ratio→zscore）；factors 示例补充 final_weight/inverse_score 并与温度公式一致 |
| v3.0.0 | 2026-01-31 | 重构版：统一API风格、添加枚举映射、完善错误处理 |

---

**关联文档**：
- 算法设计：[mss-algorithm.md](./mss-algorithm.md)
- 数据模型：[mss-data-models.md](./mss-data-models.md)
- 信息流：[mss-information-flow.md](./mss-information-flow.md)



