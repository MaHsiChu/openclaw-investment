"""
Report Generator - 报告生成器基类
使用Jinja2模板引擎，支持markdown和html格式输出
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


class ReportFormat(Enum):
    MARKDOWN = "markdown"
    HTML = "html"


@dataclass
class ReportConfig:
    """报告配置"""
    title: str = "投资分析报告"
    author: str = "OpenClaw Investment Analyst"
    format: ReportFormat = ReportFormat.MARKDOWN
    output_dir: Optional[str] = None
    include_charts: bool = False


@dataclass
class ReportResult:
    """报告生成结果"""
    content: str
    format: ReportFormat
    generated_at: datetime = field(default_factory=datetime.now)
    output_path: Optional[Path] = None


class ReportGenerator(ABC):
    """报告生成器基类"""

    def __init__(self, config: Optional[ReportConfig] = None):
        self.config = config or ReportConfig()
        self._env = self._build_jinja_env()

    def _build_jinja_env(self) -> Environment:
        """构建Jinja2环境"""
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # 自定义过滤器
        env.filters["format_float"] = lambda v, d=2: f"{v:.{d}f}" if v is not None else "N/A"
        env.filters["format_pct"] = lambda v, d=2: f"{v:+.{d}f}%" if v is not None else "N/A"
        env.filters["signal_label"] = _signal_label
        env.filters["trend_label"] = _trend_label
        return env

    @abstractmethod
    def get_template_data(self) -> Dict[str, Any]:
        """子类实现：返回模板所需数据"""

    @abstractmethod
    def markdown_template_name(self) -> str:
        """子类实现：返回markdown模板文件名"""

    @abstractmethod
    def html_template_name(self) -> str:
        """子类实现：返回html模板文件名"""

    def generate(self, fmt: Optional[ReportFormat] = None) -> ReportResult:
        """生成报告"""
        fmt = fmt or self.config.format
        data = self.get_template_data()
        data.setdefault("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
        data.setdefault("author", self.config.author)

        if fmt == ReportFormat.HTML:
            content = self._render(self.html_template_name(), data)
        else:
            content = self._render(self.markdown_template_name(), data)

        result = ReportResult(content=content, format=fmt)

        if self.config.output_dir:
            result.output_path = self._save(result)

        return result

    def _render(self, template_name: str, data: Dict[str, Any]) -> str:
        try:
            tmpl = self._env.get_template(template_name)
            return tmpl.render(**data)
        except Exception as e:
            logger.error("Template render error (%s): %s", template_name, e)
            raise

    def _save(self, result: ReportResult) -> Path:
        out_dir = Path(self.config.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ext = "html" if result.format == ReportFormat.HTML else "md"
        filename = f"{self._report_filename()}_{result.generated_at.strftime('%Y%m%d_%H%M%S')}.{ext}"
        path = out_dir / filename
        path.write_text(result.content, encoding="utf-8")
        logger.info("Report saved: %s", path)
        return path

    def _report_filename(self) -> str:
        return "report"


# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------

def _signal_label(signal_str: str) -> str:
    mapping = {"buy": "买入", "sell": "卖出", "hold": "持有"}
    return mapping.get(str(signal_str).lower(), signal_str)


def _trend_label(trend_str: str) -> str:
    mapping = {"bullish": "看涨", "bearish": "看跌", "neutral": "中性"}
    return mapping.get(str(trend_str).lower(), trend_str)
