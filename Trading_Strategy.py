import numpy as np
import pandas as pd
import yfinance as yf
import math
import copy
import time


start_time = time.perf_counter()

#Here I define the ATR function that returns the "Average True Range" over a certain period "n"
def ATR(DF,n):
    #function to calculate ATR
    df = DF.copy()
    df["H-L"] = abs(df["High"]-df["Low"])
    df["H-PC"] = abs(df["High"]-df["Close"].shift(1))
    df["L-PC"] = abs(df["Low"]-df["Close"].shift(1))
    df["TR"] = df[["H-L","H-PC","L-PC"]].max(axis=1,skipna = False)
    df["ATR"] = df["TR"].rolling(n).mean()
    df2 = df.drop(["H-L","H-PC","L-PC"],axis = 1)
    return df2["ATR"]

#Here I donwload the data for my stategy
tickers = ["MSFT","AAPL","META","AMZN","INTC","CSCO","VZ","IBM","TSLA","AMD"]
ohlcv_data = {}
for ticker in tickers: 
    ohlcv_data[ticker] = yf.download(ticker, start = "2023-12-01",end = "2024-01-16", interval = "5m")

#Here I calculate the "ATR" for each 5min period and  the "roll_max_cp" and "roll_min_cp" which will serve as stop losses for my strategy
tickers_signal = {}
tickers_ret = {}
for ticker in tickers:
    print(f"calculating ATR and rolling max price for {ticker}")
    ohlcv_data[ticker]["ATR"] = ATR(ohlcv_data[ticker],20)
    ohlcv_data[ticker]["roll_max_cp"] = ohlcv_data[ticker]["High"].rolling(20).max()
    ohlcv_data[ticker]["roll_min_cp"] = ohlcv_data[ticker]["Low"].rolling(20).min()
    ohlcv_data[ticker]["roll_max_vol"] = ohlcv_data[ticker]["Volume"].rolling(20).max()
    ohlcv_data[ticker].dropna(inplace=True)
    tickers_signal[ticker] = ""
    tickers_ret[ticker] = []


#Here I execute my strategy (Buy if close price > roll_max_cp
for ticker in tickers:
    print(f"calculating returns for {ticker}")
    tickers_ret[ticker] = []
    for i in range(len(ohlcv_data[ticker])):
        if tickers_signal[ticker] == "":
            tickers_ret[ticker].append(0)
            if ohlcv_data[ticker]["High"][i] >= ohlcv_data[ticker]["roll_max_cp"][i] and \
            ohlcv_data[ticker]["Volume"][i] >1.5*ohlcv_data[ticker]["roll_max_vol"][i-1]:
                tickers_signal[ticker] = "Buy"
            elif ohlcv_data[ticker]["Low"][i] <= ohlcv_data[ticker]["roll_min_cp"][i] and \
            ohlcv_data[ticker]["Volume"][i] >1.5*ohlcv_data[ticker]["roll_max_vol"][i-1]:
                tickers_signal[ticker] = "Sell"
                
        elif tickers_signal[ticker] == "Buy":
            if ohlcv_data[ticker]["Low"][i] < ohlcv_data[ticker]["Close"][i-1] - ohlcv_data[ticker]["ATR"][i-1]: 
                #this is the Stop Loss for the buy order
                tickers_signal[ticker] = ""
                tickers_ret[ticker].append(((ohlcv_data[ticker]["Close"][i-1] - ohlcv_data[ticker]["ATR"][i-1])/ohlcv_data[ticker]["Close"][i-1])-1)
            elif ohlcv_data[ticker]["Low"][i] <= ohlcv_data[ticker]["roll_min_cp"][i] and \
            ohlcv_data[ticker]["Volume"][i]>1.5*ohlcv_data[ticker]["roll_max_vol"][i-1]:
                #this line of code basically changes the buy order to a sell order (if the conditions happen)
                ticker_signal[ticker] = "Sell"
                tickers_ret[ticker].append((ohlcv_data[ticker]["Close"][i]/ohlcv_data[ticker]["Close"][i-1]/ohlcv_data[ticker]["Close"][i-1])-1)
            else:
                #this line of code assigns the return of each period as long as the signal is buy
                tickers_ret[ticker].append((ohlcv_data[ticker]["Close"][i]/ohlcv_data[ticker]["Close"][i-1]/ohlcv_data[ticker]["Close"][i-1])-1)
        
        elif tickers_signal[ticker]=="Sell":
            if ohlcv_data[ticker]["High"][i] > ohlcv_data[ticker]["Close"][i-1] + ohlcv_data[ticker]["ATR"][i-1]:
                #this is the stop loss for the sell order
                tickers_signal[ticker] = ""
                tickers_ret[ticker].append((ohlcv_data[ticker]["Close"][i-1]/ohlcv_data[ticker]["Close"][i]/ohlcv_data[ticker]["Close"][i])-1)
            elif ohlcv_data[ticker]["High"][i]>= ohlcv_data[ticker]["roll_max_cp"][i] and \
            ohlcv_data[ticker]["Volume"][i]>1.5*ohlcv_data[ticker]["roll_max_vol"][i-1]:
                #this line of code basically changes the sell order into a buy order (if the conditions happen)
                tickers_signal[ticker] = "Buy"
                tickers_ret[ticker].append((ohlcv_data[ticker]["Close"][i-1]/ohlcv_data[ticker]["Close"][i]/ohlcv_data[ticker]["Close"][i])-1)
            else:
                #this line of code assigns the return of each period as long as the signal is sell
                tickers_ret[ticker].append((ohlcv_data[ticker]["Close"][i-1]/ohlcv_data[ticker]["Close"][i]/ohlcv_data[ticker]["Close"][i])-1)
                
    ohlcv_data[ticker]["ret"] = np.array(tickers_ret[ticker])



end_time = time.perf_counter()
total_time = end_time - start_time
print(f"Total execution time: {total_time} seconds")


#Backtesting Results

def CAGR(DF):
    df = DF.copy()
    df["cummulative return"]= (1+df[:][0]).cumprod()
    n = len(df)/(29*78)
    CAGR = (df["cummulative return"][-1])**(1/n)-1
    return CAGR

def volatility(DF, ticker):
    df = DF.copy()
    stock_return = df[ticker]["Adj Close"].pct_change()
    stock_volatility = stock_return.std()*math.sqrt(29*78)
    return  stock_volatility

def sharpe_ratio(DF, rf = 0.03):
    df = DF.copy()
    return  CAGR(df) - rf / volatility(ohlcv_data,ticker)



strategy_ret = {}
for ticker in tickers:
    strategy_ret[ticker] = ohlcv_data[ticker]["ret"]


strategy_ret = pd.DataFrame(strategy_ret)
strategy_ret["ret"] = strategy_ret.mean(axis = 1) #this takes the average return of all the stocks for each period
strategy_ret = pd.DataFrame(strategy_ret)

print(f"The strategy return is {CAGR(strategy_ret["ret"])}")
print(f"The strategy sharpe ratio is {CAGR(sharpe_ratio["ret"])}")

(1+strategy_ret["ret"]).cumprod().plot()


