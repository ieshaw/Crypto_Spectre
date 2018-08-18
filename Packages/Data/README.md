# Data Package

This package is meant to aid in the interface with the Color Noun database.

## From Binance

From Binance we have the minutely candle metrics for over 100 coins. This is
open_time, open, close, close_time, high, low, volume, 
quote_asset_volume, taker_buy_base_asset_volume, taker_buy_quote_asset_volume.

## First Epoch

In this directory is a file callsed `first_epoch.csv` which by coin has the first epoch 
(in milliseconds, in accordance with the Binance API format) for which we have data.

## Normalization

In the `query_raw_data` method, we have automated preprocessing in order to generate 
return and spread metrics. Furthermore there is a normalization option for volume and spread.
The default normalization is 10k minutes, which is about one week.

## Missing Data

There are gaps in the continuity of our data due to a gap in coverage from the Binance API. 
Some of these gaps are consistent accross all
currencies. For example (1518321660000, 1518323700000) and (1513600200000, 1513604040000). 
Other gaps are coin specific. This is important to keep in mind when interfacing with the
database.

Use the `get_data_gaps` function to identify these missing windows of data.