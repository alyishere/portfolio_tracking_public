import requests
import pandas as pd
import time
from datetime import datetime
from datetime import timezone

def gather_current_quote(orders):
    token = open('tradier_token.txt','r').read()
    ticker_list = orders.groupby('Ticker').min()['Date'].index.tolist()
    ticker_str = ""
    for i in ticker_list:
        ticker_str = ticker_str + "," + i 
        if len(i) > 10:
            ticker_str = ticker_str + "," + i[:-15] 
    ticker_str = ticker_str[1:]

    response = requests.get('https://sandbox.tradier.com/v1/markets/quotes',
        params={'symbols': ticker_str, 'greeks': 'false'},
        headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json'}
    )
    json_response = response.json()

    #need optimization here. Duplicating quotes.
    return pd.DataFrame(json_response['quotes']['quote'])[['symbol','last']].rename({'symbol':'Ticker','last':'current_quote'},axis = 1).drop_duplicates() 

def gather_historical_quote(orders):
    holding_table = pd.DataFrame(orders.groupby('Ticker').min()['Date']).reset_index()
    holding_table_copy = holding_table.copy()
    holding_table_copy = holding_table_copy[holding_table_copy['Ticker'].str.len()>10]
    holding_table_copy['Ticker'] = holding_table_copy['Ticker'].apply(lambda option: option[:-15])
    holding_table_copy = pd.DataFrame(holding_table_copy.groupby('Ticker').min()['Date']).reset_index()
    holding_table = pd.concat([holding_table,holding_table_copy]).drop_duplicates().reset_index().drop('index',axis = 1)
    holding_table = pd.DataFrame(holding_table.groupby('Ticker').min()['Date']).reset_index()
    end_date = datetime.today().strftime("%Y-%m-%d")
    token = open('tradier_token.txt','r').read()
    def request_historicals(ticker,day1):
        start_date = day1.strftime("%Y-%m-%d")
        response = requests.get('https://sandbox.tradier.com/v1/markets/history',
            params={'symbol': ticker, 'interval': 'daily', 'start': start_date, 'end': end_date},
            headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json'}
        )
        json_response = response.json()
        return json_response['history']['day']
    holding_table['historical_quote'] = holding_table.apply(lambda ticker: request_historicals(ticker['Ticker'],ticker['Date']),axis = 1)
    return holding_table
    
def return_all_quotes(orders):
    return pd.merge(gather_historical_quote(orders),gather_current_quote(orders),on = 'Ticker',how = "outer").fillna(0).set_index('Ticker').reset_index()

def generate_price_table(df):
    import pandas as pd
    price_table = pd.DataFrame(columns=("ticker","open","high","low","close","volume"))
    for i in df.index:
        entry = df.loc[i,:]
        current_df = pd.DataFrame(entry['historical_quote'])
        current_df['ticker'] = entry['Ticker']
        price_table = pd.concat([price_table,current_df])
    return price_table