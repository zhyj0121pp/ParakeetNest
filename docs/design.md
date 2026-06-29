Project ParakeetNest

AI Investment Research Platform

Tagline

Three Parakeets. One Committee. Better Investment Decisions.

⸻

1. Vision

Background

Successful investing is not about predicting stock prices.

It is about continuously gathering evidence, challenging assumptions, managing risks, and updating investment theses as new information becomes available.

Professional investment firms achieve this through daily discussions among specialists with different perspectives.

Project ParakeetNest aims to bring this process into an AI-powered investment research platform.

Instead of replacing investors, ParakeetNest acts as an AI Investment Committee that continuously researches, debates, remembers, and learns to support better long-term investment decisions.

⸻

2. Mission

Build an AI Investment Committee that continuously learns, debates, remembers, and improves—helping investors make evidence-based long-term investment decisions rather than reacting to daily market noise.

⸻

3. Guiding Principles

Every investment decision follows these principles.

Long-term over short-term

Focus on business quality instead of daily price movement.

Evidence over emotion

Every conclusion must be supported by data.

Thesis before price

Understand why a company should be owned before evaluating its stock price.

Risk before return

Avoid permanent capital loss before pursuing exceptional returns.

Remember before reasoning

Every discussion begins by reviewing historical investment theses before analyzing new information.

Continuous learning

Every recommendation becomes future knowledge.

Respect uncertainty

Confidence is never certainty.

Every recommendation includes confidence and supporting evidence.

⸻

4. High Level Architecture

                    Scheduler
                        │
                        ▼
              AI Investment Committee
                        │
      ┌────────────────────────────────┐
      │                                │
      ▼                                ▼
 Data Collection Layer         Committee Engine
      │                                │
      ▼                                ▼
 Historical Database        Investment Knowledge Base
      │                                │
      └──────────────┬─────────────────┘
                     │
                     ▼
              Decision Engine
                     │
                     ▼
             Report Generator
                     │
                     ▼
              Email / Future UI

⸻

5. Investment Committee

The committee simulates a professional investment firm’s daily investment meeting.

Chairman

Responsibilities

* Lead committee discussion
* Balance different viewpoints
* Produce final recommendations
* Ensure evidence-based decisions

The Chairman never invents unsupported conclusions.

⸻

Xixi

Chief Fundamental Analyst

Personality

* Gentle
* Calm
* Emotionally stable
* Long-term thinker

Responsibilities

Evaluate

* Business quality
* Competitive advantage
* Management
* Financial health
* Earnings quality
* Long-term growth
* AI ecosystem positioning

Primary Question

Is this a business worth owning for many years?

⸻

Dongdong

Chief Opportunity Hunter

Personality

* Curious
* Bold
* Energetic
* Loves discovering hidden opportunities

Responsibilities

Focus on

* Emerging AI trends
* Semiconductor innovation
* Small-cap opportunities
* Technology breakthroughs
* Market rotation
* Growth catalysts

Primary Question

What opportunity is the market missing?

⸻

Yoyo

Chief Risk Officer

Personality

* Careful
* Independent
* Conservative
* Excellent observer

Responsibilities

Evaluate

* Valuation
* Concentration risk
* Earnings risk
* Liquidity
* Macro uncertainty
* Downside scenarios

Primary Question

What could go wrong?

⸻

Investment Secretary

The secretary never gives investment opinions.

Responsibilities

Maintain committee memory.

Track

* Historical discussions
* Investment thesis
* Decision history
* Recommendation history
* Catalyst history
* Lessons learned
* Committee accuracy

⸻

6. Data Collection Layer

Portfolio Service

Source

* Robinhood

Collect

* Holdings
* Position size
* Cost basis
* Cash balance
* Unrealized P/L

⸻

Market Data Service

Source

* Yahoo Finance

Collect

* Price
* Daily change
* Volume
* Market cap
* PE
* EPS
* 52-week range

⸻

News Service

Source

* Yahoo Finance News

Collect

* Company news
* Industry news
* AI news
* Semiconductor news

⸻

Financial Service

Source

* Yahoo Finance

Collect

* Revenue
* EPS
* Guidance
* Margins
* Cash flow
* Balance sheet

⸻

Macro Service

Source

* FRED

Collect

* Federal Funds Rate
* Treasury Yield
* CPI
* Inflation
* Employment

⸻

Calendar Service

Collect

* Earnings calendar
* Dividend calendar
* FOMC meetings
* CPI releases
* Major AI conferences

⸻

7. Data Quality Layer

Every dataset includes

* Source
* Fetch time
* Freshness
* Validation status
* Missing fields
* Confidence score

Analysis services never consume unvalidated data.

⸻

8. Historical Database

SQLite (v1)

Stores immutable historical facts.

Tables

* holdings
* market_data
* financials
* macro
* calendar
* news
* reports

Historical Database stores facts.

⸻

9. Investment Knowledge Base

The Knowledge Base stores accumulated investment knowledge rather than raw market data.

Objects

* Investment thesis
* Committee discussions
* Research notes
* Lessons learned
* Catalyst history
* Company summaries
* Historical recommendations

Knowledge evolves over time.

⸻

10. Investment Policy Engine

Defines permanent investment rules.

Examples

* Maximum position size
* Maximum sector exposure
* Cash reserve
* Speculative allocation limit
* Options exposure
* Buy criteria
* Reduce criteria

Committee recommendations should always respect these rules.

⸻

11. Analysis Layer

Portfolio Analyzer

Analyze

* Allocation
* Sector exposure
* Concentration
* Correlation
* Drawdown
* Portfolio risk

⸻

Stock Evaluator

Evaluate

* Fundamentals
* Valuation
* Growth
* Competitive positioning
* Earnings
* Financial quality

⸻

Market Watcher

Analyze

* Market trend
* AI trend
* Semiconductor trend
* Interest rates
* Inflation
* Liquidity

⸻

Catalyst Engine

Track

* Earnings
* Guidance
* Product launches
* AI CapEx
* Export controls
* Industry conferences

⸻

Risk Checker

Identify

* Valuation risk
* Concentration risk
* Liquidity risk
* Earnings risk
* Macro risk

⸻

Opportunity Finder

Discover opportunities in

* Artificial Intelligence
* Semiconductor
* Memory
* Silicon Photonics
* Optical Interconnect
* Physical AI
* Robotics
* Power Infrastructure

⸻

Thesis Tracker

For every company maintain

* Why we own it
* Original thesis
* Supporting evidence
* Risks
* Catalysts
* Invalidating conditions

⸻

12. Committee Workflow

Every investment decision follows the same process.

Portfolio
↓
Market Data
↓
Historical Thesis
↓
Xixi Review
↓
Dongdong Review
↓
Yoyo Review
↓
Committee Discussion
↓
Chairman Summary
↓
Final Recommendation
↓
Knowledge Base Update

The committee remembers before it reasons.

⸻

13. Decision Engine

Every recommendation contains

Action

* Buy
* Hold
* Reduce
* Watch

Confidence

* High
* Medium
* Low

Investment Horizon

* 3 Months
* 6 Months
* 1 Year
* 3 Years

Supporting Evidence

Key Risks

Major Catalysts

Data Confidence

⸻

14. Report Service

Daily Report

* Portfolio Summary
* Market Summary
* Committee Discussion
* Position Reviews
* Risk Alerts
* Opportunity Watchlist
* Final Recommendations

⸻

Weekly Report

* Thesis Updates
* Committee Accuracy
* Portfolio Performance
* Lessons Learned

⸻

Monthly Report

* Investment Journal
* Committee Performance
* Knowledge Growth
* Strategy Improvements

⸻

15. Technology Stack

Component	Technology
Language	Python
Scheduler	macOS launchd
Database	SQLite
Portfolio	Robinhood
Market Data	Yahoo Finance
News	Yahoo Finance News
Financial Data	Yahoo Finance
Macro	FRED
LLM	OpenAI GPT API
Email	Gmail API

⸻

16. Future Roadmap

Version 2

* PostgreSQL
* AWS Deployment
* SEC Filing Analysis
* Insider Trading Analysis
* ETF Flow Analysis
* Multiple Data Providers
* Better Data Validation

⸻

Version 3

* Dashboard
* Multi-Broker Support
* Backtesting
* Real-time Monitoring
* Strategy Evaluation
* Portfolio Optimization
* AI Research Assistant
* Plug-in Committee Members

⸻

17. Design Philosophy

Project ParakeetNest is not designed to predict stock prices.

It is designed to continuously build investment knowledge.

Every discussion strengthens the committee.

Every decision becomes future evidence.

Every mistake becomes future experience.

The committee does not chase the market.

It learns from it.

Ultimately, the goal is not to build a better stock picker.

The goal is to build a better long-term investment thinker.
