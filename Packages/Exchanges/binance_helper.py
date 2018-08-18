'''
Using the package from
https://github.com/sammchardy/python-binance
'''

import pandas as pd

def instantiate_api_object(public_key, private_key):
    '''
    :param public_key:
    :param private_key:
    :return: api object
    '''
    from binance.client import Client as api_object
    return api_object(public_key, private_key)

def get_exchange_df(api_object):
    '''
    :param api_object: binance api object
    :return: pandas dataframe with index ticker (string) and
    columns price(float), market(string, market form TICKERBTC), balance(float, amount available)
    '''
    exchange_df = pd.DataFrame(api_object.get_account()['balances'])
    price_df = pd.DataFrame(api_object.get_all_tickers())
    #create future row for exchange_df
    BTC_row = {'price': 1, 'symbol': 'BTCBTC', 'ticker':'BTC'}
    BTC_row['free'] = exchange_df.loc[exchange_df.asset == 'BTC', 'free'].values[0]
    BTC_row['locked'] = exchange_df.loc[exchange_df.asset == 'BTC', 'locked'].values[0]
    #tease out the ticker from the symbol
    price_df['ticker'] = price_df.symbol.apply(lambda x: x.split('BTC')[0])
    # drop non BTC Markets
    price_df = price_df.loc[price_df.ticker != price_df.symbol].copy()
    #merge the two dataframes
    exchange_df = price_df.merge(exchange_df, how='left', left_on='ticker', right_on='asset')
    #append the BTC Row
    exchange_df = exchange_df.append(BTC_row, ignore_index=True)
    #rename columns
    exchange_df[['market', 'balance']] = exchange_df[['symbol', 'free']]
    #drop the unecessary asset column
    exchange_df = exchange_df[['price', 'market','ticker', 'balance']].copy()
    # exchange_df.drop(['asset', 'locked','symbol', 'free'], axis=1, inplace=True)
    #any missing balance, make 0
    exchange_df.fillna(0, inplace=True)
    #fix the types
    exchange_df.balance = exchange_df.balance.astype(float)
    exchange_df.price = exchange_df.price.astype(float)
    #set the ticker as the index
    exchange_df.set_index('ticker', inplace=True)
    return exchange_df

def execute_trades(api_object,trade_df):
    '''
    :param api_object: binance api object
    param trade_df: pandas DataFrame with index ticker, columns Market (string), price(float, in BTC),
        Curr_Dist(float, [0,1]), Target_Dist(float,[0,1]),Trade_Perc(float,[-1,1]), Trade_Amt (in BTC,float),
        Trade_Amt_Coin (float, in the target currency)
    '''
    for coin,row in trade_df.iterrows():
        try:
            #close any open orders
            open_orders = api_object.get_open_orders(symbol=row.market)
            market = row.market
            #Binance only allows certain order sizes by coin
            trade_amt = round(row.Trade_Amt_Coin, 6)
            buy = bool(trade_amt > 0)
            sell = bool(trade_amt < 0)
            trade_amt = abs(trade_amt)
            #filter to make sure in tick size increments above min trade size
            market_lot_size_info = api_object.get_symbol_info(market)['filters'][1]
            trade_amt -= (trade_amt - float(market_lot_size_info['minQty']))%float(market_lot_size_info['stepSize'])
            if trade_amt <= 0:
                continue
            if open_orders:
                print('Cancelling open orders for {}.'.format(coin))
                for order in open_orders:
                    api_object.cancel_order(symbol=market, orderId=order['orderId'])
            if buy:
                print('Buying {} of {}'.format(trade_amt, coin))
                print(api_object.order_market_buy(symbol=market,quantity=trade_amt))
            elif sell:
                print('Selling {} of {}'.format(trade_amt, coin))
                print(api_object.order_market_sell(symbol=market,quantity=trade_amt))
        except Exception as e:
            print(e)
