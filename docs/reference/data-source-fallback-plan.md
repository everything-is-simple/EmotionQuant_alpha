# 数据源兜底方案

**版本**: v1.0  
**更新时间**: 2026-02-19  
**状态**: 设计完成，待实现

---

## 1. 方案概述

### 1.1 设计目标

建立三层数据源兜底机制，确保在 TuShare 不可用时系统仍能正常采集数据。

### 1.2 三层架构

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: TuShare (主数据源)                              │
│ - 5000积分官方接口                                       │
│ - 数据质量最高，字段最全                                  │
└─────────────────────────────────────────────────────────┘
                          ↓ (token过期/限流)
┌─────────────────────────────────────────────────────────┐
│ Layer 2: AKShare (第一兜底)                              │
│ - 开源免费，无需token                                    │
│ - 东方财富网数据源                                       │
└─────────────────────────────────────────────────────────┘
                          ↓ (接口失败/数据缺失)
┌─────────────────────────────────────────────────────────┐
│ Layer 3: BaoStock + AData (第二兜底)                     │
│ - BaoStock: 证券宝数据                                   │
│ - AData: 多源聚合                                        │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 八个L1接口映射

### 2.1 TuShare → AKShare 映射

| L1接口 | TuShare | AKShare | 字段映射 | 状态 |
|--------|---------|---------|----------|------|
| daily | `pro.daily()` | `ak.stock_zh_a_hist()` | ts_code→symbol, trade_date→日期 | ✅ 可用 |
| daily_basic | `pro.daily_basic()` | `ak.stock_zh_a_hist()` + 计算 | 需补充换手率/市值 | ⚠️ 部分 |
| limit_list_d | `pro.limit_list_d()` | `ak.stock_zt_pool_em()` | 涨跌停池 | ⚠️ 需验证 |
| index_daily | `pro.index_daily()` | `ak.index_zh_a_hist()` | 指数代码映射 | ✅ 可用 |
| index_member | `pro.index_member()` | `ak.stock_board_industry_cons_em()` | 行业成分 | ✅ 可用 |
| index_classify | `pro.index_classify()` | `ak.stock_board_industry_name_em()` | 行业分类 | ✅ 可用 |
| stock_basic | `pro.stock_basic()` | `ak.stock_info_a_code_name()` | 股票列表 | ✅ 可用 |
| trade_cal | `pro.trade_cal()` | `ak.tool_trade_date_hist_sina()` | 交易日历 | ✅ 可用 |

### 2.2 TuShare → BaoStock 映射

| L1接口 | TuShare | BaoStock | 字段映射 | 状态 |
|--------|---------|----------|----------|------|
| daily | `pro.daily()` | `bs.query_history_k_data_plus()` | 日线数据 | ✅ 可用 |
| daily_basic | `pro.daily_basic()` | `bs.query_history_k_data_plus()` | 换手率/市值 | ✅ 可用 |
| limit_list_d | `pro.limit_list_d()` | 需自行计算 | 涨跌停判定 | ⚠️ 需实现 |
| index_daily | `pro.index_daily()` | `bs.query_history_k_data_plus()` | 指数数据 | ✅ 可用 |
| index_member | `pro.index_member()` | `bs.query_sz50_stocks()` 等 | 成分股 | ⚠️ 部分 |
| index_classify | `pro.index_classify()` | `bs.query_stock_industry()` | 行业分类 | ✅ 可用 |
| stock_basic | `pro.stock_basic()` | `bs.query_stock_basic()` | 股票列表 | ✅ 可用 |
| trade_cal | `pro.trade_cal()` | `bs.query_trade_dates()` | 交易日历 | ✅ 可用 |

### 2.3 AData 补充

| 功能 | AData接口 | 说明 |
|------|-----------|------|
| 多源聚合 | `adata.stock.market.get_market()` | 聚合多个数据源 |
| 实时行情 | `adata.stock.market.get_market_realtime()` | 实时数据 |
| 财务数据 | `adata.stock.info.get_financial()` | 财务指标 |

---

## 3. 实现策略

### 3.1 数据源抽象层

```python
class DataSourceAdapter:
    """数据源适配器基类"""
    
    def fetch_daily(self, trade_date: str) -> pd.DataFrame:
        raise NotImplementedError
    
    def fetch_daily_basic(self, trade_date: str) -> pd.DataFrame:
        raise NotImplementedError
    
    # ... 其他接口

class TuShareAdapter(DataSourceAdapter):
    """TuShare适配器"""
    pass

class AKShareAdapter(DataSourceAdapter):
    """AKShare适配器"""
    pass

class BaoStockAdapter(DataSourceAdapter):
    """BaoStock适配器"""
    pass
```

### 3.2 自动降级策略

```python
class DataSourceManager:
    """数据源管理器，自动降级"""
    
    def __init__(self):
        self.sources = [
            TuShareAdapter(),    # Layer 1
            AKShareAdapter(),    # Layer 2
            BaoStockAdapter(),   # Layer 3
        ]
    
    def fetch_with_fallback(self, method: str, **kwargs):
        """带降级的数据获取"""
        for source in self.sources:
            try:
                result = getattr(source, method)(**kwargs)
                if result is not None and len(result) > 0:
                    return result, source.__class__.__name__
            except Exception as e:
                logger.warning(f"{source.__class__.__name__} failed: {e}")
                continue
        
        raise DataSourceError("All data sources failed")
```

### 3.3 字段映射与标准化

```python
class FieldMapper:
    """字段映射器"""
    
    DAILY_MAPPING = {
        'tushare': {
            'ts_code': 'stock_code',
            'trade_date': 'trade_date',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'vol': 'volume',
            'amount': 'amount',
        },
        'akshare': {
            '代码': 'stock_code',
            '日期': 'trade_date',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume',
            '成交额': 'amount',
        },
        'baostock': {
            'code': 'stock_code',
            'date': 'trade_date',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'amount': 'amount',
        }
    }
    
    @staticmethod
    def normalize(df: pd.DataFrame, source: str, data_type: str) -> pd.DataFrame:
        """标准化字段名"""
        mapping = getattr(FieldMapper, f"{data_type.upper()}_MAPPING")[source]
        return df.rename(columns=mapping)
```

---

## 4. 关键问题与解决方案

### 4.1 涨跌停数据

**问题**：
- TuShare: `limit_list_d` 直接提供
- AKShare: `stock_zt_pool_em` 返回空
- BaoStock: 无直接接口

**解决方案**：
```python
def calculate_limit_status(df: pd.DataFrame, board_type: str) -> pd.DataFrame:
    """计算涨跌停状态"""
    # 板块阈值
    thresholds = {
        'main': 0.10,      # 主板
        'gem': 0.20,       # 创业板
        'star': 0.20,      # 科创板
        'st': 0.05,        # ST
    }
    
    threshold = thresholds.get(board_type, 0.10)
    
    # 判定逻辑
    df['is_limit_up'] = (
        (df['close'] >= df['pre_close'] * (1 + threshold - 0.001)) &
        (df['high'] == df['close'])
    )
    
    df['is_limit_down'] = (
        (df['close'] <= df['pre_close'] * (1 - threshold + 0.001)) &
        (df['low'] == df['close'])
    )
    
    return df
```

### 4.2 行业映射

**问题**：
- TuShare: 申万行业分类
- AKShare: 东方财富行业分类
- BaoStock: 证监会行业分类

**解决方案**：
```python
# 建立行业映射表
INDUSTRY_MAPPING = {
    'akshare_to_sw': {
        '农林牧渔': '801010',
        '采掘': '801020',
        # ... 完整映射
    },
    'baostock_to_sw': {
        'A01': '801010',  # 农林牧渔
        'B06': '801020',  # 采掘
        # ... 完整映射
    }
}
```

### 4.3 数据质量校验

```python
class DataQualityChecker:
    """数据质量检查"""
    
    @staticmethod
    def check_completeness(df: pd.DataFrame, required_fields: list) -> bool:
        """完整性检查"""
        return all(field in df.columns for field in required_fields)
    
    @staticmethod
    def check_consistency(df: pd.DataFrame) -> bool:
        """一致性检查"""
        # 检查价格逻辑
        if not (df['low'] <= df['close']).all():
            return False
        if not (df['close'] <= df['high']).all():
            return False
        return True
    
    @staticmethod
    def check_coverage(df: pd.DataFrame, expected_count: int) -> bool:
        """覆盖率检查"""
        return len(df) >= expected_count * 0.95  # 允许5%缺失
```

---

## 5. 实施计划

### 5.1 批次 1: AKShare 适配（优先级 P0）

**目标**：完成 AKShare 作为第一兜底

**任务**：
1. 实现 `AKShareAdapter` 类
2. 完成 8 个 L1 接口映射
3. 补充涨跌停计算逻辑
4. 通过契约测试

**预计时间**：2-3 天

### 5.2 批次 2: BaoStock 适配（优先级 P1）

**目标**：完成 BaoStock 作为第二兜底

**任务**：
1. 实现 `BaoStockAdapter` 类
2. 完成 8 个 L1 接口映射
3. 建立行业映射表
4. 通过契约测试

**预计时间**：2-3 天

### 5.3 批次 3: 自动降级机制（优先级 P1）

**目标**：实现自动降级与数据源切换

**任务**：
1. 实现 `DataSourceManager`
2. 实现字段标准化
3. 实现数据质量校验
4. 通过集成测试

**预计时间**：1-2 天

---

## 6. 测试策略

### 6.1 单元测试

```python
def test_akshare_adapter_daily():
    """测试 AKShare daily 接口"""
    adapter = AKShareAdapter()
    df = adapter.fetch_daily('20250109')
    
    assert len(df) > 0
    assert 'stock_code' in df.columns
    assert 'trade_date' in df.columns
    assert 'close' in df.columns
```

### 6.2 集成测试

```python
def test_data_source_fallback():
    """测试数据源降级"""
    manager = DataSourceManager()
    
    # 模拟 TuShare 失败
    with mock.patch.object(TuShareAdapter, 'fetch_daily', side_effect=Exception):
        df, source = manager.fetch_with_fallback('fetch_daily', trade_date='20250109')
        
        assert source == 'AKShareAdapter'
        assert len(df) > 0
```

### 6.3 对比测试

```python
def test_data_consistency():
    """测试不同数据源一致性"""
    tushare_df = TuShareAdapter().fetch_daily('20250109')
    akshare_df = AKShareAdapter().fetch_daily('20250109')
    
    # 对比收盘价
    merged = tushare_df.merge(akshare_df, on='stock_code', suffixes=('_ts', '_ak'))
    diff = abs(merged['close_ts'] - merged['close_ak']) / merged['close_ts']
    
    assert (diff < 0.01).mean() > 0.95  # 95%以上数据偏差<1%
```

---

## 7. 配置管理

### 7.1 配置文件

```yaml
# config/data_sources.yaml
data_sources:
  priority:
    - tushare
    - akshare
    - baostock
  
  tushare:
    enabled: true
    token: ${TUSHARE_TOKEN}
    timeout: 30
    retry: 3
  
  akshare:
    enabled: true
    timeout: 30
    retry: 3
  
  baostock:
    enabled: true
    timeout: 30
    retry: 3
  
  fallback:
    auto_switch: true
    quality_threshold: 0.95
    log_level: WARNING
```

### 7.2 运行时切换

```python
# 手动指定数据源
manager = DataSourceManager(preferred_source='akshare')

# 禁用某个数据源
manager.disable_source('tushare')

# 查看当前数据源状态
manager.get_source_status()
```

---

## 8. 监控与告警

### 8.1 数据源健康检查

```python
class DataSourceHealthCheck:
    """数据源健康检查"""
    
    def check_all_sources(self) -> dict:
        """检查所有数据源"""
        results = {}
        for source in ['tushare', 'akshare', 'baostock']:
            results[source] = self.check_source(source)
        return results
    
    def check_source(self, source: str) -> dict:
        """检查单个数据源"""
        try:
            adapter = self.get_adapter(source)
            df = adapter.fetch_daily('20250109')
            
            return {
                'status': 'healthy',
                'latency': 0.5,  # 响应时间
                'coverage': len(df) / 5000,  # 覆盖率
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
            }
```

### 8.2 降级告警

```python
# 当发生数据源降级时发送告警
if current_source != 'tushare':
    logger.warning(f"Data source fallback: {current_source}")
    send_alert(f"Using fallback data source: {current_source}")
```

---

## 9. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-02-19 | 初版：定义三层兜底架构、接口映射、实施计划 |

---

## 10. 参考资料

- AKShare 文档: https://akshare.akfamily.xyz/
- BaoStock 文档: http://baostock.com/
- AData 文档: https://github.com/1nchaos/adata
- TuShare 文档: https://tushare.pro/document/2
