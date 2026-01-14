List of know issues and limitations that need to be addressed over time:

## 0001 - Dynamically download list of Russell 2000 tickers

Date entered: 2025-06-25
Priority:     nice to have
Date solved:  n/a
Author:       Frank Kornet

I have yet to find a way to download full list of Russell 2000 constituent tickers dynamically from the Internet without having to pay for it. This is something to figure out over time. For now, we have a big enough initial set of unique stock tickers to work with. Once we figure this out, we can implement the solution in Tickers class (file tickers.py).

## 0002 - Daily Job Bulk Replace Strategy

Date entered: 2026-01-13
Priority:     Low - by design
Date solved:  n/a
Author:       Frank Kornet

The daily job uses a bulk replace strategy with atomic table swap (WBS-1A). If the job fails after Phase 4 (atomic swap), old data is permanently lost. However, all data can be re-downloaded from yfinance by simply rerunning the daily job. Temp tables are preserved on failure for debugging.
