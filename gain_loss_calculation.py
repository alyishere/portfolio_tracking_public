import pandas as pd
import RBHD
import warnings
warnings.filterwarnings('ignore')

all_transaction = pd.read_csv("all_transactions.csv").drop("Unnamed: 0",axis = 1)
all_transaction['Date'] = all_transaction['Date'].astype('datetime64[ns]')
all_quote = pd.read_csv("all_quote_cache.csv")

portfolio_view1 = all_transaction.groupby('Ticker').min()[['Date','Instrument_Type']]
portfolio_view1['Share'] = 0.0
portfolio_view1['Cumulative Cost'] = 0.0
portfolio_view1['Realized Gain/Loss'] = 0.0
portfolio_view1['Unrealized Gain/Loss'] = 0.0
portfolio_view1['Total Gain/Loss'] = 0.0
portfolio_view1 = portfolio_view1.drop('Date',axis = 1)

price_table = pd.read_csv("price_table_cache.csv")
price_table['date'] = price_table['date'].astype('datetime64[ns]')
price_table["pc"] = price_table.sort_values('date').groupby('ticker')['close'].shift(1)
price_table['t_str'] = price_table.apply(lambda entry: entry['date'].strftime("%Y-%m-%d"), axis = 1)

def calculate_gain_loss(ticker):
    current_ticker = ticker
    current_ticker_history = all_transaction[all_transaction['Ticker']==current_ticker]
    share = 0.0
    cumulative_cost = 0.0
    realized_gain_loss = 0.0
    unrealized_gain_loss = 0.0
    total_gain_loss = 0.0
    current_instrument_type = portfolio_view1.loc[current_ticker,'Instrument_Type']

    if current_instrument_type == 'Equity':
        for i in current_ticker_history.index:
            current_transaction_type = current_ticker_history.loc[i,'Transaction_Type']
            if current_transaction_type == "BUY":
                cumulative_cost = cumulative_cost + current_ticker_history.loc[i,'Transaction_Amount']
                share = share + current_ticker_history.loc[i,'Share']
            elif current_transaction_type =="SELL":
                realized_gain_loss = realized_gain_loss + current_ticker_history.loc[i,'Transaction_Amount'] - cumulative_cost * current_ticker_history.loc[i,'Share']/share
                cumulative_cost = cumulative_cost * ((share - current_ticker_history.loc[i,'Share'])/share)
                share = share - current_ticker_history.loc[i,'Share']
            elif current_transaction_type =="SPLIT":
                share = share*current_ticker_history.loc[i,'Split_Factor']
                fractional_share = share - float(int(share))
                split_day = current_ticker_history.loc[i,'Date'].strftime("%Y-%m-%d")
                pc_price = float(price_table[price_table['ticker'] ==current_ticker][price_table['t_str'] == split_day]['pc'])
                realized_gain_loss = realized_gain_loss + fractional_share * pc_price - cumulative_cost * fractional_share/share
                cumulative_cost = cumulative_cost * ((share - fractional_share)/share)
                share = float(int(share))
            elif current_transaction_type =="DIVIDEND":
                realized_gain_loss = realized_gain_loss + current_ticker_history.loc[i,'Transaction_Amount']
    
    elif current_instrument_type == 'Option':
        K = float(current_ticker[-8:])/1000
        option_type = current_ticker[-9]
        for i in current_ticker_history.index:
            current_transaction_type = current_ticker_history.loc[i,'Transaction_Type']
            if current_transaction_type == "BUY":
                if share < 0:
                    realized_gain_loss = realized_gain_loss - current_ticker_history.loc[i,'Transaction_Amount'] + cumulative_cost * current_ticker_history.loc[i,'Share']/share
                    cumulative_cost = cumulative_cost * ((share + current_ticker_history.loc[i,'Share'])/share)
                    share = share + current_ticker_history.loc[i,'Share']
                else:    
                    cumulative_cost = cumulative_cost + current_ticker_history.loc[i,'Transaction_Amount']
                    share = share + current_ticker_history.loc[i,'Share']
            elif current_transaction_type =="SELL":
                if share == 0:
                    cumulative_cost = cumulative_cost - current_ticker_history.loc[i,'Transaction_Amount']
                    share = share - current_ticker_history.loc[i,'Share'] 
                else:
                    realized_gain_loss = realized_gain_loss + current_ticker_history.loc[i,'Transaction_Amount'] - cumulative_cost * current_ticker_history.loc[i,'Share']/share
                    cumulative_cost = cumulative_cost * ((share - current_ticker_history.loc[i,'Share'])/share)
                    share = share - current_ticker_history.loc[i,'Share']
            elif current_transaction_type =="SPLIT":
                share = share*current_ticker_history.loc[i,'Split_Factor']
                K = K/current_ticker_history.loc[i,'Split_Factor']
            elif current_transaction_type =="EXPIRE":
                valueOfOption = 0
                expire_underlying_price = get_exp_price_for_option(current_ticker)
                if option_type == "C":
                    valueOfOption = (expire_underlying_price - K) * share * 100
                elif option_type == "P":
                    valueOfOption = (K - expire_underlying_price) * share * 100
                if share > 0:
                    if valueOfOption < 0:
                        valueOfOption = 0
                elif share < 0:
                    if valueOfOption > 0:
                        valueOfOption = 0
                realized_gain_loss = realized_gain_loss + valueOfOption - cumulative_cost
                cumulative_cost = 0.0
                share = 0.0
    if share == 0:
        unrealized_gain_loss = 0
    else:
        unrealized_gain_loss = float(all_quote[all_quote['Ticker']==current_ticker]['current_quote'] * share - cumulative_cost)
        if current_instrument_type == 'Option':
            unrealized_gain_loss = float(all_quote[all_quote['Ticker']==current_ticker]['current_quote'] * share * 100 - cumulative_cost)
    total_gain_loss = realized_gain_loss + unrealized_gain_loss

    return [share,cumulative_cost,realized_gain_loss,unrealized_gain_loss,total_gain_loss]

def get_exp_price_for_option(Ticker):
    import pandas as pd
    underlying = Ticker[:-15]
    expiration = '20'+ Ticker[-15:-13] +'-'+ Ticker[-13:-11] +'-'+ Ticker[-11:-9]
    df = pd.read_csv('price_table_cache.csv')
    result = float(df.query('ticker==@underlying and date==@expiration')['close'])
    return result

for i in portfolio_view1.index:
    current_ticker = i
    figures = calculate_gain_loss(current_ticker)
    portfolio_view1.loc[i,'Share'] = figures[0]
    portfolio_view1.loc[i,'Cumulative Cost'] = figures[1]
    portfolio_view1.loc[i,'Realized Gain/Loss'] = figures[2]
    portfolio_view1.loc[i,'Unrealized Gain/Loss'] = figures[3]
    portfolio_view1.loc[i,'Total Gain/Loss'] = figures[4]

portfolio_view1 = pd.merge(portfolio_view1,all_quote.set_index('Ticker'),how = 'left',left_index=True, right_index=True) 
portfolio_view1['Market Equity'] = portfolio_view1['current_quote'] * portfolio_view1['Share']
for i in portfolio_view1[portfolio_view1['Instrument_Type']=='Option'].index:
    portfolio_view1.loc[i,"Market Equity"] = portfolio_view1.loc[i,"Market Equity"]*100
portfolio_view1 = portfolio_view1.drop(['Unnamed: 0','Date','historical_quote'],axis = 1).sort_values('Market Equity',ascending = False).reset_index()

portfolio_view1 = pd.concat([portfolio_view1,pd.read_csv('gain_loss_modify.csv')])
portfolio_view1 = portfolio_view1.append(pd.Series({
    'Ticker':"CASH",
    'Instrument_Type':"CASH",
    'Market Equity':RBHD.getRBHDCash(),
}),ignore_index=True)

portfolio_view1['Weight'] = 100*round(portfolio_view1['Market Equity'],2)/round(portfolio_view1['Market Equity'].sum(),2)
portfolio_view1 = portfolio_view1.sort_values('Market Equity',ascending = False).reset_index().drop('index',axis =1)
print(portfolio_view1)
portfolio_view1.to_csv('portfolio.csv')
print("Called Capital  \t" + str(portfolio_view1['Market Equity'].sum()-portfolio_view1['Total Gain/Loss'].sum()))
print(portfolio_view1[['Realized Gain/Loss','Unrealized Gain/Loss','Total Gain/Loss','Market Equity']].sum())
