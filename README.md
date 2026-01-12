# Stockie Financial Analysis Platform

An open-source comprehensive personal financial management suite providing professional-grade stock analysis, SEC filing intelligence, and investment por## 📋 **Project Documentation**

This project maintains comprehensive documentation across four integrated files:

- **[📖 ARCHITECTURE_ROADMAP.md](ARCHITECTURE_ROADMAP.md)** - Detailed technical architecture, UI mockups, development phases, and iterative development strategy
- **[👤 AUTHORS.md](AUTHORS.md)** - Project leadership, contributor profiles, and team information
- **[🤝 CONTRIBUTING.md](CONTRIBUTING.md)** - Development standards, testing requirements, and contribution guidelines
- **[📄 README.md](README.md)** - Project overview, quick start guide, and current status (this file)management capabilities. Developed by the Stockie Foundation.

**Vision**: Building a complete personal financial management ecosystem. Portfolio and investment management is our initial focus, with plans to expand into budgeting, expense tracking, tax optimization, retirement planning, and comprehensive financial wellness tools over the coming years.

## 🚀 **Quick Start**

> ⚠️ **Setup Instructions Warning**: The installation and setup instructions below have not been fully tested and may contain errors or missing steps. We are actively working to validate and improve these instructions as part of Phase 1 development and will continue to refine them for each subsequent phase. Please report any issues you encounter. The instructions assume that you have postgresQL running on your system. There are no instructtions provided for setting that up.

```bash
# Clone and setup
git clone https://github.com/your-org/stockie.git
cd stockie

# Install Python dependencies
poetry install && poetry shell

# Installation assumes you have already got postgres running.
# Manually create postgres admin user and paths for storing <user>_data_ts and 
# <user>_index_ts tablespaces.
$ sudo -u postgres psql
psql# create role '<user>_admin' superuser
psql# exit

$ sudo -u postgres mkdir -p /mnt/pgdb/<user>/data
$ sudo -u postgres mkdir -p /mnt/pgdb/<user>/index

# Setup database
python -m stockie.cli create database --database abc_db --admin-user abc_admin --admin-password abc_admin --user abc --password abc \
       --data-path /mnt/pgdb/abc/data --index-path /mnt/pgdb/abc/index
createdb stockie_dev
psql stockie_dev < db/create_database.sql

# Disable <user>_admin until you need it again. If you need the user again you can enable 
# the role again with alter role <user>_admin superuser
$ sudo -u postgres psql
psql# alter role '<user>_admin' nosuperuser
psql# exit

# Configure environment
cp config/settings-dev.yaml.example config/settings-dev.yaml
# Edit configuration file with your database settings and with the indicators you want

# Run initial data pipeline
python src/stockie/jobs/daily.py --config-dir config
```

## ✨ **Key Features**

- **📊 Professional Charts**: Dual y-axis charts with 20+ technical indicators
- **📄 SEC Filing Analysis**: AI-powered 10-K/10-Q document analysis and summarization  
- **🎯 Technical Analysis**: SMA, RSI, MACD, Bollinger Bands with flexible time ranges (1M to 20+ years)
- **🏢 Company Intelligence**: KPI extraction and trend analysis from SEC filings
- **📰 News & Sentiment Analysis**: Automated news scraping and AI-powered sentiment analysis for tickers and market trends
- **₿ Cryptocurrency Support**: Full crypto price data integration via Yahoo Finance (BTC, ETH, major altcoins)
- **🔬 Trading Algorithm Infrastructure**: Framework for users to develop and backtest custom trading strategies with quadratic programming portfolio optimization (educational/research purposes, not trading advice)
- **🤖 AI Integration**: Pluggable LLM providers (OpenAI, Claude, Local models)
- **⚡ High Performance**: C++ services with Python data pipeline
- **🔧 Flexible Deployment**: Single desktop to distributed multi-server

## 🏗️ **Architecture Overview**

```
Qt C++ Desktop UI
        ↕
C++ Microservices (MarketData, CompanyData, Portfolio, NewsSentiment)
        ↕  
Python ETL Pipeline (daily.py, sec_filings.py, news_scraper.py, LLM processing)
        ↕
PostgreSQL Database (Stock/Crypto data, SEC filings, News/Sentiment, AI summaries)
```

**Data Pipeline:**
- `daily.py` - Stock/crypto prices and technical indicators (runs multiple times daily)
- `sec_filings.py` - SEC 10-K/10-Q downloads and processing (runs daily)
- `news_scraper.py` - Financial news scraping and sentiment analysis (runs multiple times daily)
- On-demand LLM processing for filing analysis, news summarization, and sentiment analysis

## 📊 **Current Status**

**Phase 1: Python Pipeline Foundation** (In Progress - 2 months)
- ✅ Stock price ingestion and technical indicators
- ✅ Database optimization tools (vacuum, analyzer, profiler) 
- ✅ Security fixes and comprehensive test coverage (176 tests, 94% coverage)
- 🔲 SEC filing integration and compression
- 🔲 News scraping and sentiment analysis integration
- 🔲 Cryptocurrency data integration via Yahoo Finance
- 🔲 LLM processing framework (filings + news sentiment)
- 🔲 Validate and fix setup/installation instructions

**Next Phases (Iterative Development):**
- **Phase 2**: C++ Services (2 months) + validate C++ build instructions
- **Phase 3**: Qt Desktop UI (2 months) + validate Qt setup and build process
- **Phase 4**: Advanced Features (2 months) + validate complete installation workflow
- **Phase 5**: AI/Voice Interface (3 months) + validate AI provider setup

**Development Approach**: Phases overlap with iterative integration. Stock price visualization can begin once data pipeline is stable, allowing early UI development and testing while backend services are being built.

## 🎯 **Target Users**

**Current Focus (Investment Management):**
- Individual investors and traders
- Financial advisors and analysts
- Investment research professionals  
- Portfolio managers

**Future Expansion (Personal Finance Suite):**
- Individuals seeking comprehensive financial management
- Families managing household budgets and investments
- Financial planning enthusiasts
- Anyone wanting integrated personal financial tools

## 💾 **Data Coverage**

- **Stock Data**: 8,000+ tickers with 5+ years of historical data
- **Cryptocurrency Data**: 500+ crypto assets with full historical data
- **SEC Filings**: ~3,500 companies with compressed 10-K/10-Q storage
- **News Coverage**: 100+ financial news sources with real-time scraping
- **Storage**: 75-150GB projected over 5 years (including news/crypto data)
- **AI Summaries**: On-demand processing with intelligent caching for filings and news

## 🛠️ **Technology Stack**

| Layer | Technology | Purpose |
|-------|------------|---------|
| **UI** | Qt 6 + C++ | Professional native desktop interface |
| **Services** | C++ 17/20 + gRPC | High-performance microservices |
| **Pipeline** | Python 3.11+ | ETL processes and data management |
| **AI/ML** | OpenAI, Claude, Llama | Document analysis and summarization |
| **Optimization** | SciPy, CVXPY | Quadratic programming for portfolio optimization |
| **Database** | PostgreSQL 15+ | Time-series and document storage |

## 📈 **Sample UI Layouts**

### Main Window
```
┌─────────────────────────────────────────────────────────────┐
│ File View Portfolio Analysis Tools      [AAPL ▼]           │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────────────────────────────────┐ │
│ │Chart Options│ │        Stock Price Chart               │ │
│ │● Candlestick│ │ $180┤           ┌─RSI                   │ │
│ │☑ SMA(20)    │ │     │  /\   /\  │ 100                  │ │
│ │☑ Bollinger  │ │ $160┤ /  \ /  \ │  80─RSI              │ │
│ │☑ RSI        │ │     │/    V    \│  60                  │ │
│ │○ 1M ●1Y ○Max│ │ $140┤          \│  40                  │ │
│ └─────────────┘ └─────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │[Technical][Company Data][KPIs][News][Algorithms][Portfolio]│ │
│ │           Selected Tab Content                          │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Company Data Tab (AI-Powered)
```
┌─────────────────────────────────────────────────────────────┐
│                Company Analysis (AI-Generated)             │
├─────────────────────────────────────────────────────────────┤
│ Latest Filing: 10-K 2024 │ [Processing with GPT-4 ⟳]      │
│                                                             │
│ Business Overview:                                          │
│ Apple Inc. designs and manufactures consumer electronics   │
│ globally. Services segment shows 22% revenue growth...     │
│ [AI Summary generated from latest SEC filing]              │
│                                                             │
│ Key Risk Factors (AI-Identified):                          │
│ • Supply chain disruptions in Asia-Pacific                 │
│ • Increased smartphone market competition                   │ 
│ • App Store regulatory changes                              │
└─────────────────────────────────────────────────────────────┘
```

### News & Sentiment Tab (AI-Powered)
```
┌─────────────────────────────────────────────────────────────┐
│                Market News & Sentiment Analysis            │
├─────────────────────────────────────────────────────────────┤
│ Market Sentiment: ● Bullish 68% │ Latest AAPL News:        │
│ AAPL Sentiment:   ● Positive 72%│ 📰 Q4 Earnings Beat      │
│                                  │ 📰 iPhone Sales Strong   │
│ [📊 Sentiment Trend - 30 Days]  │ 📰 Supply Chain Update   │
│                                  │                          │
│ News Impact Analysis:            │ Key Market Themes:       │
│ Earnings Report: +$3.20 (2.1%)  │ • Earnings optimism      │
│ Fed Decision:    -$2.10 (1.4%)  │ • Tech sector rotation   │
└─────────────────────────────────────────────────────────────┘
```

### Portfolio Optimization Tab (Educational/Research)
```
┌─────────────────────────────────────────────────────────────┐
│              Portfolio Optimization & Allocation           │
├─────────────────────────────────────────────────────────────┤
│ Templates: Conservative (40/30/30) │ Current Allocation:    │
│ • 40% Domestic  • 30% International│ Domestic:  36% ▼      │
│ • 30% Bonds                         │ Intl:      28% ▼      │
│                                     │ Bonds:     36% ▲      │
│ Rebalancing: ● Quarterly ○ Monthly │                       │
│ Next Scheduled: Jan 1, 2026         │ Drift: 2.3% (< 5%)   │
│                                     │                       │
│ Quadratic Programming Results:      │ Rebalancing Needed:   │
│ Expected Return: 8.4%               │ ⚠️ EDUCATIONAL USE     │
│ Expected Risk:   12.1%              │   NOT ADVICE          │
│ Sharpe Ratio:    0.69               │ [🔄 Optimize]         │
│ [📊 Efficient Frontier Chart]       │ [⚙️ Schedule Setup]   │
└─────────────────────────────────────────────────────────────┘
```

## 📋 **Project Documentation**

This project maintains comprehensive documentation across three integrated files:

- **[📖 ARCHITECTURE_ROADMAP.md](ARCHITECTURE_ROADMAP.md)** - Detailed technical architecture, UI mockups, development phases, and iterative development strategy
- **[� AUTHORS.md](AUTHORS.md)** - Project leadership, contributor profiles, and team information
- **[📄 README.md](README.md)** - Project overview, quick start guide, and current status (this file)

**Progress Reporting**: Documentation is updated monthly/quarterly to reflect development progress, completed milestones, and phase transitions, providing transparency on active development.

## 🔧 **Prerequisites**

- **Development**: Python 3.11+, Qt 6, PostgreSQL 15+, CMake 3.20+
- **System**: 16GB+ RAM, 100GB+ disk space, multi-core CPU recommended
- **Platform**: Linux (Ubuntu) primary development platform
- **APIs**: SEC EDGAR access (free), AI provider keys (optional)

### **Platform Support**
- **✅ Linux (Ubuntu)**: Primary development and testing platform
- **🔄 Windows (WSL)**: Validation and testing planned for future releases
- **🔄 macOS**: Support validation planned for future releases
- **📱 Mobile**: Not currently planned (desktop-focused financial platform)

## 📦 **Installation**

> ⚠️ **Setup Instructions Warning**: These installation instructions are preliminary and have not been fully validated. Errors or missing dependencies may be encountered. We are working to test and refine these instructions during development.

### Python Environment Setup
```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Setup project
poetry install
poetry shell

# Create admin user manually and directories for tablespaces <user>_data_ts and <user>_index_ts
# Typical user names are stockie or stockie_dev. Typical paths depend on your system
# NB: after installing the stockie database, you can disable the <user>_admin until you need it
# again.

$ sudo -u postgres psql
psql# create role '<user>_admin' with login '<user>_admin' superuser
psql# exit

$ sudo -u postgres mkdir -p /mnt/pgdb/<user>/data
$ sudo -u postgres mkdir -p /mnt/pgdb/<user>/index

# Setup database
python -m stockie.cli create database --database abc_db --admin-user abc_admin --admin-password abc_admin --user abc --password abc \
       --data-path /mnt/pgdb/abc/data --index-path /mnt/pgdb/abc/index
createdb stockie_dev
psql stockie_dev < db/create_database.sql

# Disable <user>_admin. If you need the user again you can enable the role again with alter role <user>_admin superuser
$ sudo -u postgres psql
psql# alter role '<user>_admin' nosuperuser
psql# exit
```

### Configuration
```bash
# Copy configuration template
cp config/settings-dev.yaml.example config/settings-dev.yaml

# Edit configuration (database connection, API keys)
nano config/settings-dev.yaml
```

### Run Data Pipeline
```bash
# Initial stock price loading
python src/stockie/jobs/daily.py --config-dir config

# Database analysis tools
python tools/db/analyzer.py --config-dir config
python tools/db/vacuum.py --config-dir config --type regular
```

## 🧪 **Testing**

```bash
# Run test suite (176 tests)
pytest

# Run with coverage report
pytest --cov=src/stockie --cov-report=html

# Performance testing
python tools/perf/performance_test.py --config-dir config
```

## 📊 **Performance Metrics**

- **Test Coverage**: 95% (231 tests passing)
- **Chart Loading Target**: <2 seconds for 5-year data
- **Service Response Target**: <100ms for cached data
- **Memory Usage**: <4GB typical operation

## 🤖 **AI Integration**

Stockie supports multiple AI providers for SEC filing analysis and news sentiment analysis:

- **OpenAI GPT-4**: Premium analysis, most comprehensive
- **Anthropic Claude**: Balanced performance and cost
- **Local Llama**: Privacy-focused, runs offline
- **Custom Models**: Specialized financial domain models

### **Future AI Considerations**
- **Model Context Protocol (MCP)**: Exploring integration for enhanced AI tool connectivity and financial data access patterns
- **Agent Frameworks**: Considering integration with AI agent systems for automated financial analysis workflows

Configure in `config/settings-dev.yaml`:
```yaml
ai_providers:
  openai:
    enabled: true
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4"
  
  local_llama:
    enabled: true
    model_path: "/models/llama-finance-7b"
```

## 🛣️ **Future Roadmap**

**Investment Platform Development (Iterative Approach):**
- **Q1-Q2 2026**: C++ Services Foundation (Phase 2, 2 months)
- **Q2-Q3 2026**: Qt Desktop UI Development (Phase 3, 2 months) 
- **Q3-Q4 2026**: Advanced Features and Polish (Phase 4, 2 months)
- **Q4 2026-Q1 2027**: AI/Voice Interface Integration (Phase 5, 3 months)
- **Q2 2027**: Multi-user and Enterprise Features

**Personal Finance Suite Expansion:**
- **2027**: Budgeting and expense tracking integration
- **2027**: Tax optimization and document management
- **2028**: Retirement and financial planning tools
- **2028**: Banking and account aggregation
- **2029**: Insurance and risk management modules
- **2030**: Complete personal financial wellness ecosystem

## 🤝 **Contributing**

**Stockie is an open-source project by the Stockie Foundation.** We welcome contributions from the financial technology and open-source communities.

This project is currently in active development (Phase 1). Contributions welcome after Phase 1 completion in:

**Investment Platform:**
- Additional technical indicators
- New AI provider integrations
- UI/UX improvements  
- Performance optimizations
- Documentation and testing

**Future Personal Finance Modules:**
- Budgeting and expense tracking algorithms
- Tax optimization strategies
- Financial planning calculators
- Data visualization improvements
- Mobile and web interface development

## 📄 **License**

Open-source under **MIT License** - Stockie Foundation

This project is developed by the **Stockie Foundation**, a non-profit organization dedicated to creating open-source personal financial management tools that empower individuals to take control of their financial future.

---

## 📞 **Support**

- **Project Documentation**: 
  - [ARCHITECTURE_ROADMAP.md](ARCHITECTURE_ROADMAP.md) - Detailed technical specifications and development phases
  - [AUTHORS.md](AUTHORS.md) - Project leadership and contributor information
- **Development Progress**: Documentation updated monthly/quarterly with phase progress and milestones
- **Issues**: GitHub Issues (when repository is public)
- **Discussions**: GitHub Discussions (when repository is public)

---

*Open-source personal financial management suite by the Stockie Foundation*  
*Current Focus: Professional investment analysis | Future: Complete financial wellness*  
*Development: Iterative approach with overlapping phases*  
*Last updated: October 27, 2025 | Phase 1: In Progress (2 months)*