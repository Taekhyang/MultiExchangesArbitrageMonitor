# MultiExchangesArbitrageMonitor
## Monitor arbitrages between multiple exchanges (Bianance, Bithumb, Huobi, Mexc, Upbit) and spot the meaningful arbitrage rate

1. It spots the arbitrage based on "orderbook's highest and lowest bid-ask difference" between different exchanges
2. It spots the arbitrage based on "latest trade price difference" between different exchanges

- Added 5 exchange baseapi, subscriber (orderbook price, trade price)

- MultiExchangeCrawler thread for updating `ArbitrageByOrderBookHighLowPrice` & `ArbitrageByLastTradePrice` & `self.exchange_rates_dict` and sending those to pyqt thread through `arbitrage_queue`

- `ArbitrageMonitorModel` creates `arbitrage_monitor` sqlite3 memory db and creates default table by calling `migrate()`

- `ArbitrageMonitorModel`'s default table is `exclude_set` which stores user's excluding pairs

- `ArbitrageMonitor` thread for reading two types of "arbitrage objects" & "exchange rates" in run() method, you can use object attributes in `ArbitrageByOrderBookHighLowPrice` & `ArbitrageByLastTradePrice`.

- If `ArbitrageMonitor` gets excluding pair signal from user, you should call `register_exclude()` for updating exclude pairs in db and call `trigger_exclude_queue()`. When you call trigger_exclude_queue(), `MultiExchangeCrawler` gets `trigger_flag` which is True then calls `_update_exclude_list()` to update exclude list and filter those list.

- telegram setting can be configured in `config.ini` file and it consists of two types which are `orderbook_high_low` & `trade_price`

- If you want send telegram message, then call send_telegram()


Hid all exchanges baseapi except bithumb for personal reason
