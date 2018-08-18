import pandas as pd
import sqlalchemy as sa

def instantiate_engine(json_path, key_name):
    '''
    :return engine: sqlalchemy engine for colornoun database
    :return conn: sqlalchemy engine connection for colornoun database
    '''
    # Connecting to mysql by providing a sqlachemy engine
    import json
    import os
    with open(json_path) as secrets_file:
        secrets = json.load(secrets_file)
        secrets_file.close()
    key_dict = secrets[key_name]
    engine_string = 'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST_IP}:{MYSQL_PORT}/{MYSQL_DATABASE}'
    engine = sa.create_engine(engine_string.format(MYSQL_USER=key_dict['MYSQL_USER'],
                                                MYSQL_PASSWORD=key_dict['MYSQL_PASSWORD'],
                                                MYSQL_HOST_IP=key_dict['MYSQL_HOST_IP'],
                                                MYSQL_PORT=key_dict['MYSQL_PORT'],
                                                MYSQL_DATABASE=key_dict['MYSQL_DATABASE']),
                           echo=False)
    conn = engine.connect()
    return engine,conn

def query_raw_data(coin,columns,first_epoch,last_epoch, conn, normalize=True, norm_min=10000):
    '''
    :param coin: string, coin ticker
    :param columns: list of strings, columns desired can be
        ['returns','spread','open_time','close_time','num_trades','open','high','low','close','volume',
            'quote_asset_volume','taker_buy_base_asset_volume','taker_buy_quote_asset_volume','coin']
    :param first_epoch: int
    :param last_epoch: int
    :param conn: sqlalchemy engine connection for colornoun database
    :param normalize: bool, if the spread or volume is to be normalized
    :param norm_min: int, number of minutes to normalize over, default is 10k about 1 week
    :return: sql query result as a pandas dataframe
    '''
    query_cols = set(columns)
    offset = 60000 * (norm_min - 1)
    #query data for necessary columns desired
    if 'return' in columns:
        query_cols = query_cols.union(set(['open', 'close']))
        query_cols.remove('return')
    if 'spread' in columns:
        query_cols = query_cols.union(set(['high', 'low']))
        query_cols.remove('spread')
    #offset the query start date to accomodate normalization
    if 'spread' in columns or 'volume' in columns and normalize:
        first_epoch -= offset
    #develop query statement
    stmt = 'SELECT ' + ','.join(map(str, list(query_cols)))
    stmt += ' FROM {}_binance_raw'.format(coin)
    stmt += ' WHERE open_time >= {} AND open_time <= {}'.format(first_epoch, last_epoch)
    df = pd.read_sql(stmt, conn)
    #make sure data is in appropriate type
    int_cols = ['open_time', 'close_time', 'num_trades']
    for col in query_cols.intersection(set(int_cols)):
        df[col] = df[col].astype(int)
    float_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume',
                  'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
    for col in query_cols.intersection(set(float_cols)):
        df[col] = df[col].astype(float)
    if 'return' in columns:
        df['return'] = (df.close - df.open).divide(df.open)
    if 'spread' in columns:
        df['spread'] = df.high - df.low
        if normalize:
            df['spread'] = (df['spread'] - df['spread'].rolling(norm_min).mean()).divide(
                df['spread'].rolling(norm_min).std())
    if 'volume' in columns and normalize:
        df['volume'] = (df['volume'] - df['volume'].rolling(norm_min).mean()).divide(
            df['volume'].rolling(norm_min).std())
    df.dropna(inplace=True)
    return df[columns].copy()

def parse_df(df, num_rows = 10000):
    '''
    Meant to parse pandas dataframe before upload. SQL connection times out if uploading more than
    25k rows.
    :param df: pandas datatframe
    :param num_rows: number of rows for dataframe to be split into
    :return:
    '''
    df_list = list()
    num_split = len(df) // num_rows + 1
    for i in range(num_split):
        df_list.append(df[i*num_rows:(i+1)*num_rows])
    return df_list

def upload_df_to_db(df, table_name, engine):
    '''
    This is to help the parsing and uploading of pandas dataframes
    :param df: pandas dataframe
    :param table_name: name of table on database
    :param engine: sqlalchemy engine
    '''
    df_list = parse_df(df)
    for upload_df in df_list:
        try:
            upload_df.to_sql(table_name, con=engine, index=False, if_exists='append')
            print('Success')
        except Exception as e:
            print('Failure')
            print(e)

def get_last_epoch_binance_raw_data(coin,conn):
    '''
    This is meant to help uploading the raw historic data to the colornoun db
    :param coin: string, ticker of coin
    :param conn: sqlalchemy engine connection for colornoun database
    :param engine: engine: sqlalchemy engine for colornoun database
    :return last_epoch: int
    '''
    try:
        #Query Database for most recent enty
        stmt = '''SELECT open_time from {}_binance_raw ORDER BY open_time DESC LIMIT 1'''.format(
            coin)
        df = pd.read_sql(stmt,conn)
        last_epoch = df.values[0][0]
    except:
        last_epoch = 1500004800000
    return last_epoch

def get_data_gaps(input_df):
    '''
    This is meant to find any breaks in the data coverages
    :param input_df: Binance raw dataframe with column named open_time which are millisecond epoch integers
        This is the standard form for the Binance API
    :return: a list of tuples of epochs where data is missing
    '''
    df = input_df.copy()
    df = df.sort_values('open_time', ascending=False)
    df['diff'] = df.open_time - df.open_time.shift(-1)
    df['prev'] = df.open_time.shift(-1)
    df.prev += 60000
    missing_data = df.loc[df['diff'] > 60000].copy()
    
    return list(zip(missing_data.prev.astype(int), missing_data.open_time.astype(int)))

def grab_data(coins, start_epoch, end_epoch, data_list):
    '''
    This returns a dataframe of the requested data
    :param coins: list of strings, tickers of desirec coins
    :param start_epoch: int
    :param end_epoch: int
    :param data_list: list of strings,
        ['returns','spread','open_time','close_time','num_trades','open','high','low','close','volume',
            'quote_asset_volume','taker_buy_base_asset_volume','taker_buy_quote_asset_volume','coin']
    :return: pandas dataframe, columns of names data_TICKER (ex: return_LTC)
    '''
    # query data and save file
    engine, conn = instantiate_engine()
    data_list.append('open_time')
    #make sure no duplicate entries in data list
    data_list = list(set(data_list))
    out_df = pd.DataFrame()
    for coin in coins:
        print('Grabbing {} Data'.format(coin))
        temp_df = query_raw_data(coin, data_list, start_epoch, end_epoch, conn)
        temp_df.set_index('open_time', inplace=True)
        # rename the comlumns
        map_dict = {}
        for column in temp_df.columns:
            map_dict[column] = '{}_{}'.format(column, coin)
        temp_df.rename(columns=map_dict, inplace=True)
        # append this to the out_Df
        out_df = out_df.join(temp_df, how='outer')
    return out_df
