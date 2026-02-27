# M3 🟠 calculator.py 的 quality_flag 缺少 stale_days 判断

## 问题定位

- **设计文件**: `docs/design/core-algorithms/irs/irs-algorithm.md` §3.4 (line 218-219)
- **正确实现**: `src/algorithms/irs/pipeline.py` (line 557-558)
- **问题代码**: `src/algorithms/irs/calculator.py` (line 262)

## 差异描述

### 设计规定 + pipeline.py 正确实现

quality_flag 的判定优先级：
1. `stale_days > 0` → `"stale"`
2. `sample_days < 60` → `"cold_start"`
3. 否则 → `"normal"`

```python
# pipeline.py:557-558
stale_days = int(float(item.get("stale_days", 0) or 0))
quality_flag = "stale" if stale_days > 0 else ("cold_start" if sample_days < 60 else "normal")
```

### calculator.py 的 bug

```python
# calculator.py:262
"quality_flag": "cold_start" if sample_days < 60 else "normal",
```

只检查了 `sample_days`，完全跳过了 `stale_days` 判断。
当 stale_days > 0 时，quality_flag 应为 `"stale"` 但实际输出 `"normal"` 或 `"cold_start"`。

## 影响

- Integration 层根据 quality_flag 决定是否回退 baseline 权重
- 如果 stale 数据被标记为 normal，Integration 会正常消费可能不准确的评分
- 当前 calculator.py 非主链，影响有限；但一旦升级为主链则成为数据质量漏洞

## 修复方案（唯一方案）

```python
# calculator.py — 替换 line 262-263 区域
stale_days = int(float(item.get("stale_days", 0) or 0))
quality_flag = "stale" if stale_days > 0 else ("cold_start" if sample_days < 60 else "normal")

# 在 output_rows.append 中使用：
"quality_flag": quality_flag,
"stale_days": stale_days,
```

## 风险

极低。纯逻辑修复，不影响评分计算。
