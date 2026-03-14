"""Auto Learner - 自动学习模块
主动搜索、学习和整合前沿知识
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiohttp


class AutoLearner:
    """自动学习者"""
    
    def __init__(self, knowledge_base):
        self.kb = knowledge_base
        self.session = None
        self.learning_history = []
        
        # 学习源配置
        self.sources = {
            "arxiv": {
                "enabled": True,
                "categories": ["q-fin.TR", "q-fin.PM", "q-fin.MF", "cs.LG", "cs.AI"],
                "keywords": ["trading strategy", "portfolio optimization", "market prediction",
                           "quantitative finance", "machine learning trading", "sentiment analysis"]
            },
            "github": {
                "enabled": True,
                "topics": ["quantitative-trading", "stock-analysis", "portfolio-management",
                          "trading-bot", "algorithmic-trading", "financial-analysis"],
                "languages": ["Python"]
            },
            "mcp": {
                "enabled": True,
                "sources": ["fastmcp.me", "mcpmarket.com"]
            },
            "skills": {
                "enabled": True,
                "hub": "clawhub.com"
            }
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    # ============== arXiv 学习 ==============
    
    async def learn_from_arxiv(self, days: int = 7) -> List[Dict]:
        """从arXiv学习最新论文"""
        from xml.etree import ElementTree as ET
        
        papers = []
        base_url = "http://export.arxiv.org/api/query"
        
        for category in self.sources["arxiv"]["categories"]:
            query = f"cat:{category}"
            params = {
                "search_query": query,
                "start": 0,
                "max_results": 10,
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }
            
            try:
                async with self.session.get(base_url, params=params) as resp:
                    if resp.status == 200:
                        xml_content = await resp.text()
                        root = ET.fromstring(xml_content)
                        
                        # 解析Atom feed
                        ns = {'atom': 'http://www.w3.org/2005/Atom'}
                        for entry in root.findall('atom:entry', ns):
                            title = entry.find('atom:title', ns).text
                            summary = entry.find('atom:summary', ns).text
                            published = entry.find('atom:published', ns).text
                            link = entry.find('atom:id', ns).text
                            
                            # 检查日期
                            pub_date = datetime.fromisoformat(published.replace('Z', '+00:00'))
                            if datetime.now(pub_date.tzinfo) - pub_date > timedelta(days=days):
                                continue
                            
                            # 检查关键词相关性
                            relevance = self._calculate_relevance(title + " " + summary)
                            
                            papers.append({
                                "source": "arxiv",
                                "title": title,
                                "summary": summary,
                                "link": link,
                                "published": published,
                                "category": category,
                                "relevance": relevance
                            })
            except Exception as e:
                print(f"Error fetching arXiv: {e}")
        
        return papers
    
    # ============== GitHub 学习 ==============
    
    async def learn_from_github(self) -> List[Dict]:
        """从GitHub学习优秀项目"""
        projects = []
        base_url = "https://api.github.com/search/repositories"
        
        for topic in self.sources["github"]["topics"]:
            params = {
                "q": f"topic:{topic} language:python",
                "sort": "stars",
                "order": "desc",
                "per_page": 5
            }
            
            try:
                async with self.session.get(base_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get("items", []):
                            projects.append({
                                "source": "github",
                                "name": item["full_name"],
                                "description": item["description"],
                                "stars": item["stargazers_count"],
                                "url": item["html_url"],
                                "topics": item.get("topics", []),
                                "relevance": self._calculate_relevance(
                                    item["description"] or ""
                                )
                            })
            except Exception as e:
                print(f"Error fetching GitHub: {e}")
        
        return projects
    
    # ============== MCP 市场学习 ==============
    
    async def learn_from_mcp(self) -> List[Dict]:
        """学习新的MCP服务器"""
        mcps = []
        # TODO: 实现MCP市场扫描
        return mcps
    
    # ============== 知识处理 ==============
    
    def _calculate_relevance(self, text: str) -> float:
        """计算文本相关性得分"""
        keywords = self.sources["arxiv"]["keywords"]
        text_lower = text.lower()
        
        score = 0.0
        for keyword in keywords:
            if keyword.lower() in text_lower:
                score += 1.0
        
        return min(score / len(keywords) * 10, 1.0)
    
    def _extract_insights(self, papers: List[Dict], projects: List[Dict]) -> List[Dict]:
        """提取关键洞察"""
        insights = []
        
        # 按相关性排序
        all_items = papers + projects
        all_items.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        
        for item in all_items[:10]:
            if item["source"] == "arxiv":
                insights.append({
                    "type": "paper",
                    "title": item["title"],
                    "key_point": item["summary"][:200] + "...",
                    "application": "TODO: 分析应用价值",
                    "source": item["link"]
                })
            else:
                insights.append({
                    "type": "project",
                    "name": item["name"],
                    "key_point": item["description"],
                    "application": "TODO: 分析可借鉴技术",
                    "source": item["url"]
                })
        
        return insights
    
    async def run_learning_session(self) -> Dict:
        """执行一次完整学习会话"""
        session_start = datetime.now()
        
        results = {
            "session_date": session_start.isoformat(),
            "sources": {},
            "insights": [],
            "knowledge_added": 0
        }
        
        # 从各个源学习
        if self.sources["arxiv"]["enabled"]:
            papers = await self.learn_from_arxiv()
            results["sources"]["arxiv"] = len(papers)
            for paper in papers:
                self.kb.add_knowledge(
                    source=paper["link"],
                    source_type="arxiv",
                    title=paper["title"],
                    content=paper["summary"],
                    summary=paper["summary"][:300],
                    tags=[paper["category"], "paper"],
                    relevance_score=paper["relevance"]
                )
        
        if self.sources["github"]["enabled"]:
            projects = await self.learn_from_github()
            results["sources"]["github"] = len(projects)
            for proj in projects:
                self.kb.add_knowledge(
                    source=proj["url"],
                    source_type="github",
                    title=proj["name"],
                    content=json.dumps(proj),
                    summary=proj["description"] or "",
                    tags=proj["topics"] + ["project"],
                    relevance_score=proj["relevance"]
                )
        
        # 提取洞察
        all_papers = [p for p in await self.learn_from_arxiv()]
        all_projects = [p for p in await self.learn_from_github()]
        results["insights"] = self._extract_insights(all_papers, all_projects)
        
        # 记录会话
        self.learning_history.append(results)
        
        return results
    
    def get_learning_report(self) -> str:
        """生成学习报告"""
        if not self.learning_history:
            return "No learning sessions yet."
        
        latest = self.learning_history[-1]
        report = f"""
# 自动学习报告

**会话时间**: {latest['session_date']}

## 数据源
"""
        for source, count in latest['sources'].items():
            report += f"- {source}: {count} 项\n"
        
        report += "\n## 关键洞察\n\n"
        for i, insight in enumerate(latest['insights'][:5], 1):
            report += f"### {i}. {insight['title'] or insight['name']}\n"
            report += f"- **类型**: {insight['type']}\n"
            report += f"- **关键点**: {insight['key_point']}\n"
            report += f"- **潜在应用**: {insight['application']}\n\n"
        
        return report


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from evolution.engine import KnowledgeBase
    
    async def test():
        kb = KnowledgeBase()
        async with AutoLearner(kb) as learner:
            result = await learner.run_learning_session()
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("\n" + learner.get_learning_report())
    
    asyncio.run(test())
