# OpenClaw Investment Analyst 项目
## AI驱动的专业投资分析与模拟系统

### 项目愿景
构建一个集成到OpenClaw的智能投资分析系统，能够：
- 实时监控多板块股市动态（互联网、银行、金融、AI、能源、游戏）
- 自动获取并阅读大量行业报告
- 以专业投资人视角定期生成分析报告
- 运行投资模拟，跟踪收益表现

### 核心模块

#### 1. 数据获取层 (data/)
- **market_data.py** - 实时股价数据获取
  - 支持美股(yfinance)、A股(akshare)
  - 板块股票池管理
  - 历史数据缓存
- **news_report.py** - 新闻与报告获取
  - 财经新闻爬虫
  - 研报PDF下载解析
  - 财报数据获取

#### 2. 分析引擎层 (analyzer/)
- **technical.py** - 技术分析
  - 移动平均线、MACD、RSI、布林带等
  - K线形态识别
  - 趋势判断
- **fundamental.py** - 基本面分析
  - 财务指标计算(PE、PB、ROE等)
  - 估值模型(DCF、相对估值)
  - 行业对比分析
- **sentiment.py** - 情绪分析
  - 新闻情绪NLP分析
  - 社交媒体情绪监控
  - 市场情绪指数
- **ai_analyst.py** - AI深度分析
  - LLM研报解读
  - 多维度综合分析
  - 风险识别

#### 3. 报告生成层 (report/)
- **daily_report.py** - 日报生成
- **weekly_report.py** - 周报生成
- **sector_report.py** - 板块深度报告
- **templates/** - 报告模板

#### 4. 投资模拟层 (simulation/)
- **portfolio.py** - 投资组合管理
- **backtest.py** - 回测引擎
- **strategy.py** - 投资策略库
- **performance.py** - 收益跟踪

#### 5. OpenClaw集成层 (openclaw/)
- **commands.py** - 命令接口
- **scheduler.py** - 定时任务
- **notifier.py** - 消息推送

### 技术栈
- Python 3.11+
- yfinance / akshare - 股票数据
- pandas / numpy - 数据处理
- ta-lib / pandas-ta - 技术指标
- transformers / langchain - AI分析
- rich / textual - CLI界面
- APScheduler - 定时任务
- sqlite - 本地数据存储

### 项目结构
```
openclaw-investment/
├── config/                 # 配置文件
│   ├── sectors.json       # 板块股票配置
│   ├── settings.yaml      # 系统设置
│   └── api_keys.env       # API密钥
├── data/                   # 数据获取模块
├── analyzer/              # 分析引擎
├── report/                # 报告生成
├── simulation/            # 投资模拟
├── openclaw/              # OpenClaw集成
├── storage/               # 数据存储
├── logs/                  # 日志
├── tests/                 # 测试
├── requirements.txt
└── README.md
```

### 数据流
1. 定时任务触发数据获取
2. 数据清洗存储到本地
3. 分析引擎多维度处理
4. LLM生成投资建议
5. 生成结构化报告
6. 推送至OpenClaw

### 监控板块
- **互联网**: META, GOOGL, AMZN, NFLX, BABA, TCEHY
- **银行**: JPM, BAC, WFC, C, GS, MS
- **金融**: V, MA, PYPL, SQ, COIN
- **AI**: NVDA, AMD, TSM, AVGO, ARM, SMCI
- **能源**: XOM, CVX, COP, OXY, SLB
- **游戏**: RBLX, EA, TTWO, U, PLTK

### 开发阶段
1. **Phase 1**: 数据获取层 + 基础CLI
2. **Phase 2**: 技术分析 + 报告生成
3. **Phase 3**: AI分析 + 基本面分析
4. **Phase 4**: 投资模拟 + 回测
5. **Phase 5**: OpenClaw集成 + 自动化
