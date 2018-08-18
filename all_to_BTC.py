from Packages.Exchanges.general_helper import key_retriever, get_exchange_df, instantiate_api_object, all_to_BTC

key_path = '.keys.json'
key_name = 'Binance_Old'
key_status = 'live'

exchange, public_key, private_key = key_retriever(key_path,key_name,key_status)
trade_df = all_to_BTC(exchange,public_key, private_key)
