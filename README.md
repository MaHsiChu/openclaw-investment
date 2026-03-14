# OpenClaw Investment Analyst - 自我进化投资系统

一个能够**自主学习、自我进化**的AI驱动投资分析与模拟系统。

## 🌟 核心特性

### 1. 多维度投资分析
- **实时监控**: 互联网、银行、金融、AI、能源、游戏六大板块
- **技术指标**: MA、MACD、RSI、布林带等经典指标
- **基本面分析**: PE、PB、ROE、DCF估值模型
- **情绪分析**: 新闻情绪、社交媒体情绪
- **AI深度分析**: LLM驱动的研报解读与投资建议

### 2. 自我进化框架
系统能够自主学习和改进，无需人工干预：

```
知识获取 → 消化整合 → 应用验证 → 效果评估 → 反馈优化
     ↑                                        ↓
     └────────────────────────────────────────┘
```

**进化维度**:
- **知识进化**: 自动学习arXiv论文、GitHub项目、技术博客
- **策略进化**: 遗传算法优化投资策略，回测验证
- **Skill进化**: 自动识别能力缺口并开发新Skill
- **代码进化**: 自动重构优化，性能提升

### 3. 投资模拟系统
- **虚拟资金**: 模拟真实投资操作
- **策略回测**: 历史数据验证策略表现
- **收益跟踪**: 实时追踪投资组合表现
- **风险分析**: VaR、最大回撤、夏普比率

## 📁 项目结构

```
openclaw-investment/
├── config/                 # 配置文件
│   └── sectors.json       # 板块股票配置
├── data/                   # 数据获取模块
│   └── market_data.py     # 股票数据获取(美股/A股)
├── storage/               # 数据存储
│   └── database.py        # SQLite本地缓存
├── analyzer/              # 分析引擎
│   ├── technical.py       # 技术分析
│   ├── fundamental.py     # 基本面分析
│   ├── sentiment.py       # 情绪分析
│   └── ai_analyst.py      # AI深度分析
├── report/                # 报告生成
│   ├── daily_report.py    # 日报
│   ├── weekly_report.py   # 周报
│   └── sector_report.py   # 板块深度报告
├── simulation/            # 投资模拟
│   ├── portfolio.py       # 投资组合管理
│   ├── backtest.py        # 回测引擎
│   └── strategy.py        # 策略库
├── evolution/             # 自我进化模块 ⭐
│   ├── engine.py          # 进化引擎核心
│   ├── auto_learner.py    # 自动学习
│   └── skill_developer.py # 自动Skill开发
├── openclaw/              # OpenClaw集成
├── cli/                   # 命令行界面
│   └── main.py           # 交互式CLI
├── tests/                 # 测试用例
└── docs/                  # 文档
    └── SELF_EVOLUTION.md  # 进化框架文档
```

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行CLI
```bash
python cli/main.py
```

### 命令示例
```
> sectors          # 查看监控板块
> stocks ai        # 查看AI板块股票
> update ai        # 更新AI板块数据
> chart NVDA       # 查看NVDA股票图表
```

## 🧬 自我进化系统

### 自动学习 (Auto Learner)
自动搜索和学习前沿知识：
- **arXiv**: 量化金融、机器学习论文
- **GitHub**:  trending量化交易项目
- **MCP市场**: 新MCP服务器集成
- **Skill Hub**: 技能市场更新

### 策略进化 (Strategy Evolution)
使用遗传算法优化策略：
```python
# 策略参数自动调优
# 策略交叉组合
# 适应性选择机制
```

### 自动Skill开发 (Skill Developer)
识别能力缺口并自动生成Skill：
```python
# 识别缺口 → 生成代码 → 编写测试 → 部署上线
```

### 进化触发机制
- **定时进化**: 每日/每周/每月自动执行
- **事件驱动**: 新论文/市场变化/工具更新
- **性能驱动**: 收益下降/响应变慢时自动优化

## 📊 监控板块

### 互联网
META, GOOGL, AMZN, NFLX, BABA, TCEHY

### 银行
JPM, BAC, WFC, GS, MS, 工行/农行/中行

### 金融
V, MA, PYPL, SQ, COIN

### AI
NVDA, AMD, AVGO, ARM, SMCI

### 能源
XOM, CVX, COP, OXY, SLB

### 游戏
RBLX, EA, TTWO, U, ATVI

## 🔧 OpenClaw集成

### 命令
```
/invest sectors          # 查看板块
/invest update [sector]  # 更新数据
/invest report [type]    # 生成报告
/invest portfolio        # 查看组合
/invest simulate         # 运行模拟
/invest evolve status    # 进化状态
/invest evolve learn     # 立即学习
```

### 自动推送
- 每日市场简报 (飞书)
- 周报生成与推送
- 策略更新通知
- 异常预警

## 📈 路线图

### Phase 1 ✅ 数据获取层
- [x] 美股/A股数据获取
- [x] SQLite本地缓存
- [x] 基础CLI界面
- [x] 板块配置

### Phase 2 🔄 分析引擎
- [ ] 技术指标分析
- [ ] 报告生成系统
- [ ] 日报/周报模板

### Phase 3 📋 AI分析
- [ ] LLM研报解读
- [ ] 新闻情绪分析
- [ ] 多维度综合评分

### Phase 4 💰 投资模拟
- [ ] 投资组合管理
- [ ] 回测引擎
- [ ] 收益跟踪可视化

### Phase 5 🧠 自我进化
- [ ] 自动学习模块
- [ ] 策略遗传优化
- [ ] 自动Skill开发
- [ ] 代码自动重构

### Phase 6 🔌 OpenClaw集成
- [ ] 命令接口
- [ ] 定时任务调度
- [ ] 消息推送

## 📝 文档

- [项目规格书](PROJECT_SPEC.md)
- [自我进化框架](docs/SELF_EVOLUTION.md)
- [开发进度](PROGRESS.md)

## 🤝 贡献

这是一个自我进化的项目，欢迎提出改进建议！

## 📄 许可证

MIT License
