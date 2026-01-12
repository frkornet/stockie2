# Stockie Financial Analysis Platform
## Architecture, Roadmap & Development Plan

> **📚 Project Documentation Suite**: This technical roadmap is part of an integrated documentation set including [📄 README.md](README.md) for project overview, [👤 AUTHORS.md](AUTHORS.md) for team information, and [🤝 CONTRIBUTING.md](CONTRIBUTING.md) for development standards. Documentation is updated quarterly to document and track development progress.

# 📊 **Project Overview**

Stockie is an open-source comprehensive personal financial management suite developed by the Stockie Foundation. This document covers the **Investment Management Module** - the initial focus of our broader vision to create a complete personal financial ecosystem using freely available data sources.

**Current Phase**: Professional-grade stock analysis, SEC filing intelligence, sentiment analysis, and investment portfolio management capabilities in a native desktop application.

**Long-term Vision**: Expand beyond investment management to include budgeting, expense tracking, tax optimization, retirement planning, and comprehensive financial wellness tools, creating a unified personal financial management platform over the next 5-10 years. Module priorities and implementation order will be influenced by community feedback and user needs.

## 🎯 **Target Users**

**Current Focus (Investment Management Module):**
- Individual investors and traders
- Financial advisors and analysts  
- Investment research professionals
- Portfolio managers

**Future Scope (Complete Personal Finance Suite):**
- Individuals seeking comprehensive financial management
- Families managing household budgets and investments
- Financial planning enthusiasts
- Anyone wanting integrated personal financial tools

## ✨ **Key Features**

**Investment Management Module (Current Focus):**
- **Professional Stock Charts**: Dual y-axis charts with technical indicators
- **SEC Filing Analysis**: AI-powered 10-K/10-Q document analysis and summarization
- **Technical Analysis**: 20+ technical indicators with flexible time ranges (1M to 20+ years)
- **Company Intelligence**: KPI extraction and trend analysis from SEC filings
- **News & Sentiment Analysis**: Automated news scraping and AI-powered sentiment analysis for tickers and market trends
- **Cryptocurrency Support**: Full crypto price data integration via Yahoo Finance (BTC, ETH, major altcoins)
- **Trading Algorithm Infrastructure**: Framework for users to develop and backtest custom trading strategies with quadratic programming portfolio optimization (educational/research purposes, not trading advice)

**Future Personal Finance Modules:**
- **Budgeting & Expense Tracking**: Automated categorization, spending insights, budget optimization
- **Tax Optimization**: Document management, deduction tracking, tax planning strategies
- **Retirement Planning**: 401k/IRA analysis, retirement projections, withdrawal strategies
- **Banking Integration**: Account aggregation, cash flow analysis, automated transfers
- **Insurance Management**: Coverage analysis, premium optimization, risk assessment
- **Financial Wellness**: Credit monitoring, debt management, financial goal tracking

---

# 🏗️ **System Architecture**

Stockie's architecture is designed to balance performance, scalability, and maintainability. Stockie is initially targeted at Linux with possible extension to Linux derivatives on MacOs and Windows. The hybrid approach of combining Python data pipelines with C++ services and Qt UI addresses specific requirements for financial software:

- **Performance**: Sub-second chart rendering for 20+ years of data
- **Scalability**: Ability to scale from laptop to distributed multi-server setup
- **Maintainability**: Clear separation of concerns between data processing and user interaction
- **Flexibility**: Support for both local and distributed deployment patterns

The Investment Module consists of the following key components:

**Python Data Pipeline:**
- **Rapid Development**: Excel at ETL, data processing, and AI/ML integration
- **Rich Ecosystem**: Pandas, NumPy, requests, LLM libraries readily available
- **Maintenance**: Easy to modify data sources, add indicators, integrate new APIs
- **Scripting**: Perfect for scheduled jobs (daily.py, sec_filings.py, news_scraper.py)

**C++ Services Layer:**
- **Performance**: Critical for real-time chart data serving and technical indicator calculations
- **Memory Efficiency**: Handle large datasets (20+ years × 8000+ tickers) efficiently
- **Low Latency**: <100ms response times for cached data queries
- **Resource Control**: Precise memory and CPU usage management

**Qt C++ Desktop UI:**
- **Native Performance**: Hardware-accelerated rendering for complex financial charts
- **Professional Appearance**: Indistinguishable from commercial financial platforms
- **Cross-Platform**: Windows, Linux, macOS support with native look-and-feel
- **Rich Components**: Built-in charting, data visualization, and financial UI widgets

**PostgreSQL Database:**
- **Time-Series Performance**: Optimized for financial data queries and aggregations
- **Data Integrity**: ACID compliance critical for financial calculations
- **Scalability**: Handles both desktop (~100GB) and enterprise (multi-TB) deployments
- **Compression**: Efficient storage for SEC filings and news archives

The Qt UI interfaces with the C++ Services Layer in one of two ways. If both components run on the same desktop, communication will be done via shared memory. If they are on different machines, the communication will be done over the network using gRPC. Running both components on the same machine will be faster and the way most users will use the system.

The chart below shows the way the components are arranged and communicate with one another.

```
┌────────┐       ┌──────────┐        ┌──────────┐       ┌───────────┐
|  Qt UI | <==>  | Services | <==>   | Stockie  | <==>  | Data      |
└────────┘       |  Layer   |        | Database |       | Pipelines |
                 └──────────┘        └──────────┘       └───────────┘
```

The Qt C++ Desktop UI provides stock charts with dual y-axes, candlesticks, and technical indicators. As well as company data derived from 10-K and 10-Q reports, AI summaries, KPI trends derived from these filings. 

The C++ Microservices Layer provides 1) market data services (such as stock prices and technical indicators), 2) company data services (such as filing summaries and KPI trends), and 3) portfolio services (such as holdings, performance, and rebalancing).

The Stockie PostgreSQL Database stores stock/crypto prices, technical indicators, 10-K / 10-Q filings (using compression), company meta data, and news articles (including summaries). Some of the data may be stored in the Linux file system to manage size of database.

The Data Pipelines layer consists of a set of jobs that run periodically to collect data and store collected data in the Stockie PostgreSQL Database. There are 3 pipelines currently envisaged. Daily.py is used to collect stock /crypto prices and calculate technical indicators. The job runs multiple times a day during trading days. The SEC filings (10-K and 10-Q) are collected from EDGAR by sec_filings.py. This job will run daily during trading days. News article will be collected using news_scraper.py and the job will run multiple times per day. It will identify the articles which may have an impact on the stock price of stocks or crypto currencies. Daily.py exist and will require a few enhancements. Sec_filings.py and news_scraper.py still need to be developed.

If we are able to find a free source for providing annual meeting transcripts then we will integrate that into the overall Investment Module and extend sec_filings.py to handle the transcripts. These will be important and can add significant value to assessing the individual companies.

The chart below explains the different Data Pipelines graphically with a brief description of the main functionality offered. Most of the functionality for daily.py exists with exception for crypto prices and atomic swap (i.e. storing stock prices and calculated indicators in temporary tables while daily.py is running and then replacing the stock prices and calculated indicators with in a single operation to reduce impact on users). The others still need to be developed.

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│   daily.py          │    │   sec_filings.py     │    │ news_scraper.py │
│   (Multiple/day)    │    │   (Once daily)       │    │ (Multiple/day)  │
│                     │    │                      │    │                 │
│ • Load stock prices │    │ • Download 10-K/10-Q │    │ • Scrape news   │
│ • Load crypto prices│    │   from EDGAR         │    │   articles      │
│ • Calculate         │    │ • Compress & store   │    │ • Sentiment     │
│   indicators        │    │ • Extract metadata   │    │   analysis      │
│ • Atomic swap       │    │ • Index documents    │    │ • Market trend  │
│ • VACUUM maintenance│    │                      │    │   detection     │
└─────────────────────┘    └──────────────────────┘    └─────────────────┘

┌─────────────────────┐    ┌──────────────────────┐
│ LLM Processing      │    │ Portfolio Scheduler  │
│ (On-demand)         │    │ (Scheduled)          │
│                     │    │                      │
│ • Decompress        │    │ • Rebalancing checks │
│   filings           │    │   (Monthly/Quarterly)│
│ • AI analysis       │    │ • Drift analysis     │
│ • Generate          │    │ • Allocation alerts  │
│   summaries         │    │ • Optimization runs  │
└─────────────────────┘    └──────────────────────┘

┌─────────────────────┐
│ Alert System        │
│ (Real-time)         │
│                     │
│ • Price alerts      │
│ • News alerts       │
│ • Sentiment alerts  │
│ • Rebalance alerts  │
│ • Market volatility │
│   warnings          │
└─────────────────────┘
```

The outlined architecture for the Investment Module provides a solid basis to implement the other modules and offers the following benefits:

1. **Performance**: C++ services deliver financial-grade responsiveness
2. **Maintainability**: Python pipelines easy to modify and extend
3. **Scalability**: Seamless transition from desktop to distributed deployment
4. **Development Velocity**: Right tool for each layer accelerates development
5. **User Experience**: Qt delivers professional, responsive financial UI
6. **Data Integrity**: PostgreSQL ensures reliable financial calculations
7. **Future-Proof**: Modular design accommodates personal finance module expansion

---

# 🖥️ **User Interface Design**

The screen designs below are intended to show how the envisaged functionality will look like from a user perspective. The intention is to make the user interface intuitive and simple to use. This is a first pass at the functionality and the designs will be updated based upon implementation experience and user feedback.

This is the main screen the user will see when logging on to Stockie application. Some of the functionality will not be available from day 1. There are some 20 different technical indicators and more work is needed to determine how best to make all these technical indicators available in the user interface. The Price Chart will be available for stocks first and once the crypto currencies prices are stored, they can also be selected and charted. The Tab Content Area depends on the specific tab selected. The tabs are listed below in more detail to help the user visualize what we have in mind.

```
┌───────────────────────────────────────────────────────────────────────────┐
│ Budget    Tax    Invest    Retire    Tools   Help            [AAPL    ▼]  │
├───────────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────┐ ┌──────────────────────────────────────────────────┐ │
│ │ Chart Controls   │ │                                                  │ │
│ │                  │ │                   Price Chart                    │ │
│ │ Chart Type:      │ │                                                  │ │
│ │ ○ Line Chart     │ │  $180 ┤                               ┌─ RSI     │ │
│ │ ● Candlesticks   │ │       │    /\      /\                │  100      │ │
│ │                  │ │  $160 ┤   /  \    /  \    Bollinger │   80       │ │
│ │ Indicators:      │ │       │  /    \  /    \   Bands     │   60 ─ RSI │ │
│ │ ☑ SMA(20)        │ │  $140 ┤ /      \/      \ /‾‾‾‾‾‾‾‾‾\ │   40      │ │
│ │ ☑ Bollinger      │ │       │/                \          \│   20       │ │
│ │ ☑ RSI            │ │  $120 ┤                  \________/  │    0      │ │
│ │ ☐ MACD           │ │       └──────────────────────────────┴───────────┘ │
│ │ ☐ Volume         │ │       Jan   Mar   May   Jul   Sep   Nov    2024  │ │
│ │                  │ │                                                  │ │
│ │ Time Range:      │ └──────────────────────────────────────────────────┘ │
│ │ ○ 1M  ○ 3M  ● 1Y │                                                      │
│ │ ○ 2Y  ○ 5Y  ○ Max│ ┌──────────────────────────────────────────────────┐ │
│ │ ○ Custom:        │ │ [Technical] [Company] [KPIs] [Sentiment]         │ │
│ │   [Start] [End]  │ │ [Algorithms] [Portfolio]                         │ │
│ └──────────────────┘ │                                                  │ │
│                      │          Tab Content Area                        │ │
│                      │                                                  │ │
│                      │  (Selected tab shows relevant data/analysis)     │ │
│                      │                                                  │ │
│                      └──────────────────────────────────────────────────┘ │
├───────────────────────────────────────────────────────────────────────────┤
│ Status: Connected | Last update: Oct 27, 2025 14:23 EST | AI: GPT-4       │
└───────────────────────────────────────────────────────────────────────────┘
```

The top menu is used to allow the user to select the Personal Finance Module the user wants to work with. For now there is only one option available Invest. The main menu option allows the user to select the stock and/or crypto currency the user is interested in.

As can be seen in the main screen layout, there are six different tabs that the user can select. The tabs are described one by one below including a rough screen design to help the user to visualize what these tabs have to offer. The tabs will be added as extra Data Pipelines are implemented.

## **Technical Indicators Tab**

This is a very rough design and may change. The intention is show a range of technical indicators and help the user determine how the stock / crypto is doing and whether the price is expected to go up or down in the coming days, weeks, months using standard technical indicator interpretations. Note these interpretations may be wrong and no guarantee is made that the prices will follow these standard interpretations. The tab will show trend indicators, momentum indicators, volatility indicators, and volume indicators. A way will be provided to allow the user to select the specific indicators they want to per group.

```
┌──────────────────────────────────────────────────────────────────┐
│                    Technical Analysis Summary                    │
├──────────────────────────────────────────────────────────────────┤
│ Trend Indicators:                    Momentum Indicators:        │
│ ┌────────────────────────────────┐   ┌─────────────────────────┐ │
│ │ SMA(20):  $165.23  ↗           │   │ RSI(14):   62.4  ⚠      │ │
│ │ SMA(50):  $158.91  ↗           │   │ MACD:      1.23  ↗      │ │
│ │ EMA(12):  $167.45  ↗           │   │ Stoch:     45.2  →      │ │
│ └────────────────────────────────┘   └─────────────────────────┘ │
│                                                                  │
│ Volatility Indicators:                Volume Indicators:         │
│ ┌────────────────────────────────┐   ┌─────────────────────────┐ │
│ │ BB Upper: $172.50              │   │ Volume:    1.2M  ↓      │ │
│ │ BB Lower: $155.80              │   │ Avg Vol:   1.8M         │ │
│ │ ATR:      $8.45                │   │ OBV:       +125K ↗      │ │
│ └────────────────────────────────┘   └─────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## **Company Data Tab**

The Company Data tab displays the AI summaries derived from 10-K, 10-Q filings, and possibly investor meeting transcripts if these are freely available. The intention of the tab is to describe the business the company is in as well as the key strategic risks and the key business initiatives to improve and grow the business. The content is generated by running the 10-K and 10-Q filings and investor meeting transcripts if available through an LLM and asking it to summarize each company in a consistent manner using the same AI chatbot prompt. This will be part of the daily sec_filings.py run.

```
┌──────────────────────────────────────────────────────────────────┐
│                    Company Analysis (AI-Generated)               │
├──────────────────────────────────────────────────────────────────┤
│ Latest Filing: 10-K 2024 (Filed: Mar 15, 2024) │ [Processing ⟳] │
│                                                                  │
│ Business Overview:                                               │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ Apple Inc. designs, manufactures, and markets consumer       │ │
│ │ electronics globally. The company has diversified into       │ │
│ │ services with 22% revenue growth in Services segment.        │ │
│ │ [AI Summary from latest 10-K filing - GPT-4]                 │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ Key Risk Factors (AI-Identified):                                │
│ • Supply chain disruptions in Asia-Pacific region                │
│ • Increased competition in smartphone market                     │
│ • Regulatory changes affecting App Store policies                │
│ • Semiconductor shortages impacting production                   │
│ • Currency fluctuations in international markets                 │
│                                                                  │
│ Strategic Initiatives:                                           │
│ • Expansion into autonomous vehicle technology                   │
│ • Investment in AR/VR platforms and content                      │
│ • Carbon neutral goal by 2030 across supply chain                │
└──────────────────────────────────────────────────────────────────┘
```

## **KPIs Tab**

The KPIs can be grouped into (1) liquidity ratios (i.e. current ratio and quick ratio), (2) asset management ratios (total asset turnover ratio, inventory turnover ratio, and days sales outstanding), (3) financial leverage ratios (debt/assets ratio, debt/equity ratio, and market/book ratio), (4) profitability ratios (gross profit margin, profit margin, return on assets, return on equity, DuPont formula, and degree of leverage), (5) market value ratios (price/earnings ratio, price/earnings to growth ratio, book value/share, and price to book ratio), and (6) dividend policy ratios (dividend yield and payout ratio).

The calculation of these ratios relies on the balance sheet and profit and loss statements. These annual and quarterly financial statements are extracted from the 10-K and 10-Q filings and analyzed and normalized by LLM to provide consistency across companies. The user can select key attributes from these statements and display them over a select number of quarters or years at the top box of the tab. The user can select whether to display them as a table or a line chart. The second box in the tab can be used to select the ratios the user wants to see in the format the user selects (table or line chart).

The tab is intended to allow the user to dig deeper into the performance of the company using fundamental analysis concepts.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Financial Key Metrics                        │
├─────────────────────────────────────────────────────────────────┤
│ Quarterly/Yearly Trends :                                       │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Revenue (B):    [table or line chart]                       │ │
│ │ Net Income (B): [table or line chart]                       │ │
│ │ EPS:            [table or line chart]                       │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Ratios:                                                         │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ P/E Ratio:   [table or line chart]                          │ │
│ │ ROE:         [table or line chart]                          │ │
│ │ ROA:         [table or line chart]                          │ │
│ │ Debt/Equity: [table or line chart]                          │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## **Sentiment Tab**

Sentiment analysis relies on a range of data sources that need to be integrated to come to an overall sentiment score using LLM to analyze the different data sources. A key challenge is to access these data sources and collect relevant data for free. Sentiment is typically a trailing indicator.

For a comprehensive sentiment analysis using LLM, we ideally need access to a range of data sources: (1) company filings, (2) economic/macro data, (3) industry-specific information, (4) company-specific news/transcripts, (5) social/retail sentiment, (6) insider trading & institutional holdings, (7) market microstructure/technical data, (8) competitor & peer analysis, (9)_ ESG & regulatory events, (10) analyst ratings & estimates, (11) options market sentiment, and (12) global/geopolitical events.

The data sources can be grouped into three types of sentiments: (1) fundamental sentiment (data sources (1), (2), (3), (4), (8), and (10)), (2) technical sentiment (data source (7)), and (3) alternative sentiment (data sources (5), (6), (9), (11), and (12)).

To implement collecting and analyzing all these different data sources in real time will take time to develop, maintain, and run. Since this needs to run on a relatively small (desktop) machine and not on some large computer farm, we need to be selective in the sources we collect and analayze. We also have limited development resources that can monitor these data pipelines and fix issues as they occur due to data source changes in terms API or website. Below is a rough outline how the range of data sources may be expanded and integrated in Stockie sentiment analysis over time.

1. Start with high-quality structured data:

    - (7) yfinance: interface exists
    - (1) SEC EDGAR: most authoritative
    - (2) FRED: economic context
    - (11) Options: VIX index

2. Add alternative data:

    - (4) GoogleNews/BingNews/NewsAPI/Finnhub: company and market news
    - (5) Reddit/Twitter: retail investor sentiment
    - (6) Insider trading: smart money

NB: possible insider trading sources are (1) SEC EDGAR Forms 3, 4, and 5, (2) SEC 13F Filings, (3) OpenInsider aggregated insider trading, (4) whale Whisdom free 13F data, and (5) Fintel limited free institutional data.

```
┌────────────────────────────────────────────────────────────────────┐
│                    Sentiment Analysis                              │
├────────────────────────────────────────────────────────────────────┤
| Overview 
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │ Fundamental Sentiment Score: x / 100                           │ │
│ │ Technical Sentiment Score:   x / 100                           │ │
│ │ Alternative Sentiment Score: x / 100                           │ │
| | Overall Sentiment Score:     x / 100                           | |
| |                                                                | |
| | <summary text>                                                 | |
│ └────────────────────────────────────────────────────────────────┘ │
|                                                                    |
│ Fundamental Sentiment:                   Latest News (AAPL):       │
│ ┌─────────────────────────────────────┐  ┌───────────────────────┐ │
│ │ <summary text>                      │  │ 📰 Apple Reports Q4   │ │
│ │                                     │  │    Earnings Beat      │ │
│ └─────────────────────────────────────┘  │    [2 hours ago]      │ │
│                                          │                       │ │
│ Technical Sentiment                      │ 📰 iPhone 16 Sales    │ │
│ ┌─────────────────────────────────────┐  │    Exceed Expectations│ │
│ │ <summary text>                      │  │    [4 hours ago]      │ │
│ |                                     |  │                       │ │
│ └─────────────────────────────────────┘  │ 📰 Supply Chain       │ │
│                                          │    Challenges         │ │
│ Alternative Sentiment                    │    [6 hours ago]      │ │
│ ┌─────────────────────────────────────┐  │                       │ │
│ │ <summary text>                      │  | 📰 Apple CEO fired    │ │
│ |                                     |  │    [2 days ago]       │ │
│ └─────────────────────────────────────┘  └───────────────────────┘ │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## **Trading Algorithms Tab**

A simple set of trading algorithms will be developed and made available for the user to select from. These trading algorithms will run in the C++ service layer and have been pre-developed. The user can customize the trading algorithm used by specify parameters (e.g. entry point and exit point). The initial set of trading algorithms that will be implemented is 

1. moving average cross over (SMA and EMA), 
2. RSI mean reversion, and 
3. quadratic optimization algorithms (minimize variance)

Later on, an infrastructure framework will be developed to allow users to develop custom trading algorithms using python. This requires the framework to run python code. This may be implemented by adding a python background service along side the C++ services. Details of how this will work still need to be worked out. Once that is done, the UI will be updated to reflect allow users to run their custom developed trading algorithms.

The backtest will support running the algorithm over a specified period for a specified duration. This will use the actual price data available over the specified period. This will run the backtest one time over the period. If synthetic data is selected, the backtest will be run a specified number of times and the price data will be generatedusing a range of possible outcomes. The backtest results will show the average return as well as the range of outcomes observed. This is akin to a Markov Chain simulation.

To be able to backtest a trading algorithm, the backtester needs to have rules for deciding what stocks to select for investment after stocks have been sold. To do that, the backtester needs to determine how well the trading algorithm worked for each stock up to now and select the stocks that have the highest historical return observed so far assuming the entry point criteria have been met. To use this method, a warm up period is needed. Stocks that have not completed at least 2 entry-exit cycles will be ignored.

```
┌───────────────────────────────────────────────────────────────┐
│             Algorithm Development & Backtesting               │
├───────────────────────────────────────────────────────────────┤
│ Strategy Library:                   Active Strategy:          │
│ ┌─────────────────────────────┐     ┌──────────────────────┐  │
│ │ ○ SMA Crossover             │     │ Entry:  RSI < 30     │  │
│ │ ○ EMA Crossover             │     │ Exit:   RSI > 70     │  │
│ │ ● RSI Mean Reversion        │     │ Risk:   5% per trade │  │
│ │ ○ Quadratic optimization    │     │ Budget: 10,000       │  │
│ │ [                           │     |                      |  │
│ └─────────────────────────────┘     └──────────────────────┘  │
│                                                               │
| Backtest Params             Backtest Results   [Backtest]     |
│ ┌───────────────────┐       ┌─────────────────────────────┐   |
│ | Start: 1/1/2019   |       │ Total Return:    +24.5%▲    │   │
│ | End:   12/31/2025 |       │ Sharpe Ratio:    1.23       │   │
│ | Rebalance: Qtr    |       │ Max Drawdown:    -8.4%      │   │
│ | Warmup: 2 years   |       │ Win Rate:        58.2%      │   │
│ | Synthetic: yes/no |       │ [📊 Performance Chart]      │   │
│ └───────────────────┘       └─────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

## **Portfolio Optimization Tab**

Portfolio optimization uses standard templates for investors that the user can select and tailor to their preferences. The templates split the portfolio in stocks, crypto, and bonds. The stocks can be split into large cap, small cap, domestic, international, emerging, and sector specific (e.g. tech companies, AI companies, biotech companies, etcetera). On top of that the user needs to specify the amount invested in each category and whether this is in a taxable account or tax-deferred account. The user needs to specify the marginal tax bracket the user is in to determine the after tax gains.

To help the user determine appropriate percentages for the different asset classes, the user needs to fill out a survey to determine the user's investment profile. This can range from very conservative to very aggressive. Where a user sits depends on the tolerance for losses and the ability to absorb losses. A young person starting to invest with decades until retirement can afford to be more aggressive (and probably should) versus a person close to retirement needs to be more conservative (assuming all investments are needed to cover for retirement).

On the user the screen the user can make a topdown target allocation and can specify the accounts owned with current investment amounts. That allows the system to determine how far off the user is from the specified target. The user can specify how and when to rebalance the portfolio as well as the trading method to use.

The user can run a backtest to get a sense of the range of possible outcomes or the user can run the backtest over a specified period with known prices for the investment. Underlying the system maps the asset classes (e.g. domestic large) to well known low cost ETFs. The proposed rebalancing transactions are designed in a way to minimize taxes. Bonds and cash is put into tax deferred accounts. If there is not sufficient space in the tax deferred accounts, bonds will be bought in taxabale accounts. ETFs will be bought and allocated to tax deferred and if not enough space, the remainder will be allocated in taxable accounts. The rationale is to avoid having to pay taxes on interest income and dividend as much as possible.

In terms of trading methods, the simple rule based method uses ETFs to meet the target requirements. The quadratic trading method focuses on minimizing the expected variance while allowing for some drift from the specified topdown target allocations. The last trading method uses LLM chatbot to make investment decisions based upon the parameters (allocation targets, investments in accounts, and the rebalancing intention). The LLM will have the most leeway in terms of the proposed transactions. Note that this is also the most risky trading approach and little evidence exists that this trading method is sound. So, the user accepts all risk for using this approach. The LLM trading method is provided to show the user alternatives and what other trading robots are doing under the covers.

```
┌─────────────────────────────────────────────────────────────────────┐
│   Portfolio Optimization & Allocation [Survey]                      │
├─────────────────────────────────────────────────────────────────────┤
| Target ROI:                 10%                                     |
| Investor type:              Aggressive                              |
|                                                                     |
│ Allocation Targets:                                                 │
│ ┌───────────────────────────────────────────────────────────┐       │
| |                Target  Actual E[ROI]  Std Dev    Amount   |       |
│ │ Domestic Large:  30%    36%    10%     0.7     $ 103,500  │       │
│ │ Domestic Small:  10%     0%    12%     0.9     $  34,500  │       │
│ │ International:   10%     0%    12%     1.0     $  34,500  │       │
│ │ Emerging:        10%     0%    15%     1.2     $  34,500  │       │
│ │ Bonds:           30%    14%     4%     0.2     $ 103,500  │       │
│ | Algo Trading:     0%     0%    20%     1.5     $     -    |       │
│ | Crypto:           3%     3%    20%     2.0     $  10,350  |       │
| | Cash:             7%    28%                    $  24,150  |       |
| | Total                          11%     0.9     $ 345,000  |       |
│ └───────────────────────────────────────────────────────────┘       │
│                                                                     │
│ Accounts and Funding:                                               │
│ ┌───────────────────────────────────────────────────┐               │
| |         Ticker    Shares       Total     Type     |               |
│ │ Acct #1 VOO         100      $ 125,000  taxable   │               │
| | Acct #1 VGT          10      $  25,000  taxable   |               |
| | Acct #1 Cash          -      $  50,000  taxable   |               |
│ │ Acct #2 VGT         100      $  50,000  deferred  │               │
│ │ Acct #2 BND        1000      $  50,000  deferred  │               │
│ │ Acct #3 Cash          -      $  45,000  deferred  │               │
│ │ Acct #4  -            -           -        -      │               │
│ │ Acct #5  -            -           -        -      │               │
| | Total                        $ 345,000            |               |
│ └───────────────────────────────────────────────────┘               │
│                                                                     │
│ Rebalancing Schedule:                Trading:                       │
│ ┌────────────────────────────────┐   ┌──────────────────────────┐   |
│ │ ○ Quarterly (Jan/Apr/Jul/Oct)  │   | ○ Trading Agent (LLM)    |   │
│ │ ○ Monthly (1st of month)       │   | ○ Quadratic optimization |   │
│ │ ○ Semi-Annual (Jan/Jul)        │   | ● Simple Rule Based      |   │
│ │ ● Annual (January)             │   └──────────────────────────┘   │
│ │ ○ Threshold-based: ± 10% drift │                                  │
│ └────────────────────────────────┘                                  │
|                                                                     |
│ Backtest:                        Rebalancing Needed:                │
│ ┌─────────────────────────────┐  ┌────────────────────────────────┐ │
│ │ Parameters:                 │  │ Acct  Ticker Action   Amount   │ |
│ │ Start:          1/1/2019    │  │  #1    VOO    Sell   $ 21,500  │ │
│ │ End:            12/31/2025  │  │  #1    VGT    Sell   $ 25,000  │ │
│ │ Warmup:         2 years     │  │  #1    VB     Buy    $ 34,500  │ │
| | Synthetic:      yes/no      |  |  #1    VXUS   Buy    $ 34,500  | |
| |                             |  |  #1    VWO    Buy    $ 27,500  | |
| | Max Return:     25.4%       |  |  #3    VWO    Buy    $  7,000  | |
| | Avg Return:     8.4%        |  |  #2    VGT    Sell   $ 50,000  | |
| | Min Return:     -5.4%       |  |  #2    BND    Buy    $ 50,000  | |
| | Sharpe Ratio:   0.69        |  |  #3    BND    Buy    $  3,500  | |
| | [📊 Risk/Return Chart]      |  |  #3    BTC    Buy    $ 10,350  | |
│ └─────────────────────────────┘  └────────────────────────────────┘ |
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

# 📊 **Data Storage Strategy**

The ability to store all the different types of data will be critical for the successful implementatioon of the investment module. Below is a first attempt to estimate the amount of data that needs to be stored. Note that the market data estimate is based upon current data storage usage. The other estimates are current best estimates and will be refined as we build the system and gain experience running the system.

### **Market Data (Stocks & Crypto)**
- **Daily price data**: ~8,000 stock tickers + ~500 crypto assets × 20 years × 250 days = ~45M records
- **Technical indicators**: Pre-calculated and stored daily for stocks and crypto
- **Cryptocurrency data**: BTC, ETH, major altcoins via Yahoo Finance integration
- **Storage requirement**: ~45 GB for historical price/indicator data

### **SEC Filing Data**
- **Active filers**: ~3,500 companies (of 8,000 tickers)
- **Filing frequency**: 5 per year (1 × 10-K + 4 × 10-Q) = 17,500 annual filings
- **Compressed storage**: ~ 1 MB per filing (gzip compression)
- **Annual storage**: ~17 GB compressed per year
- **5-year projection**: ~85 GB for complete filing archive

### **News & Sentiment Data**
- **News articles**: ~100-500 articles per day across major financial sources
- **Sentiment analysis**: AI-processed sentiment scores for articles and tickers
- **Market trend data**: Aggregated sentiment trends and market perception indicators
- **Storage requirement**: ~5-10 GB annually for news archive and sentiment data

### **AI-Generated Content**
- **Filing summaries**: ~50-100 KB per processed filing
- **News summaries**: ~10-20 KB per processed article
- **Cache storage**: ~2-4 GB for all summaries (filings + news)
- **LLM processing**: On-demand with intelligent caching for performance

### **Total Storage Projection**
- **Year 1**: ~80 GB (including news and crypto data)
- **Year 5**: ~250 GB (manageable on modern systems)

---

# 🎯 **Work Breakdown Structure (WBS)**

This section provides a high-level breakdown structure for completing Stockie version 1.0 (investment module). The WBS builds out the architecture and UI outlined in earlier sections and will be refined as we build the system and gain experience building the various components of the system. 

## **WBS-1: Infrastructure & Core Data**
A. **Implement dual table swap for stock prices and technical indicators**
   - Create temporary table, calculate all indicators, atomically swap with production table
   - Essential for production performance and avoiding table locks

B. **Add cryptocurrency ticker support**
   - Extend data pipeline to handle crypto tickers (BTC-USD, ETH-USD, etc.) alongside traditional stock tickers
   - Update price ingestion and technical indicators to work with crypto data sources
   - No database schema changes needed - existing ticker column handles crypto symbols

C. **Complete type hint coverage**
   - Fix missing return type hints in `CalculateIndicators._process()`, `PerformanceIndicators.__init__()`, and inner functions
   - Add missing parameter type hints in `TrendIndicators.macd()` and `load_stock_prices()`
   - Ensure proper imports for complex types (`Callable`, `Union`, etc.) where needed
   - Run mypy or similar type checker to validate completeness and catch type-related issues

D. **Implement stockie database CLI**
   - Implement CLI framework with helper functions in the stockie.db directory
   - Implement database create command to create stockie database
   - Implement database drop command to drop an existing stockie database
   - Update documentation to use CLI to create stockie database

## **WBS-2: C++ Services Infrastructure**
A. **Build service communication framework** 
   - Implement service communication supporting both shared memory (desktop) and gRPC (distributed deployment)
   - Create abstract communication interface, service discovery, health monitoring, and message passing infrastructure

B. **Implement initial MarketDataService**
   - Create C++ service to serve stock price data, technical indicators, and chart data from PostgreSQL
   - Implement caching, data aggregation, and optimized queries for financial charting performance

## **WBS-3: UI Framework & Visualization**
A. **Build Qt 6 UI framework foundation**
   - Create Qt 6 main application framework with menu system, navigation structure, tab-based content organization
   - Establish status bar, overall UI architecture, and foundation for all subsequent UI components
   - Include stock selection patterns and service integration framework

B. **Build stock price visualization UI**
   - Create Qt 6 UI component for stock price graphs with candlestick toggle and technical indicator overlays (RSI, Bollinger Bands)
   - Validates complete stack: Python → PostgreSQL → C++ Service → Qt UI
   - Focus on real-time chart rendering with indicator overlays

## **WBS-4: Company Summary**
A. **Implement SEC filings pipeline**
   - Implement SEC filings data pipeline (sec_filings.py job) for ~3,500 tickers
   - Download and process 10-K, 10-Q, and 8-K filings for AI-powered analysis

B. **Implement initial CompanyDataService**
   - Create C++ service to serve SEC filing data, company summaries, and compressed filing metadata
   - Implement caching, filing retrieval, and summary data serving for company analysis components

C. **Add company summaries to UI**
   - Process SEC filing data to generate AI-powered company summaries
   - Create structured business descriptions using AI analysis of fundamental data

## **WBS-5: Company KPI**
A. **Generate company KPIs**
    - Extract key performance indicators from SEC filing data
    - Build on summary work to identify and calculate financial metrics and business KPIs

B. **Extend CompanyDataService with KPI support**
    - Extend CompanyDataService to serve KPI data, financial metrics, and trend analysis
    - Add KPI caching, aggregation capabilities, and optimized queries for financial metrics visualization

C. **Add company KPIs to UI**
    - Update Qt 6 UI to display company KPIs
    - Add KPI visualization components accessing CompanyDataService for financial metrics display

## **WBS-6: News Sentiment**
A. **Implement news scraping pipeline**
    - Implement news scraping pipeline (news_scrapers.py) to collect financial news articles related to tracked tickers
    - Match news articles to relevant tickers and store data for sentiment analysis processing

B. **Generate news sentiment analysis**
    - Process scraped news articles to perform sentiment analysis on ticker-related news
    - Generate sentiment scores (positive, negative, neutral) and confidence metrics aggregated by ticker

C. **Add news sentiment to UI**
    - Update Qt 6 UI to display news sentiment analysis results
    - Add news sentiment visualization components showing recent news, sentiment scores, and sentiment trends

## **WBS-7: Portfolio Foundation**
A. **Create portfolio tracking database schema**
    - Create database schema and tables to track portfolios and their evolution over time
    - Include tables for portfolio definitions, holdings history, transactions, performance metrics, and rebalancing events

B. **Implement rebalancing scheduler**
    - Create automated rebalancing scheduler to periodically review and rebalance portfolios
    - Include configurable rebalancing frequencies and triggers based on target allocations and drift thresholds

C. **Implement backtesting framework**
    - Build backtesting framework to test portfolio optimization strategies against historical data
    - Include performance metrics calculation, risk analysis, drawdown analysis, and comparison tools

D. **Predict company expected return and standard deviation (risk)** 
    - Use historical performance data to estimate and record expected return and standard deviation
    - Use sentiment data for market and company to record the updated expected return and standard deviation with the help of an LLM (including rationale for change)

## **WBS-8: Portfolio Functionality**
A. **Implement standard allocation templates**
    - Create standard portfolio allocation templates (conservative, moderate, aggressive)
    - Predefined asset allocation percentages and risk parameters as starting points for optimization
    - Map asset classes to ETFs (e.g. VOO domestic large cap) and allow user to make changes to the mappings
    - Implement survey to determine investor profile for the user
    - Use investor profile to populate the target allocations for the user as a starting point.

B. **Implement quadratic programming library**
    - Integrate quadratic programming optimization libraries (SciPy/CVXPY) for mean-variance portfolio optimization
    - Implement efficient frontier calculation, risk-return optimization, and constraint handling for portfolio construction

C. **Add portfolio management to UI**
    - Create Qt 6 UI components for portfolio management including portfolio creation, allocation visualization, performance tracking, and rebalancing interfaces
    - Integrate with portfolio database schema and optimization libraries to provide complete portfolio management functionality

## **WBS-9: LLM Trading Agent**

A. **Select LLM framework**
    - Define high-level tasks that the LLM trading agent needs to execute in the overall portfolio workflow
    - Determine the data sources that the LLM needs to carry out these high-level tasks
    - Review frameworks and select appropriate framework to allow use of local and external LLMs

B. **Implement LLM Trading Agent**
    - Define prompts for each of the high-level tasks. The prompts need to ensure that the LLM provides a structured response, so the existing code can work with the result
    - Implement RAG data collection hooks to provide the LLM with all available relevant data and help it improve its response
    - Implement selected framework along with RAG hooks and prompts

C. **Add LLM Trading Agent to UI**
    - Extend the UI to allow the user to select LLM trading method for portfolio management
    - Integrate LLM trading agent into backtesting framework
    - Add general LLM question and answer capability to UI. These prompts are not pre-cooked and are specified by the user 

## **WBS-10: Stockie Release 1.0**

A. **Package Stockie Software**
    - Review how to package and distribute software using PyPi ecosystem so users can install it with pip install stockie
    - Package Stockie software, so users can install it with pip install stockie
    - Write installation script to assist the user in setting up Stockie and do an initial default configuration

B. **Write initial documentation set**
    - Write installation instructions for Ubuntu Linux (additional platforms to be added later)
    - Write user guide on how to configure and use Stockie

C. **Validate installation instructions**
    - Test installation instructions to ensure installation instructions are complete
    - Address any missing dependencies or configuration issues

# Critical Success Factors (CSF) and High-Level Timeline

Key risks for implementing the investment module are summarized in the table below. The risks are managed by developing the system in an iterative manner that allows us to build experience with the architecture and tools and also makes clear early on what is and isn't feasible. This allows us to detect early on whether the risks are materializing.

Key risks around LLMs and free data access are beyond our circle of influence and are accepted as is since the intent is to build an investment module with LLM and free data access at the centre. If these do not work as envisaged we will need to go back to the drawing board and completely reconsider the intent,  scope, and timeline of the investment module.

The remaining risks can be managed by increasing skills and taking longer to develop. That is handled by the contingency included in the plan. Please note that the 60 work breakdown structure below includes 6 weeks of contingency and an extra quarter of contingency (Q2 2026) in the overall timeline. So, nineteen weeks of contingency overall. That should be sufficient to address the risks within our circle of influence.

To help manage the risks further, unit tests will be developed as functionality is added to the system. The intention is to have at least a coverage rate of 80%. Pytest is used for python unit tests, the C++ services will have unit tests using Google Test (aka GTest), and the UI will use QTest framework for unit tests. As functionality is added the solution is put in production to ensure that it works as intended and there are no issues. This is a basic integration test to ensure things work end to end.

| Risk / CSF                                                                      |    Impact     |
|---------------------------------------------------------------------------------|---------------| 
| Architecture does not work or has hidden issues                                 | Low           |
| Insufficient C++ skills to develop the system                                   | Low - Medium  |
| Qt 6.10 UI is too complex and labor intensive to develop                        | Medium        |
| SEC filing API is too complicated to use                                        | Medium        |
| LLM is unable to generate KPIs from the SEC filings in a consistent manner      | Medium - High |
| LLM framework proves too hard to implement                                      | Medium - High |
| News scraping data pipeline proves too difficult to develop, run, and maintain  | High          |
| Portfolio requirements unclear and too hard to implement                        | High          |
| Unable to access data for free at volume (e.g. news articles)                   | High          |

The table below summarizes the estimated elapsed time to implement the investment module. The estimates assume that the risks can be managed and that they do not prove too disruptive. 

| Work Breakdown Structure (WBS)                   |     Elapsed    |
|--------------------------------------------------|----------------|
| **1. Infrastructure & Core Data**                | **2 weeks**    |
|   - A. dual table swap                           | 1 week         |
|   - B. crypto ticker support                     | 1 week         |
|   - C. complete type hint coverage               | 0 week         |
|   - D. stockie database create/drop CLI          | 0 week         |
| **2. C++ Services Infrastructure**               | **4 weeks**    |
|   - A. build service communication framework     | 1 week         |
|   - B. implement initial market data service     | 3 weeks        |
| **3. UI Framework & Visualization**              | **4 weeks**    |
|   - A. build Qt 6 UI framework foundation        | 2 weeks        |
|   - B. build stock price visualization           | 2 weeks        |
| **4. Company Summary**                           | **5 weeks**    |
|   - A. implement SEC filings pipeline            | 2 weeks        |
|   - B. implement initial CompanyDataService      | 1 week         |
|   - C. add company summaries to UI               | 2 weeks        |
| **5. Company KPIs**                              | **6 weeks**    |
|   - A. generate company KPIs                     | 2 weeks        |
|   - B. add KPI support to CompanyDataService     | 2 weeks        |
|   - C. add company KPIs to UI                    | 2 weeks        |
| **6. News Sentiment**                            | **6 weeks**    |
|   - A. implement news scraping pipeline          | 3 weeks        |
|   - B. generate company sentiment scores         | 2 weeks        |
|   - C. add news sentiment to UI                  | 1 week         |
| **7. Portfolio Foundation**                      | **6 weeks**    |
|   - A. create portfolio database schema          | 1 week         |
|   - B. implement rebalance scheduler             | 1 week         |
|   - C. implement backtesting framework           | 2 weeks        |
|   - D. predict company expected return & risk    | 2 weeks        |
| **8. Portfolio Functionality**                   | **6 weeks**    |
|   - A. implement target allocation templates     | 2 weeks        |
|   - B. implement quadratic programming algo lib  | 2 weeks        |
|   - C. add portfolio functionality to UI         | 2 weeks        |
| **9. LLM Trading Agent**                         | **8 weeks**    |
|   - A. select LLM framework                      | 2 weeks        |
|   - B. implement LLM trading agent               | 4 weeks        |
|   - C. add LLM trading agent to UI               | 2 weeks        |
| **10. Stockie Release 1.0**                      | **6 weeks**    |
|   - A. package stockie software                  | 2 weeks        |
|   - B. write initial documentation set           | 2 weeks        |
|   - C. validate installation instructions        | 2 weeks        |
| **Contingency**                                  | **6 weeks**    |
| **Total**                                        | **60 weeks**   |

The following table maps the investment module work breakdown structure to a rough timeline. Progress will be reported quarterly and the timeline will be reviewed on a quarterly basis as well. Adjustments will be made to the timeline and work breakdown structure based upon the experience gained during the previous quarter. This will allow new insights and ideas to be incorporated into the overall plan. 

| Timeline | WBS         |
|----------|-------------|
| Q1 2026  | 1 - 3       |
| Q2 2026  | 4 - 5       |
| Q3 2026  | 6 - 7       |
| Q4 2026  | 7 - 8       |
| Q1 2027  | 9 - 10      |
| Q2 2027  | Contingency |

Please note: 
(1) The table should be read that by end Q1 2026, WBS 1 - 3 will be completed and so on. 
(2) The above work breakdown structure does not yet deal with the implementation of a trading algo library. This will be incorporated as we go along and implemented as part of the contingency if possible. 
(3) The upgrading the technology stack as newer versions come available will be done at various points in the timeline to ensure the technology stack we use is up to date and leverages the latest available versions. For example, Postgres 18.1 is available but we are currently still using Postgres 17 as the development platform and in production. 
(4) The above WBS does not address building a job monitoring system to ensure jobs are running as planned without issues. That will be added over time as we gain a better understanding of how the actual jobs look and how best to monitor them proactively and minimize manual monitoring. 
(5) As we gain experience with running the system, we also need to work out how to implement a backup and recovery strategy. A lot of the data can be reloaded from sources, but parts will need to be protected to ensure no loss of data over time.

---

# 🗺️ **Personal Finance Suite Expansion Roadmap**

## **Post-Investment Module Development (2027-2032)**

> **Note**: This roadmap represents our envisioned direction for expanding Stockie into a comprehensive personal financial management suite over the next 5-10 years. Module priorities, features, and timeline may evolve based on community feedback, user needs, market demands, and development experiences. We welcome input from users or contributors on which modules should be prioritized next.

**Budgeting & Expense Module (Envisioned 2027 - 2028):**
- Bank account integration and transaction categorization
- Automated expense tracking and budget creation
- Spending pattern analysis and optimization recommendations
- Integration with investment data for complete financial picture

**Tax Optimization Module (Envisioned 2028-2029):**
- Tax document management and organization
- Automated deduction tracking and optimization
- Integration with investment data for capital gains/losses
- Tax planning strategies and projection tools

**Retirement Planning Module (Envisioned 2029-2030):**
- 401k/IRA account integration and analysis
- Retirement savings optimization recommendations
- Social Security and pension planning integration
- Monte Carlo simulations for retirement scenarios

**Banking & Cash Management Module (Envisioned 2030-2031):**
- Multi-bank account aggregation
- Cash flow analysis and forecasting
- Automated savings and transfer optimization
- Emergency fund and liquidity management

**Insurance & Risk Module (Envisioned 2031-2032):**
- Insurance policy tracking and analysis
- Coverage gap identification and recommendations
- Premium optimization across all insurance types
- Integration with investment risk assessment

**Financial Wellness Dashboard (Envisioned 2032-2033):**
- Unified financial health scoring
- Goal tracking across all financial domains
- Automated financial coaching and recommendations
- Complete personal financial ecosystem integration

---

# 🛠️ **Technology Stack**

## **Frontend**
- **Qt 6.10** with C++ - Professional native desktop UI
- **QtCharts** - Financial charting with dual y-axes
- **QtWidgets** - Traditional desktop interface components

## **Backend Services**
- **C++ 20** - High-performance microservices
- **gRPC/HTTP** - Service communication protocols
- **Boost 1.83.0** - Inter-process communication and utilities

## **Data Pipeline**
- **Python 3.14+** - ETL processes and data management
- **Pandas/NumPy** - Data processing and analysis
- **SciPy/CVXPY** - Quadratic programming and portfolio optimization
- **Requests/BeautifulSoup** - Web scraping and API integration

## **Database**
- **PostgreSQL 17+** - Primary data storage
- **Compression** - gzip for SEC filing storage
- **Indexing** - Optimized for time-series and text queries

## **Development Platform**
- **Linux (Ubuntu)** - Primary development and testing environment
- **MacOS** - First future support validation target
- **Windows (WSL)** - Second future validation and testing target
- **Cross-platform Qt** - Ensures consistent UI across platforms

### **Development Tools**
- **CMake** - C++ build system
- **Poetry** - Python dependency management
- **pytest** - Python testing framework
- **Git** - Version control and collaboration

NB: If CMake turns out to be more effort than it's worth, we will revert to plain vanilla Makefiles to keep things simple and moving forward.

---

## 📈 **Success Criteria**

Below are the success metrics by which we will judge the performance and functionality of Stockie 1.0. These criteria will be refined and updated as we build components of the investment module.

### **Performance Targets**
- **Chart loading**: <2 seconds for 5-year data
- **Service response**: <100ms for cached data
- **Filing processing**: <30 seconds per document
- **Memory usage**: <4GB for typical operation

### **Data Coverage Goals**
- **Stock data**: 8,000+ tickers with 20+ years history
- **Cryptocurrency data**: 500+ crypto assets with full historical data
- **SEC filings**: 3,500+ companies with current and historical filings
- **News coverage**: free financial news sources with regular scraping (e.g. hourly)
- **AI summaries**: 95%+ of filings and news processed within 24 hours
- **Technical indicators**: 20+ indicators calculated daily for stocks and crypto
- **Sentiment analysis**: Real-time sentiment tracking for supported companies

### **User Experience Goals**
- **Professional appearance**: Close as possible to commercial platforms
- **Responsiveness**: Interactive UI updates without blocking
- **Flexibility**: Scalable from laptop to multi-server deployment

---