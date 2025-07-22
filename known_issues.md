List of know issues and limitations that need to be addressed over time:

## 0001 - Dynamically download list of Russell 2000 tickers

Date entered: 2025-06-25
Priority:     nice to have
Date solved:  n/a
Author:       Frank Kornet

I have yet to find a way to download full list of Russell 2000 constituent tickers dynamically from the Internet without having to pay for it. This is something to figure out over time. For now, we have a big enough initial set of unique stock tickers to work with. Once we figure this out, we can implement the solution in Tickers class (file tickers.py).


## 0002 - Annualization is hard-coded in the technical indicator classes

The technical indicators have logic to annualize and dailyize the technical indicators. At the moment this is hard-coded using the value of 252. This is a bad design and really should be part of the technical indicators base class. That way the client has control over the period that they want to "annualize". It could be shorter or longer. The default is to annualize using 252 days per trading year. Change to be implemented once the technical indicators have been implemented and the calculate indicators confirmed to be working.
