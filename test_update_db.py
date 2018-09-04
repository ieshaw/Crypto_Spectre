import pandas as pd
import time
import numpy as np
import Packages.Data.helper as data_helper
from Packages.Exchanges.general_helper import key_retriever,instantiate_api_object
from Packages.Miscellaneous.email import load_credentials,send_email
from Packages.Miscellaneous.timer import timer

#Use binance account to pull data
key_path = '.keys.json'
key_name = 'Binance'
key_status = 'ro'
i = 0
done = False
effort_counter = 0
effort_max = 5
while (not done) and (effort_counter < effort_max):
    try : 
        exchange, public_key, private_key = key_retriever(key_path,key_name,key_status)
        api_object = instantiate_api_object(exchange, public_key, private_key)
        engine,conn = data_helper.instantiate_engine(json_path=key_path,key_name="DB")
        ex_info_df = pd.DataFrame(api_object.get_exchange_info()['symbols'])
        ex_info_df = ex_info_df.loc[ex_info_df.quoteAsset == 'BTC']
        num_coins = len(ex_info_df)
        print('{} Currencies to update.'.format(num_coins))
        tic = time.time()
        to_update_df = ex_info_df.iloc[i:].copy()
        for index,row in to_update_df.iterrows():
            coin = row.baseAsset
            market = row.symbol
            coin = row.baseAsset
            market = row.symbol
            print('Uploading: {}. Currency {} of {}'.format(coin, i+1, num_coins))
            last_epoch = data_helper.get_last_epoch_binance_raw_data(coin=coin, conn=conn)
            klines = api_object.get_historical_klines(market, '1m', start_str=str(last_epoch))
            df = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume',
                                               'close_time', 'quote_asset_volume', 'num_trades', 'taker_buy_base_asset_volume',
                                               'taker_buy_quote_asset_volume', 'ignore'])
            df['coin'] = coin
            df = df.loc[df.open_time > last_epoch].copy()
            table_name = '{}_binance_raw'.format(coin)
            data_helper.upload_df_to_db(df, table_name, engine)
            i += 1
        toc = time.time()
        #Email to notify being done
        msg = 'Complete. Took: {}'.format(timer(tic,toc))
        subj = 'Upload Market Data'
        to_addrs = ['ian@spectre.engineering']
        json_path='.keys.json'
        key_name='Email'
        send_email(json_path,key_name,msg,subj,to_addrs)
        done = True
    except Exception as e:
        print(e)
        effort_counter += 1
        print('Effort {}, of max {}, failed. Trying again'.format(effort_counter, effort_max))
