# portfolio_tracking_public

This is the public version of portfolio_tracking.

Current problem: shorting equity might not work; no margin stuff; no crpto (can add in modify files); doesn't work with MTA.

Supported platform: Robinhood

To use, you need to add the following files:
  RBHD_USERNM.txt: robinhood username;
  RBHD_PSWD.txt: robinhood password;
  finnhub_token.txt: api token from finnhub;
  tradier_token.txt: api token from tradier developer (sanbox)
  
After adding the required data, run service.py for report.

You can manually modify the portfolio and orders through changing the csv files.
