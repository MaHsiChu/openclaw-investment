# {{ title }}

**周期**: {{ week_start }} — {{ week_end }}
**生成时间**: {{ generated_at }}
**分析师**: {{ author }}

---

## 一周回顾

{% for sector in sectors %}
### {{ sector.name }}

| 股票 | 周涨跌幅 | 周最高 | 周最低 | 均量变化 | 信号 |
|------|----------|--------|--------|----------|------|
{% for s in sector.stocks %}
| {{ s.symbol }} | {{ s.week_change | format_pct }} | ${{ s.week_high | format_float }} | ${{ s.week_low | format_float }} | {{ s.volume_change | format_pct }} | {{ s.signal | signal_label }} |
{% endfor %}

{% endfor %}

---

## 趋势分析

### 强势板块
{% for s in trend_analysis.strong_sectors %}
- **{{ s.name }}**: {{ s.reason }}
{% endfor %}

### 弱势板块
{% for s in trend_analysis.weak_sectors %}
- **{{ s.name }}**: {{ s.reason }}
{% endfor %}

---

## 一周涨幅榜

| 排名 | 股票 | 涨跌幅 | 最新价 | 信号 |
|------|------|--------|--------|------|
{% for r in top_performers %}
| {{ loop.index }} | {{ r.symbol }} | {{ r.week_change | format_pct }} | ${{ r.price | format_float }} | {{ r.signal | signal_label }} |
{% endfor %}

## 一周跌幅榜

| 排名 | 股票 | 涨跌幅 | 最新价 | 信号 |
|------|------|--------|--------|------|
{% for r in bottom_performers %}
| {{ loop.index }} | {{ r.symbol }} | {{ r.week_change | format_pct }} | ${{ r.price | format_float }} | {{ r.signal | signal_label }} |
{% endfor %}

---

## 下周展望

{% if outlook.summary %}
{{ outlook.summary }}
{% endif %}

### 重点关注
{% for item in outlook.watchlist %}
- **{{ item.symbol }}**: {{ item.reason }}
{% endfor %}

---

## 风险提示

本报告由 OpenClaw Investment Analyst 自动生成，仅供参考，不构成投资建议。
投资有风险，入市需谨慎。
