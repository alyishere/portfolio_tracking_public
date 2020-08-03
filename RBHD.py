import requests
import time
start_time = time.time()

wait_time = 1
total_wait_time = 0
def new_wait():
    global wait_time
    global total_wait_time
    time.sleep(wait_time)
    total_wait_time = total_wait_time + wait_time 

import pandas as pd
import matplotlib as plt
from datetime import datetime
from datetime import timezone
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen
import json
import os

import warnings
warnings.filterwarnings('ignore')

def rbhd_login():
    username = ''
    password = ''

    username = open('RBHD_USERNM.txt','r').read()
    password = open('RBHD_PSWD.txt','r').read()

    header = {"Accept": "application/json"}
    data = {"client_id": "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS",
            "expires_in": 86400,
            "grant_type": "password",
            "password": password,
            "scope": "internal",
            "username": username,
            "device_token":"0af4d874-eed1-4018-9193-5ee4c4206220",
            "challenge_type": "sms", ##not used I think
    }

    url = "https://api.robinhood.com/oauth2/token/"
    r = requests.post(url, data=data, headers=header)
    return "Bearer " + json.loads(r.text)['access_token']

def rbhd_get_orders(rbhd_token):
    header = {"Accept": "application/json",
            "Authorization": rbhd_token
    }
    url = "https://api.robinhood.com/orders/"
    r = requests.get(url, headers=header)

    header2 = {"Accept": "application/json",
            "Authorization":rbhd_token
    }
    url = "https://api.robinhood.com/options/orders/"
    r2 = requests.get(url, headers=header2)
    return {'equity':json.loads(r.text),'option':json.loads(r2.text)}

def rbhd_get_dividends(rbhd_token):
    header = {"Accept": "application/json",
            "Authorization": rbhd_token
    }
    url = "https://api.robinhood.com/dividends/"
    r = requests.get(url, headers=header)

    return json.loads(r.text)

def getData(url):
    def get_jsonparsed_data(url):
        response = urlopen(url)
        data = response.read().decode("utf-8")
        return json.loads(data)
    return (get_jsonparsed_data(url)) 

def rbhd_format_equity_orders(equity_orders):
        transaction_history = pd.DataFrame(columns=['Ticker','Date','Price/Share','Share'])
        for i in equity_orders["results"]:
                if i['state'] == "filled":
                        action = i["side"]
                        ticker = getData(i["instrument"])["symbol"]
                        price_per_share = i["executions"][0]["price"]
                        quantity = float(i["executions"][0]["quantity"])
                        date = i["executions"][0]["timestamp"]#[0:10] come back to this if date is having problems. This will remove hour and minute from equity transaction time. 
                        transaction_history = transaction_history.append(pd.Series({"Ticker":ticker,
                        "Date":date,
                        "Price/Share":price_per_share,
                        "Share":float(quantity),
                        "Transaction_Type": action.upper()
                        }),ignore_index=True)
        transaction_history['Date'] = transaction_history['Date'].astype('datetime64[ns]') 
        transaction_history['Price/Share'] = transaction_history['Price/Share'].astype('float')
        # transaction_history['Transaction_Type'] = "BUY"
        # transaction_history[transaction_history['Share']<0]['Transaction_Type'] = "SELL"
        # transaction_history[transaction_history['Share']<0]['Share'] =  - transaction_history[transaction_history['Share']<0]['Share']
        transaction_history['Transaction_Amount'] = transaction_history['Price/Share'] * transaction_history['Share'] 
        
        return transaction_history 

def rbhd_format_option_orders(option_orders):
    transaction_history_option = pd.DataFrame(columns=['Ticker','Date','Price/Share','Share'])
    for i in option_orders["results"]:
        if i['state'] == "filled":
            underlying_ticker = i["chain_symbol"]
            for j in i['legs']:
                instrument = getData(j['option'])
                instrument_type = instrument['type']
                instrument_K = instrument['strike_price']
                instrument_expiration_date = instrument['expiration_date']
                side = j['side']

                for e in j['executions']:
                    date = e['timestamp'] 
                    quantity = e['quantity'] 
                    price = e['price']
                    option_ticker = underlying_ticker + instrument_expiration_date.replace("-","")[-6:] + instrument_type[0].upper() + str(int(float(instrument_K) * 1000)+100000000)[1:]

                    transaction_history_option = transaction_history_option.append(pd.Series({"Ticker":option_ticker,
                            "Date":date,
                            "Price/Share": float(price)*100 ,
                            "Share":float(quantity),
                            "Transaction_Type": side.upper()
                            }),ignore_index=True)

    transaction_history_option['Date'] = transaction_history_option['Date'].astype('datetime64[ns]') 
    transaction_history_option['Transaction_Amount'] = transaction_history_option['Price/Share'] * transaction_history_option['Share']
    return transaction_history_option

def rbhd_login_and_gather():
    rbhd_token = rbhd_login()
    rbhd_orders = rbhd_get_orders(rbhd_token)

    rbhd_equity_orders = (rbhd_format_equity_orders(rbhd_orders['equity']))
    rbhd_equity_orders['Instrument_Type'] = "Equity"
    rbhd_option_orders = (rbhd_format_option_orders(rbhd_orders['option']))
    rbhd_option_orders['Instrument_Type'] = "Option"

    rbhd_dividends = pd.DataFrame(rbhd_get_dividends(rbhd_token)['results'])
    rbhd_dividends["Ticker"] = rbhd_dividends.apply(lambda stock: getData(stock["instrument"])["symbol"], axis = 1)
    rbhd_dividends["amount"] = rbhd_dividends["amount"].astype('float')
    rbhd_dividends["paid_at"] = rbhd_dividends["paid_at"].astype('datetime64[ns]') 

    return {'orders':pd.concat([rbhd_equity_orders,rbhd_option_orders]),'dividends':rbhd_dividends[['Ticker','amount','paid_at','state']]}

def getRBHDAccountInfo():
    import json
    rbhd_token = rbhd_login()
    header = {"Accept": "application/json",
            "Authorization":rbhd_token
    }
    url = "https://api.robinhood.com/accounts/"
    r = requests.get(url, headers=header)
    return json.loads(r.text)

def getRBHDCash():
    info = getRBHDAccountInfo()
    return float(info['results'][0]['portfolio_cash'])

def getPortfolioPositions():
        token = rbhd_login()
        account_number = getRBHDAccountInfo()['results'][0]['account_number']
        header = {"Accept": "application/json",
                "Authorization": token
        }
        url = "https://api.robinhood.com/portfolios/historicals/" + account_number + "/?account=" + account_number + "&bounds=regular&interval=&span=all"
        r = requests.get(url, headers=header)
        portfolioPositionsDF = pd.DataFrame(json.loads(r.text)['equity_historicals'])
        portfolioPositionsDF['close_equity'] = portfolioPositionsDF['close_equity'].astype('float')
        portfolioPositionsDF['adjusted_close_equity'] = portfolioPositionsDF['adjusted_close_equity'].astype('float')
        portfolioPositionsDF['previous_adjusted_close_equity'] = portfolioPositionsDF['adjusted_close_equity'].shift(1)
        portfolioPositionsDF['daily_return_$'] = portfolioPositionsDF['adjusted_close_equity']-portfolioPositionsDF['previous_adjusted_close_equity']
        portfolioPositionsDF['previous_close_equity'] = portfolioPositionsDF['close_equity']-portfolioPositionsDF['daily_return_$']
        portfolioPositionsDF['daily_return_%'] = portfolioPositionsDF['daily_return_$']/portfolioPositionsDF['previous_close_equity']
        portfolioPositionsDF['total_return_$'] = portfolioPositionsDF['daily_return_$'].cumsum()
        portfolioPositionsDF['fund_$'] =  portfolioPositionsDF['close_equity'] - portfolioPositionsDF['total_return_$'] 
        portfolioPositionsDF.to_csv('historical_position.csv')
        return portfolioPositionsDF

def monthly_return_RBHD():
    positions = getPortfolioPositions()
    from pandas.tseries.offsets import MonthEnd
    positions['Date'] = (pd.to_datetime(positions['begins_at'], format="%Y%m%")).dt.date
    positions['Month_End'] = positions['Date'].apply(lambda date: (date+MonthEnd(0)).strftime("%Y-%m-%d"))
    positions['daily_return_%+1'] = positions['daily_return_%'] +1
    positions['MTD_perf'] = (positions.groupby('Month_End')['daily_return_%+1'].cumprod()-1)*100
    ## MTD_perf is calculated by compounding daily. This is not usually used due to large capital inflow/outflow
    result_table = pd.merge(positions.groupby('Month_End').tail(1),positions.groupby('Month_End')['daily_return_$'].sum(),left_on="Month_End",right_on="Month_End")[['Month_End','close_equity','fund_$','close_market_value','daily_return_$_y','MTD_perf']]
    result_table['close_market_value'] = result_table['close_market_value'].astype('float') 
    result_table['Cash'] = result_table['close_equity'] - result_table['close_market_value']
    result_table['Previous_Commitment'] = result_table['fund_$'].shift(1)
    result_table.fillna(0, inplace=True)
    result_table['Capital_Flow'] = result_table['fund_$'] - result_table['Previous_Commitment']
    result_table['Monthly_Performance'] = 100*result_table['daily_return_$_y']/(result_table['close_equity']-result_table['daily_return_$_y'])
    
    result = result_table[['Month_End','close_equity','fund_$','Capital_Flow','Cash','daily_return_$_y','Monthly_Performance']].rename({'close_equity':'NAV','fund_$':'Contributed_Capital','daily_return_$_y':'PnL'},axis=1)
    result.to_csv('monthly_return.csv')
    
    return result
