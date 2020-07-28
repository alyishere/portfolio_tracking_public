import RBHD 
import requests
import pandas as pd
from datetime import datetime
from datetime import timezone
import time

count1 = time.time()

data = RBHD.rbhd_login_and_gather()

orders = data['orders'].sort_values('Date',ascending=False).reset_index().drop('index',axis = 1)

modify_order = pd.read_csv('order_modify.csv')
modify_order['Date'] = modify_order['Date'].astype('datetime64[ns]')

orders = pd.concat([orders,modify_order]).sort_values('Date',ascending=False)

orders.to_csv("orders_cache.csv")
dividends = data['dividends']
dividends.to_csv("dividends_cache.csv")

import Quote_Gatherer

all_quote = Quote_Gatherer.return_all_quotes(orders)
price_table = Quote_Gatherer.generate_price_table(all_quote)

all_quote.to_csv('all_quote_cache.csv')
price_table.to_csv('price_table_cache.csv')

#the following section add in "underlying","split","dividend", and "option expire" items to the orders

def get_underlying(instrument):
    if instrument['Instrument_Type'] == "Option":
        return instrument["Ticker"][:-15]
    else:
        return instrument["Ticker"]

orders['Underlying'] = orders.apply(lambda instrument: get_underlying(instrument),axis = 1)

day1list = pd.DataFrame(orders.groupby('Underlying').min()['Date'])
for i in day1list.index:
    ticker_i = i
    date1 = day1list.loc[i,"Date"].strftime("%Y-%m-%d")
    date2 = datetime.today().strftime("%Y-%m-%d")
    token = open('finnhub_token.txt','r').read()
    r = requests.get('https://finnhub.io/api/v1/stock/split?symbol=' + ticker_i + '&from=' + date1 + "&to=+" + date2 + '&token=' + token)
    
    for j in r.json():
        orders = orders.append(pd.Series({"Ticker":ticker_i,
            "Date":j['date'],
            "Price/Share":0.0,
            "Share":0.0,
            "Transaction_Type":"SPLIT",
            "Transaction_Amount":0.0,
            "Split_Factor":j['toFactor']/j['fromFactor'],
            "Instrument_Type":"Equity",
            "Underlying":ticker_i
        }),ignore_index=True)
orders['Date'] = orders['Date'].astype('datetime64[ns]') 
orders = orders.sort_values("Date").reset_index().drop("index",axis=1)

dividends['amount'] = dividends['amount'].astype('float')
dividends = dividends[dividends['state']=="paid"]
for i in dividends.index:
    div = dividends.loc[i,:]
    orders = orders.append(pd.Series({"Ticker":div['Ticker'],
        "Date":div['paid_at'],
        "Price/Share":0.0,
        "Share":0.0,
        "Transaction_Type":"DIVIDEND",
        "Transaction_Amount":div['amount'],
        "Instrument_Type":"Equity",
        "Underlying":div['Ticker']
    }),ignore_index=True)

today_date = datetime.today()
day1list_option = pd.DataFrame(orders[orders['Instrument_Type']=="Option"].groupby('Ticker').min()['Date'])
for i in day1list_option.index:
    expire_date = datetime.strptime((i[-15:-13] + i[-13:-11] + i[-11:-9] +"1730" ), '%y%m%d%H%M')
    if today_date > expire_date:
        orders = orders.append(pd.Series({"Ticker":i,
            "Date":expire_date,
            "Price/Share":0.0,
            "Share":0.0,
            "Transaction_Type":"EXPIRE",
            "Transaction_Amount":0.0,
            "Instrument_Type":"Option",
            "Underlying":i[0:-15]
        }),ignore_index=True)

orders.sort_values("Date").to_csv("all_transactions.csv")

count2 = time.time()
print("All files have been cached. Spent: " + str(round(count2 - count1,2)) + "s.")