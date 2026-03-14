"""
Sentiment Analyzer - 新闻情绪分析模块
集成NewsAPI获取财经新闻，使用transformers进行情绪分类
"""
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    """新闻文章"""
    title: str
    source: str
    published_at: str
    url: str = ""
    description: str = ""


@dataclass
class SentimentResult:
    """情绪分析结果"""
    symbol: str
    overall_score: float  # -1.0 (极度看跌) 到 1.0 (极度看涨)
    overall_label: str  # positive / negative / neutral
    article_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    articles: List[Dict] = field(default_factory=list)
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class SentimentAnalyzer:
    """新闻情绪分析器"""

    def __init__(self, newsapi_key: Optional[str] = None):
        self.newsapi_key = newsapi_key or os.getenv("NEWSAPI_KEY")
        self._classifier = None

    # ------------------------------------------------------------------
    # NewsAPI 获取
    # ------------------------------------------------------------------

    def fetch_news(self, symbol: str, company_name: str = "",
                   days: int = 7, max_articles: int = 20) -> List[NewsArticle]:
        """从NewsAPI获取财经新闻"""
        if not self.newsapi_key:
            logger.warning("NewsAPI key not set, returning empty results")
            return []

        try:
            from newsapi import NewsApiClient
        except ImportError:
            logger.warning("newsapi-python not installed, returning empty results")
            return []

        api = NewsApiClient(api_key=self.newsapi_key)
        query = f"{symbol} OR {company_name}" if company_name else symbol
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        try:
            response = api.get_everything(
                q=query,
                from_param=from_date,
                language="en",
                sort_by="relevancy",
                page_size=max_articles,
            )
        except Exception as e:
            logger.error("NewsAPI error for %s: %s", symbol, e)
            return []

        articles = []
        for item in response.get("articles", []):
            articles.append(NewsArticle(
                title=item.get("title", ""),
                source=item.get("source", {}).get("name", ""),
                published_at=item.get("publishedAt", ""),
                url=item.get("url", ""),
                description=item.get("description", "") or "",
            ))
        return articles

    # ------------------------------------------------------------------
    # 情绪分类
    # ------------------------------------------------------------------

    def _get_classifier(self):
        """延迟加载transformers情绪分类器"""
        if self._classifier is None:
            try:
                from transformers import pipeline
                self._classifier = pipeline(
                    "sentiment-analysis",
                    model="distilbert-base-uncased-finetuned-sst-2-english",
                    truncation=True,
                    max_length=512,
                )
                logger.info("Sentiment classifier loaded")
            except ImportError:
                logger.warning("transformers not installed, using rule-based fallback")
                self._classifier = "fallback"
        return self._classifier

    def classify_text(self, text: str) -> Dict:
        """对单条文本进行情绪分类

        Returns:
            {"label": "positive"|"negative"|"neutral", "score": float}
        """
        if not text.strip():
            return {"label": "neutral", "score": 0.0}

        classifier = self._get_classifier()

        if classifier == "fallback":
            return self._rule_based_classify(text)

        try:
            result = classifier(text[:512])[0]
            label = result["label"].lower()
            score = result["score"]
            # 转换为 -1 到 1 的分数
            if label == "negative":
                return {"label": "negative", "score": -score}
            else:
                return {"label": "positive", "score": score}
        except Exception as e:
            logger.error("Classification error: %s", e)
            return {"label": "neutral", "score": 0.0}

    def _rule_based_classify(self, text: str) -> Dict:
        """基于关键词的简易情绪分类 (fallback)"""
        text_lower = text.lower()

        positive_words = [
            "surge", "soar", "rally", "gain", "rise", "profit", "beat",
            "upgrade", "bullish", "record high", "growth", "outperform",
            "positive", "strong", "buy", "upside", "boost", "breakout",
        ]
        negative_words = [
            "crash", "plunge", "drop", "fall", "loss", "miss", "decline",
            "downgrade", "bearish", "record low", "layoff", "underperform",
            "negative", "weak", "sell", "downside", "warning", "risk",
        ]

        pos = sum(1 for w in positive_words if w in text_lower)
        neg = sum(1 for w in negative_words if w in text_lower)
        total = pos + neg

        if total == 0:
            return {"label": "neutral", "score": 0.0}

        score = (pos - neg) / total
        if score > 0.15:
            label = "positive"
        elif score < -0.15:
            label = "negative"
        else:
            label = "neutral"

        return {"label": label, "score": round(score, 4)}

    # ------------------------------------------------------------------
    # 综合分析
    # ------------------------------------------------------------------

    def analyze(self, symbol: str, company_name: str = "",
                days: int = 7) -> SentimentResult:
        """综合情绪分析：获取新闻 + 分类 + 汇总"""
        articles = self.fetch_news(symbol, company_name, days=days)

        if not articles:
            return SentimentResult(
                symbol=symbol,
                overall_score=0.0,
                overall_label="neutral",
            )

        scored_articles = []
        scores = []
        pos_count = neg_count = neu_count = 0

        for article in articles:
            text = f"{article.title}. {article.description}"
            result = self.classify_text(text)
            scores.append(result["score"])

            if result["label"] == "positive":
                pos_count += 1
            elif result["label"] == "negative":
                neg_count += 1
            else:
                neu_count += 1

            scored_articles.append({
                "title": article.title,
                "source": article.source,
                "published_at": article.published_at,
                "sentiment_label": result["label"],
                "sentiment_score": result["score"],
            })

        overall_score = sum(scores) / len(scores) if scores else 0.0
        if overall_score > 0.15:
            overall_label = "positive"
        elif overall_score < -0.15:
            overall_label = "negative"
        else:
            overall_label = "neutral"

        return SentimentResult(
            symbol=symbol,
            overall_score=round(overall_score, 4),
            overall_label=overall_label,
            article_count=len(articles),
            positive_count=pos_count,
            negative_count=neg_count,
            neutral_count=neu_count,
            articles=scored_articles,
        )

    def save_to_db(self, result: SentimentResult, db) -> None:
        """将情绪分析结果保存到数据库

        Args:
            result: 分析结果
            db: DatabaseManager 实例
        """
        import sqlite3

        try:
            with sqlite3.connect(db.db_path) as conn:
                for article in result.articles:
                    conn.execute("""
                        INSERT INTO news_sentiment
                        (symbol, title, source, sentiment_score, sentiment_label, published_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        result.symbol,
                        article["title"],
                        article["source"],
                        article["sentiment_score"],
                        article["sentiment_label"],
                        article["published_at"],
                    ))
                conn.commit()
            logger.info("Saved %d sentiment records for %s",
                        len(result.articles), result.symbol)
        except Exception as e:
            logger.error("Error saving sentiment for %s: %s", result.symbol, e)

    def format_report(self, result: SentimentResult) -> str:
        """格式化情绪分析报告"""
        emoji = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}
        lines = [
            f"**新闻情绪分析 - {result.symbol}**\n",
            f"综合情绪: {emoji.get(result.overall_label, '⚪')} {result.overall_label} "
            f"(得分: {result.overall_score:+.2f})",
            f"新闻数量: {result.article_count}",
            f"  正面: {result.positive_count}  负面: {result.negative_count}  中性: {result.neutral_count}",
        ]

        if result.articles:
            lines.append("\n**近期新闻**:")
            for art in result.articles[:5]:
                icon = emoji.get(art["sentiment_label"], "⚪")
                lines.append(f"  {icon} {art['title'][:80]}  ({art['source']})")

        return "\n".join(lines)
