"""
AI Analyst - AI 深度分析模块
使用 LLM 分析多维度数据，生成投资建议与风险识别
"""
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AnalysisReport:
    """AI 分析报告"""
    symbol: str
    summary: str = ""
    recommendation: str = ""        # strong_buy / buy / hold / sell / strong_sell
    confidence: float = 0.0         # 0-100
    target_price: Optional[float] = None
    risk_level: str = ""            # low / medium / high
    key_factors: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class AIAnalyst:
    """AI 深度分析器

    支持多种 LLM 后端：
    - Anthropic Claude (默认)
    - OpenAI GPT
    - 本地 fallback（无需 API key 的规则引擎）
    """

    def __init__(self, provider: str = "auto", api_key: Optional[str] = None):
        """
        Args:
            provider: "anthropic" | "openai" | "auto" | "local"
            api_key: API key，不传则从环境变量获取
        """
        self.provider = provider
        self._api_key = api_key
        self._client = None

    def _resolve_provider(self) -> str:
        """自动检测可用的 LLM 提供商"""
        if self.provider != "auto":
            return self.provider

        if os.getenv("ANTHROPIC_API_KEY") or self._api_key:
            return "anthropic"
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        return "local"

    # ------------------------------------------------------------------
    # LLM 调用
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        """调用 LLM 获取分析"""
        provider = self._resolve_provider()

        if provider == "anthropic":
            return self._call_anthropic(prompt)
        elif provider == "openai":
            return self._call_openai(prompt)
        else:
            return self._local_analysis(prompt)

    def _call_anthropic(self, prompt: str) -> str:
        try:
            import anthropic
            key = self._api_key or os.getenv("ANTHROPIC_API_KEY")
            client = anthropic.Anthropic(api_key=key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except ImportError:
            logger.warning("anthropic package not installed, falling back to local")
            return self._local_analysis(prompt)
        except Exception as e:
            logger.error("Anthropic API error: %s", e)
            return self._local_analysis(prompt)

    def _call_openai(self, prompt: str) -> str:
        try:
            import openai
            key = self._api_key or os.getenv("OPENAI_API_KEY")
            client = openai.OpenAI(api_key=key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except ImportError:
            logger.warning("openai package not installed, falling back to local")
            return self._local_analysis(prompt)
        except Exception as e:
            logger.error("OpenAI API error: %s", e)
            return self._local_analysis(prompt)

    def _local_analysis(self, prompt: str) -> str:
        """本地规则引擎分析 (无需 API key)"""
        return "LOCAL_ANALYSIS"

    # ------------------------------------------------------------------
    # 数据准备
    # ------------------------------------------------------------------

    def _build_prompt(self, symbol: str, data: Dict[str, Any]) -> str:
        """构建分析提示词"""
        sections = [f"请作为专业投资分析师，对 {symbol} 进行深度分析。\n"]

        if "technical" in data:
            tech = data["technical"]
            sections.append("## 技术面数据")
            sections.append(f"趋势: {tech.get('trend', 'N/A')}")
            sections.append(f"信号: {tech.get('signal', 'N/A')}")
            sections.append(f"RSI: {tech.get('rsi', 'N/A')}")
            sections.append(f"MACD: {tech.get('macd', 'N/A')}")
            sections.append(f"布林带位置: {tech.get('bb_position', 'N/A')}")
            sections.append("")

        if "fundamental" in data:
            fund = data["fundamental"]
            sections.append("## 基本面数据")
            sections.append(f"PE: {fund.get('pe_ratio', 'N/A')}")
            sections.append(f"PB: {fund.get('pb_ratio', 'N/A')}")
            sections.append(f"ROE: {fund.get('roe', 'N/A')}")
            sections.append(f"营收增长: {fund.get('revenue_growth', 'N/A')}")
            sections.append(f"净利率: {fund.get('net_margin', 'N/A')}")
            sections.append(f"负债率: {fund.get('debt_to_equity', 'N/A')}")
            sections.append(f"综合评分: {fund.get('score', 'N/A')}")
            sections.append("")

        if "sentiment" in data:
            sent = data["sentiment"]
            sections.append("## 市场情绪")
            sections.append(f"情绪评分: {sent.get('overall_score', 'N/A')}")
            sections.append(f"情绪标签: {sent.get('overall_label', 'N/A')}")
            sections.append(f"正面新闻: {sent.get('positive_count', 0)}")
            sections.append(f"负面新闻: {sent.get('negative_count', 0)}")
            sections.append("")

        if "price" in data:
            price = data["price"]
            sections.append("## 价格数据")
            sections.append(f"当前价格: ${price.get('current', 'N/A')}")
            sections.append(f"52周高: ${price.get('high_52w', 'N/A')}")
            sections.append(f"52周低: ${price.get('low_52w', 'N/A')}")
            sections.append("")

        sections.append("""请以 JSON 格式返回分析结果，包含以下字段：
{
  "summary": "200字以内的分析摘要",
  "recommendation": "strong_buy / buy / hold / sell / strong_sell",
  "confidence": 0-100的置信度,
  "target_price": 目标价格（数字）,
  "risk_level": "low / medium / high",
  "key_factors": ["关键因素1", "关键因素2", ...],
  "risks": ["风险1", "风险2", ...],
  "opportunities": ["机会1", "机会2", ...]
}
只返回JSON，不要其他内容。""")

        return "\n".join(sections)

    # ------------------------------------------------------------------
    # 核心分析
    # ------------------------------------------------------------------

    def analyze(self, symbol: str, data: Dict[str, Any]) -> AnalysisReport:
        """执行 AI 深度分析

        Args:
            symbol: 股票代码
            data: 多维度数据字典，可包含:
                - technical: 技术面指标
                - fundamental: 基本面指标
                - sentiment: 情绪数据
                - price: 价格数据
        """
        prompt = self._build_prompt(symbol, data)
        response = self._call_llm(prompt)

        if response == "LOCAL_ANALYSIS":
            return self._rule_based_analysis(symbol, data)

        return self._parse_llm_response(symbol, response)

    def _parse_llm_response(self, symbol: str, response: str) -> AnalysisReport:
        """解析 LLM 返回的 JSON"""
        try:
            # 尝试从 response 中提取 JSON
            text = response.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])

            result = json.loads(text)
            return AnalysisReport(
                symbol=symbol,
                summary=result.get("summary", ""),
                recommendation=result.get("recommendation", "hold"),
                confidence=float(result.get("confidence", 50)),
                target_price=result.get("target_price"),
                risk_level=result.get("risk_level", "medium"),
                key_factors=result.get("key_factors", []),
                risks=result.get("risks", []),
                opportunities=result.get("opportunities", []),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse LLM response: %s", e)
            return AnalysisReport(
                symbol=symbol,
                summary=response[:500],
                recommendation="hold",
                confidence=30,
                risk_level="medium",
            )

    def _rule_based_analysis(self, symbol: str, data: Dict[str, Any]) -> AnalysisReport:
        """本地规则引擎分析（无需 LLM API）"""
        score = 50.0
        factors = []
        risks = []
        opportunities = []

        # 技术面
        tech = data.get("technical", {})
        if tech.get("signal") == "buy":
            score += 10
            factors.append("技术面呈现买入信号")
        elif tech.get("signal") == "sell":
            score -= 10
            factors.append("技术面呈现卖出信号")

        if tech.get("trend") == "bullish":
            score += 5
            opportunities.append("上升趋势中，动能良好")
        elif tech.get("trend") == "bearish":
            score -= 5
            risks.append("处于下降趋势中")

        rsi = tech.get("rsi")
        if rsi is not None:
            if rsi < 30:
                score += 8
                opportunities.append(f"RSI({rsi:.0f})处于超卖区域")
            elif rsi > 70:
                score -= 8
                risks.append(f"RSI({rsi:.0f})处于超买区域")

        # 基本面
        fund = data.get("fundamental", {})
        fund_score = fund.get("score", 0)
        if fund_score > 70:
            score += 10
            factors.append(f"基本面评分优秀({fund_score:.0f})")
        elif fund_score > 50:
            score += 5
        elif fund_score > 0:
            score -= 5
            risks.append(f"基本面评分偏低({fund_score:.0f})")

        pe = fund.get("pe_ratio")
        if pe is not None:
            if 0 < pe < 15:
                opportunities.append("估值偏低(低PE)")
            elif pe > 50:
                risks.append("估值偏高(高PE)")

        roe = fund.get("roe")
        if roe is not None and roe > 20:
            factors.append(f"高ROE({roe:.1f}%)表明盈利能力强")

        # 情绪面
        sent = data.get("sentiment", {})
        sent_score = sent.get("overall_score", 0)
        if sent_score > 0.3:
            score += 5
            factors.append("市场情绪积极")
        elif sent_score < -0.3:
            score -= 5
            risks.append("市场情绪偏负面")

        # 生成建议
        score = max(0, min(100, score))
        if score >= 75:
            recommendation = "strong_buy"
        elif score >= 60:
            recommendation = "buy"
        elif score >= 40:
            recommendation = "hold"
        elif score >= 25:
            recommendation = "sell"
        else:
            recommendation = "strong_sell"

        if score >= 60:
            risk_level = "low"
        elif score >= 40:
            risk_level = "medium"
        else:
            risk_level = "high"

        if not factors:
            factors.append("数据有限，建议关注后续走势")

        summary_parts = []
        if tech.get("trend"):
            summary_parts.append(f"技术面{tech['trend']}")
        if fund_score:
            summary_parts.append(f"基本面评分{fund_score:.0f}")
        if sent_score:
            summary_parts.append(f"市场情绪{'偏正' if sent_score > 0 else '偏负'}")

        summary = (
            f"{symbol}综合分析: {', '.join(summary_parts) if summary_parts else '数据不足'}。"
            f"综合评分{score:.0f}，建议{recommendation}。"
        )

        return AnalysisReport(
            symbol=symbol,
            summary=summary,
            recommendation=recommendation,
            confidence=score,
            risk_level=risk_level,
            key_factors=factors,
            risks=risks if risks else ["暂无明显风险"],
            opportunities=opportunities if opportunities else ["需要更多数据确认"],
        )

    # ------------------------------------------------------------------
    # 多股票综合分析
    # ------------------------------------------------------------------

    def compare(self, reports: List[AnalysisReport]) -> str:
        """多股票对比分析"""
        if not reports:
            return "无分析数据"

        sorted_reports = sorted(reports, key=lambda r: r.confidence, reverse=True)
        lines = ["**AI 多股对比分析**\n"]

        rec_cn = {
            "strong_buy": "强烈买入", "buy": "买入", "hold": "持有",
            "sell": "卖出", "strong_sell": "强烈卖出",
        }

        for i, r in enumerate(sorted_reports, 1):
            lines.append(
                f"{i}. **{r.symbol}** - {rec_cn.get(r.recommendation, r.recommendation)} "
                f"(置信度: {r.confidence:.0f}%)"
            )
            if r.key_factors:
                lines.append(f"   关键因素: {'; '.join(r.key_factors[:2])}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 报告格式化
    # ------------------------------------------------------------------

    def format_report(self, report: AnalysisReport) -> str:
        """格式化 AI 分析报告"""
        rec_cn = {
            "strong_buy": "强烈买入 🟢🟢",
            "buy": "买入 🟢",
            "hold": "持有 🟡",
            "sell": "卖出 🔴",
            "strong_sell": "强烈卖出 🔴🔴",
        }
        risk_cn = {"low": "低风险", "medium": "中等风险", "high": "高风险"}

        lines = [
            f"**AI 深度分析 - {report.symbol}**\n",
            f"建议: {rec_cn.get(report.recommendation, report.recommendation)}",
            f"置信度: {report.confidence:.0f}%",
            f"风险等级: {risk_cn.get(report.risk_level, report.risk_level)}",
        ]

        if report.target_price:
            lines.append(f"目标价: ${report.target_price:.2f}")

        lines.extend(["", f"**摘要**: {report.summary}"])

        if report.key_factors:
            lines.extend(["", "**关键因素**:"])
            for f in report.key_factors:
                lines.append(f"  + {f}")

        if report.risks and report.risks != ["暂无明显风险"]:
            lines.extend(["", "**风险提示**:"])
            for r in report.risks:
                lines.append(f"  - {r}")

        if report.opportunities and report.opportunities != ["需要更多数据确认"]:
            lines.extend(["", "**潜在机会**:"])
            for o in report.opportunities:
                lines.append(f"  + {o}")

        lines.extend([
            "",
            "---",
            "*以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。*",
        ])

        return "\n".join(lines)
