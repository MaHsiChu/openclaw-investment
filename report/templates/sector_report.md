# {{ title }}

**板块**: {{ sector_name }}
**生成时间**: {{ generated_at }}
**分析师**: {{ author }}

---

## 板块概览

| 指标 | 数值 |
|------|------|
| 分析标的 | {{ overview.stock_count }} 只 |
| 看涨 | {{ overview.bullish_count }} |
| 看跌 | {{ overview.bearish_count }} |
| 中性 | {{ overview.neutral_count }} |
| 板块评级 | {{ overview.rating }} |

{% if overview.description %}
{{ overview.description }}
{% endif %}

---

## 个股深度分析

{% for stock in stocks %}
### {{ stock.symbol }}{% if stock.name %} — {{ stock.name }}{% endif %}

**当前价格**: ${{ stock.price | format_float }} &nbsp;|&nbsp; **趋势**: {{ stock.trend | trend_label }} &nbsp;|&nbsp; **信号**: {{ stock.signal | signal_label }} ({{ stock.confidence | format_float(1) }}%)

#### 技术指标
| 指标 | 数值 | 状态 |
|------|------|------|
| SMA(5/20) | ${{ stock.sma_5 | format_float }} / ${{ stock.sma_20 | format_float }} | {{ "多头排列" if stock.sma_5 and stock.sma_20 and stock.sma_5 > stock.sma_20 else "空头排列" }} |
| EMA(12/26) | ${{ stock.ema_12 | format_float }} / ${{ stock.ema_26 | format_float }} | - |
| RSI(14) | {{ stock.rsi | format_float(1) }} | {{ "超卖" if stock.rsi and stock.rsi < 30 else "超买" if stock.rsi and stock.rsi > 70 else "正常" }} |
| MACD | {{ stock.macd | format_float(3) }} | {{ "金叉" if stock.macd_hist and stock.macd_hist > 0 else "死叉" }} |
| 布林带 %B | {{ stock.bb_position | format_float(1) }}% | {{ "下轨" if stock.bb_position and stock.bb_position < 20 else "上轨" if stock.bb_position and stock.bb_position > 80 else "中区" }} |
| KDJ (K/D/J) | {{ stock.k | format_float(1) }} / {{ stock.d | format_float(1) }} / {{ stock.j | format_float(1) }} | - |
| ATR(14) | {{ stock.atr | format_float(3) }} | - |

#### 支撑阻力
- **支撑位**: ${{ stock.support | format_float }}
- **阻力位**: ${{ stock.resistance | format_float }}
- **枢轴点**: ${{ stock.pivot | format_float }}

{% if stock.patterns %}
#### K线形态
{% for p in stock.patterns %}
- {{ p }}
{% endfor %}
{% endif %}

{% if stock.summary %}
#### 分析小结
{{ stock.summary }}
{% endif %}

---
{% endfor %}

## 板块相关性

{% if correlation %}
各标的趋势一致性: **{{ correlation.consistency }}%**

{% if correlation.leaders %}
**领涨标的**: {{ correlation.leaders | join(", ") }}
{% endif %}
{% if correlation.laggards %}
**落后标的**: {{ correlation.laggards | join(", ") }}
{% endif %}
{% endif %}

## 风险提示

本报告由 OpenClaw Investment Analyst 自动生成，仅供参考，不构成投资建议。
投资有风险，入市需谨慎。
