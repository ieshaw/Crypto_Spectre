import pandas as pd

'''
These are the functions for general admin.
'''

def key_retriever(json_path, key_name, status='ro'):
    '''
    :param json_path:
    :param key_name:
    :param status: either 'ro' or 'live'
    :return: exchange, public, private
    '''
    import json
    import os
    with open(json_path) as secrets_file:
        secrets = json.load(secrets_file)
        secrets_file.close()
    key_dict = secrets[key_name]
    exchange = key_dict['exchange']
    return exchange, key_dict[status]['public'], key_dict[status]['private']

'''
These are the logic functions of planning trades
'''

def expand_exchange_df(exchange_df):
    '''
    :param exchange_df: pandas dataframe with columns price(float), market(string, market form TICKERBTC),
        ticker(string), balance(float, amount available)
    :return: pandas dataframe with columns price(float), market(string, market form TICKERBTC),
        ticker(string), balance(float, amount available),
        amt_BTC (float), Curr_Dist(float, current proportion between 0 and 1 of each coin for portfolio)
    '''
    exchange_df = exchange_df.copy()
    #make amt BTC column
    exchange_df.eval('amt_BTC = balance * price', inplace=True)
    #get current distribution
    exchange_df['Curr_Dist'] = exchange_df.amt_BTC/(exchange_df.amt_BTC.sum())
    exchange_df['Curr_Dist'].fillna(0, inplace=True)
    return exchange_df

def plan_trades(exchange_df, weights_dict,
                portfolio_trade_basement=0.01, min_BTC_prop=0.1,
                exchange_min_trade_BTC=0.001):
    '''
    This function plans the trades by comparing the target portfolio distribution and the current distribution.
    This also filters to ensure trades are above the exchange minimum,
    that the portfolio always has above a minimum amount of BTC available,
    and any trade is above a minimum proportion of the portfolio.

    :param exchange_df: pandas dataframe with index ticker ad columns price(float),
        market(string, market form TICKERBTC), balance(float, amount available),
        amt_BTC (float), Curr_Dist(float, current proportion between 0 and 1 of each coin for portfolio)
    :param weights_dict: Dictionary of weights with Currency_Ticker:0.XX pairs.
    :param portfolio_trade_basement: float in [0,1]. The minimum trade size in percentage points of
        portfolio size.
    :param min_BTC_prop: float in [0,1]. The minimum about of BTC to be in the portfolio.
    :param exchange_min_trade_BTC: floatm the minimum trade size of the exchange in BTC. Usually 0.001.
    :return: pandas DataFrame with index ticker, columns market (string), price(float, in BTC),
        Curr_Dist(float, [0,1]), Target_Dist(float,[0,1]),Trade_Perc(float,[-1,1]), Trade_Amt (in BTC,float),
        Trade_Amt_Coin (float, in the target currency)
    '''
    target_series = pd.Series(weights_dict, name='Target_Dist')
    #join on the current exchange df
    trade_df = exchange_df.join(target_series, how='left')
    trade_df['Target_Dist'].fillna(0, inplace=True)
    #Make sure that the weights sum to 1
    trade_df.Target_Dist /= trade_df.Target_Dist.sum()
    trade_df['Target_Dist'].fillna(0, inplace=True)
    # If the target dist for non BTC is higher than non BTC propotion, rescale
    target_dist_BTC = trade_df.loc[trade_df.index == 'BTC', 'Target_Dist'].values[0]
    if min_BTC_prop > target_dist_BTC:
        non_BTC_dist = 1 - target_dist_BTC
        trade_df.Target_Dist *= (1 - min_BTC_prop)/non_BTC_dist
        #Set the BTC Target Dist
        trade_df.loc[trade_df.index == 'BTC', 'Target_Dist'] = min_BTC_prop
    #Find BTC value of portfolio
    BTC_val = exchange_df.amt_BTC.sum()
    #Set Trade basement as max of desired percentage of portfolio or
    #the minimum trade on the exchange
    portfolio_trade_basement = max(portfolio_trade_basement,exchange_min_trade_BTC/BTC_val)
    #Find the Trade percentage of portfolio for each currency
    trade_df.eval('Trade_Perc = Target_Dist - Curr_Dist',inplace=True)
    #Make sure the trades are above the Trade Basement
    trade_df.Trade_Perc = trade_df.Trade_Perc.where(trade_df.Trade_Perc.abs() > portfolio_trade_basement, 0)
    #Find the amount of each coin to be traded in BTC
    trade_df['Trade_Amt_BTC'] = trade_df.Trade_Perc * BTC_val
    #See if have enough BTC to make buys
    BTC_avail = trade_df.loc[trade_df.index == 'BTC', 'amt_BTC'].values[0]
    buy_intent_BTC = trade_df.loc[trade_df.Trade_Amt_BTC > 0, 'Trade_Amt_BTC'].sum()
    #if wanting to buy more than available, rescale to use at most 90% of current BTC avail,
    # in case prices move against us
    if buy_intent_BTC > BTC_avail:
        trade_df.loc[trade_df.Trade_Amt_BTC > 0, 'Trade_Amt_BTC'] *= 0.9 * BTC_avail/buy_intent_BTC
    # Find the amount of each coin to be traded in the target currency
    trade_df.eval('Trade_Amt_Coin = Trade_Amt_BTC/price', inplace=True)
    #drop the BTC row since base currency
    try:
        trade_df.drop(['BTC'],inplace=True)
    except:
        None
    return trade_df

'''
These are the functions that abstract away the specific exchange interface.
'''

def instantiate_api_object(exchange,public_key, private_key):
    '''
    :param exchange:
    :param public_key:
    :param private_key:
    :return api_object:
    '''
    if exchange == 'Bittrex':
        from Packages.API.Bittrex_Helper.helper import instantiate_api_object
    elif exchange == 'Binance':
        from Packages.Exchanges.binance_helper import instantiate_api_object
    return instantiate_api_object(public_key, private_key)

def get_exchange_df(exchange, api_object):
    '''
    :param exchange:
    :param api_object
    :return: pandas dataframe with index ticker (string) and
    columns price(float), market(string, market form TICKERBTC), balance(float, amount available)
    '''
    if exchange == 'Bittrex':
        from Packages.API.Bittrex_Helper.helper import get_exchange_df
    elif exchange == 'Binance':
        from Packages.Exchanges.binance_helper import get_exchange_df
    exchange_df = get_exchange_df(api_object)
    return expand_exchange_df(exchange_df)

def get_portfolio_val_BTC(exchange,public_key, private_key):
    '''
    :param exchange: string, exchange name. Binance or Bittrex
    :param public_key: string
    :param private_key: string
    :return: float
    '''
    api_object = instantiate_api_object(exchange, public_key, private_key)
    exchange_df = get_exchange_df(exchange, api_object)
    return exchange_df.amt_BTC.sum()

'''
These are end to end functions. taking a key json and a weights dictionary and
executing the trades to move the portfolio towards those weights.
'''

def execute_trades(exchange, api_object, trade_df):
    '''
    :param exchange:
    :param api_object
    :param trade_df: pandas DataFrame with index ticker, columns market (string), price(float, in BTC),
        Curr_Dist(float, [0,1]), Target_Dist(float,[0,1]),Trade_Perc(float,[-1,1]), Trade_Amt (in BTC,float),
        Trade_Amt_Coin (float, in the target currency)
    :return trade_df without 0 valued trades
    '''
    #Get ride of zero valued trades
    trade_df = trade_df.loc[trade_df.Trade_Perc != 0].copy()
    #load in the proper module
    if exchange == 'Bittrex':
        from Packages.API.Bittrex_Helper.helper import execute_trades
    elif exchange == 'Binance':
        from Packages.Exchanges.binance_helper import execute_trades
    execute_trades(api_object, trade_df)
    return trade_df

def trade_on_weights(exchange,public_key, private_key, weights_dict,
                     portfolio_trade_basement=0.01, min_BTC_prop=0.1,
                           exchange_min_trade_BTC=0.001):
    '''
    :param exchange: string
    :param public_key: string
    :param private_key: string
    :param weights_dict: Dictionary of weights with Currency_Ticker:0.XX pairs.
    :param portfolio_trade_basement: float in [0,1]. The minimum trade size in percentage points of
        portfolio size.
    :param min_BTC_prop: float in [0,1]. The minimum about of BTC to be in the portfolio.
    :param exchange_min_trade_BTC: float the minimum trade size of the exchange in BTC. Usually 0.001.
    :return:
    '''
    api_object = instantiate_api_object(exchange, public_key, private_key)
    exchange_df = get_exchange_df(exchange, api_object)
    trade_df = plan_trades(exchange_df, weights_dict, portfolio_trade_basement=portfolio_trade_basement,
                           min_BTC_prop=min_BTC_prop,
                           exchange_min_trade_BTC=exchange_min_trade_BTC)
    trade_df = execute_trades(exchange, api_object, trade_df)
    return trade_df

def all_to_BTC(exchange,public_key, private_key):
    '''
    This sends all holdings in the specified account to BTC.

    :param exchange: string
    :param public_key: string
    :param private_key: string
    :return:
    '''
    btc_dict = {'BTC':1}
    return trade_on_weights(exchange,public_key, private_key, btc_dict,
                     portfolio_trade_basement=0, min_BTC_prop=0,
                           exchange_min_trade_BTC=0)


