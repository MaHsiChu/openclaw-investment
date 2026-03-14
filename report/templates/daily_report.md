# {{ title }}

**生成时间**: {{ generated_at }}
**分析师**: {{ author }}

---

## 市场概览

| 指标 | 数值 |
|------|------|
| 分析板块数 | {{ market_overview.total_sectors }} |
| 分析股票数 | {{ market_overview.total_stocks }} |
| 看涨 | {{ market_overview.bullish_count }} |
| 看跌 | {{ market_overview.bearish_count }} |
| 中性 | {{ market_overview.neutral_count }} |
| 市场情绪 | {{ market_overview.sentiment }} |

{% if market_overview.summary %}
> {{ market_overview.summary }}
{% endif %}

---

## 板块分析

{% for sector in sectors %}
### {{ sector.name }}（{{ sector.symbol_key }}）

**板块表现**: {{ sector.sentiment }}
**分析标的**: {{ sector.stock_count }} 只

| 股票 | 最新价 | RSI | MACD | 趋势 | 信号 | 置信度 |
|------|--------|-----|------|------|------|--------|
{% for s in sector.stocks %}
| {{ s.symbol }} | ${{ s.price | format_float }} | {{ s.rsi | format_float(1) }} | {{ s.macd | format_float(3) }} | {{ s.trend | trend_label }} | {{ s.signal | signal_label }} | {{ s.confidence | format_float(1) }}% |
{% endfor %}

{% if sector.patterns %}
**K线形态**:
{% for p in sector.patterns %}
- {{ p.symbol }}: {{ p.pattern }}
{% endfor %}
{% endif %}

{% endfor %}

---

## 个股推荐

### 买入关注
{% if buy_recommendations %}
{% for r in buy_recommendations %}
**{{ r.symbol }}** — {{ r.name }}
- 价格: ${{ r.price | format_float }}
- RSI: {{ r.rsi | format_float(1) }} | MACD柱: {{ r.macd_hist | format_float(4) }}
- 支撑: ${{ r.support | format_float }} / 阻力: ${{ r.resistance | format_float }}
- 理由: {{ r.reason }}

{% endfor %}
{% else %}
_当前无明确买入信号_
{% endif %}

### 卖出/减仓关注
{% if sell_recommendations %}
{% for r in sell_recommendations %}
**{{ r.symbol }}** — {{ r.name }}
- 价格: ${{ r.price | format_float }}
- RSI: {{ r.rsi | format_float(1) }} | 布林带位置: {{ r.bb_position | format_float(1) }}%
- 理由: {{ r.reason }}

{% endfor %}
{% else %}
_当前无明确卖出信号_
{% endif %}

---

## 风险提示

本报告由 OpenClaw Investment Analyst 自动生成，仅供参考，不构成投资建议。
投资有风险，入市需谨慎。
