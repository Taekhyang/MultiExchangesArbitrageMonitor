import threading
import multiprocessing
import asyncio
import queue
import configparser

from enum import Enum
from BaseApi.Binance.base_binance import BaseBinance
from BaseApi.Bithumb.base_bithumb import BaseBithumb
from BaseApi.Huobi.base_huobi import BaseHuobi
from BaseApi.Upbit.base_upbit import BaseUpbit
from BaseApi.Mexc.base_mexc import BaseMexc
from util import (get_exchange_combinations, filter_market, format_comma,
                send_telegram, get_current_krw_usd_exchange_rate, debugger)
from models import ArbitrageMonitorModel



config = configparser.ConfigParser()
config.read('config.ini')

TELEGRAM_ORDERBOOK_HIGH_LOW = float(config['telegram']['orderbook_high_low'])
TELEGRAM_TRADE_PRICE = float(config['telegram']['trade_price'])

MAX_ZERO = 2


class Markets(object):
    KRW = 'KRW'
    USDT = 'USDT'


class Consts(object):
    ASK = 'ask'
    BID = 'bid'

    EXCHANGE_RATES = 'exchange_rates'


class ExchangeRateSymbols(object):
    KRW_BTC = 'KRW_BTC'
    KRW_USDT = 'KRW_USDT'
    USDT_BTC = 'USDT_BTC'
    KRW_ETH = 'KRW_ETH'
    KRW_USD = 'KRW_USD'


class Exchanges(Enum):
    BINANCE = 'binance'
    HUOBI = 'huobi'
    MEXC = 'mexc'
    UPBIT = 'upbit'
    BITHUMB = 'bithumb'


class ArbitrageTypes(object):
    ORDERBOOK_HIGH_LOW = 'orderbook_high_low'
    TRADE_PRICE = 'trade_price'


class ExchangeSymbol(object):
    def __init__(self, exchange, symbol):
        self.exchange = exchange
        self.symbol = symbol

    @property
    def market(self):
        market, _ = self.symbol.split('_')
        return market

    @property
    def trade(self):
        _, trade = self.symbol.split('_')
        return trade


class ArbitrageByOrderBookHighLowPrice(object):
    def __init__(
            self, trade_symbol, base_exchange,
            base_exchange_market, target_exchange, target_exchange_market,
            base_high_bid_price=None, target_low_ask_price=None, arbitrage_percent=None
    ):
        self.trade_symbol = trade_symbol

        self.base_exchange = base_exchange
        self.base_exchange_market = base_exchange_market

        self.target_exchange = target_exchange
        self.target_exchange_market = target_exchange_market

        self.base_high_bid_price = round(base_high_bid_price, MAX_ZERO) if base_high_bid_price else base_high_bid_price
        self.target_low_ask_price = round(target_low_ask_price,
                                          MAX_ZERO) if target_low_ask_price else target_low_ask_price

        self.arbitrage_percent = round(arbitrage_percent, MAX_ZERO) if arbitrage_percent else arbitrage_percent

    @property
    def base_high_bid_price_with_comma(self):
        return format_comma(self.base_high_bid_price)

    @property
    def target_low_ask_price_with_comma(self):
        return format_comma(self.target_low_ask_price)

    @property
    def arbitrage_percent_with_comma(self):
        return format_comma(self.arbitrage_percent)

    def __str__(self):
        return """
         arbitrage type : orderbook high low
         trade symbol : [{}]
         base exchange: [{}] base exchange market: [{}]
         target exchange: [{}] target exchange market: [{}]
         base high bid price: [{}] target low ask price: [{}]
         arbitrage percent: [{}]
         """.format(
            self.trade_symbol, self.base_exchange, self.base_exchange_market,
            self.target_exchange, self.target_exchange_market, self.base_high_bid_price,
            self.target_low_ask_price, self.arbitrage_percent
        )

    def __eq__(self, other):
        if isinstance(other, ArbitrageByOrderBookHighLowPrice):
            return self.trade_symbol == other.trade_symbol and \
                   self.base_exchange == other.base_exchange and self.base_exchange_market == other.base_exchange_market and \
                   self.target_exchange == other.target_exchange and self.target_exchange_market == other.target_exchange_market


class ArbitrageByLastTradePrice(object):
    def __init__(
            self, trade_symbol, base_exchange,
            base_exchange_market, target_exchange, target_exchange_market,
            base_trade_price=None, target_trade_price=None, arbitrage_percent=None
    ):
        self.trade_symbol = trade_symbol

        self.base_exchange = base_exchange
        self.base_exchange_market = base_exchange_market

        self.target_exchange = target_exchange
        self.target_exchange_market = target_exchange_market

        self.base_trade_price = round(base_trade_price, MAX_ZERO) if base_trade_price else base_trade_price
        self.target_trade_price = round(target_trade_price, MAX_ZERO) if target_trade_price else target_trade_price

        self.arbitrage_percent = round(arbitrage_percent, MAX_ZERO) if arbitrage_percent else arbitrage_percent

    @property
    def base_trade_price_with_comma(self):
        return format_comma(self.base_trade_price)

    @property
    def target_trade_price_with_comma(self):
        return format_comma(self.target_trade_price)

    @property
    def arbitrage_percent_with_comma(self):
        return format_comma(self.arbitrage_percent)

    def __str__(self):
        return """
        arbitrage type : trade price
        trade symbol : [{}]
        base exchange: [{}] base exchange market: [{}]
        target exchange: [{}] target exchange market: [{}]
        base trade price: [{}] target trade price: [{}]
        arbitrage percent: [{}]
        """.format(
            self.trade_symbol, self.base_exchange, self.base_exchange_market,
            self.target_exchange, self.target_exchange_market, self.base_trade_price,
            self.target_trade_price, self.arbitrage_percent
        )

    def __eq__(self, other):
        if isinstance(other, ArbitrageByLastTradePrice):
            return self.trade_symbol == other.trade_symbol and \
                   self.base_exchange == other.base_exchange and self.base_exchange_market == other.base_exchange_market and \
                   self.target_exchange == other.target_exchange and self.target_exchange_market == other.target_exchange_market


class MultiExchangeCrawler(threading.Thread):
    def __init__(self, arbitrage_queue, exclude_trigger_queue):
        super(MultiExchangeCrawler, self).__init__()
        self.base_binance = BaseBinance(None, None)
        self.base_bithumb = BaseBithumb(None, None)
        self.base_huobi = BaseHuobi(None, None)
        self.base_upbit = BaseUpbit(None, None)
        self.base_mexc = BaseMexc(None, None)

        self.binance_orderbook_high_low = None
        self.bithumb_orderbook_high_low = None
        self.huobi_orderbook_high_low = None
        self.upbit_orderbook_high_low = None
        self.mexc_orderbook_high_low = None

        self.arbitrage_monitor_model = ArbitrageMonitorModel()
        self.arbitrage_monitor_model.migrate()

        self._exclude_arbitrage_by_orderbook_high_low_obj_list = list()
        self._exclude_arbitrage_by_trade_price_obj_list = list()

        self.available_symbols_dict = dict()
        self.exchange_rate_dict = dict()
        self.subscribe_symbols_dict = dict()
        self.comparison_pairs = list()

        self._arbitrage_by_orderbook_high_low_list = list()
        self._arbitrage_by_trade_price_list = list()
        self._arbitrage_dict = dict()

        self.arbitrage_queue = arbitrage_queue
        self.exclude_trigger_queue = exclude_trigger_queue

        self.loop = asyncio.get_event_loop()

        self._set_all_subscribe()
        self._set_all_availables()
        self._set_comparison_pairs()
        self._subscribe_symbols()

        self._update_exclude_list()

    def _set_all_subscribe(self):
        self.base_binance.set_subscriber()
        self.base_bithumb.set_subscriber()
        self.base_upbit.set_subscriber()
        self.base_huobi.set_subscriber()
        self.base_mexc.set_subscriber()

    def _set_all_availables(self):
        """
            upbit, bithumb -> KRW market
            binance, huobi, mexc -> USDT market
        """

        binance_symbol_list = self.base_binance.get_available()
        filtered_binance_symbol_list = filter_market([Markets.USDT], binance_symbol_list)

        huobi_symbol_list = self.base_huobi.get_available()
        filtered_huobi_symbol_list = filter_market([Markets.USDT], huobi_symbol_list)

        mexc_symbol_list = self.base_mexc.get_available()
        filtered_mexc_symbol_list = filter_market([Markets.USDT], mexc_symbol_list)

        upbit_symbol_list = self.base_upbit.get_available()
        filtered_upbit_symbol_list = filter_market([Markets.KRW], upbit_symbol_list)

        bithumb_symbol_list = self.base_bithumb.get_available()
        filtered_bithumb_symbol_list = filter_market([Markets.KRW], bithumb_symbol_list)

        self.available_symbols_dict[Exchanges.BINANCE.value] = filtered_binance_symbol_list
        self.available_symbols_dict[Exchanges.HUOBI.value] = filtered_huobi_symbol_list
        self.available_symbols_dict[Exchanges.MEXC.value] = filtered_mexc_symbol_list
        self.available_symbols_dict[Exchanges.UPBIT.value] = filtered_upbit_symbol_list
        self.available_symbols_dict[Exchanges.BITHUMB.value] = filtered_bithumb_symbol_list

    def update_market_exchange_rates(self):
        upbit_support_symbols = [ExchangeRateSymbols.KRW_BTC, ExchangeRateSymbols.KRW_ETH]

        for symbol in upbit_support_symbols:
            result = self.base_upbit.get_ticker(symbol)
            if result.success:
                current_price = result.data['sai_price']
                self.exchange_rate_dict[symbol] = current_price

        binance_support_symbols = [ExchangeRateSymbols.USDT_BTC]

        for symbol in binance_support_symbols:
            result = self.base_binance.get_ticker(symbol)
            if result.success:
                current_price = float(result.data['sai_price'])
                self.exchange_rate_dict[symbol] = current_price

        # 테더값은 업비트의 비트코인 원화가격을 바이낸스의 비트코인 테더로 나눈다
        upbit_btc_to_krw = self.exchange_rate_dict[ExchangeRateSymbols.KRW_BTC]
        binance_btc_to_usdt = self.exchange_rate_dict[ExchangeRateSymbols.USDT_BTC]

        usdt_in_krw = upbit_btc_to_krw / binance_btc_to_usdt
        self.exchange_rate_dict[ExchangeRateSymbols.KRW_USDT] = usdt_in_krw

        # 원달러 환율
        usd_in_krw = get_current_krw_usd_exchange_rate()
        self.exchange_rate_dict[ExchangeRateSymbols.KRW_USD] = usd_in_krw

    def _set_comparison_pairs(self):
        """
            set comparison pairs from exchange combinations
            it makes pairs from two lists
            ex) binance: ['USDT_BTC', 'USDT_DOGE', ...], upbit: ['KRW_BTC', 'USDT_XRP', ...]

            -> self.comparison_pairs : [(ExchangeSymbol('binance', 'BTC'), ExchangeSymbol('upbit', 'BTC')), ...]
        """
        exchanges = [exchange.value for exchange in Exchanges]
        exchange_combinations = get_exchange_combinations(exchanges)

        for base_exchange, target_exchange in exchange_combinations:
            base_available_list = self.available_symbols_dict[Exchanges(base_exchange).value]
            target_available_list = self.available_symbols_dict[Exchanges(target_exchange).value]

            for base_symbol in base_available_list:
                _, base_trade = base_symbol.split('_')
                for target_symbol in target_available_list:
                    _, target_trade = target_symbol.split('_')

                    if base_trade == target_trade:
                        base_exchange_symbol = ExchangeSymbol(base_exchange, base_symbol)
                        target_exchange_symbol = ExchangeSymbol(target_exchange, target_symbol)
                        pair_tuple = (base_exchange_symbol, target_exchange_symbol)

                        self.comparison_pairs.append(pair_tuple)

                        # add symbols that are actually going to be subscribed
                        self.subscribe_symbols_dict.setdefault(base_exchange, set())
                        self.subscribe_symbols_dict.setdefault(target_exchange, set())

                        self.subscribe_symbols_dict[base_exchange].add(base_symbol)
                        self.subscribe_symbols_dict[target_exchange].add(target_symbol)

    def _subscribe_symbols(self):
        for exchange in self.subscribe_symbols_dict:
            subscribe_symbol_list = list(self.subscribe_symbols_dict[exchange])

            if exchange == Exchanges.BINANCE.value:
                self.base_binance.set_subscribe_orderbook(subscribe_symbol_list)
                self.base_binance.set_subscribe_trade(subscribe_symbol_list)
                debugger.info('subscribe {}'.format(Exchanges.BINANCE.value))

            elif exchange == Exchanges.BITHUMB.value:
                self.base_bithumb.set_subscribe_orderbook(subscribe_symbol_list)
                self.base_bithumb.set_subscribe_trade(subscribe_symbol_list)
                debugger.info('subscribe {}'.format(Exchanges.BITHUMB.value))

            elif exchange == Exchanges.UPBIT.value:
                self.base_upbit.set_subscribe_orderbook(subscribe_symbol_list)
                self.base_upbit.set_subscribe_trade(subscribe_symbol_list)
                debugger.info('subscribe {}'.format(Exchanges.UPBIT.value))

            elif exchange == Exchanges.HUOBI.value:
                self.base_huobi.set_subscribe_orderbook(subscribe_symbol_list)
                self.base_huobi.set_subscribe_trade(subscribe_symbol_list)
                debugger.info('subscribe {}'.format(Exchanges.HUOBI.value))

            elif exchange == Exchanges.MEXC.value:
                self.base_mexc.set_subscribe_orderbook(subscribe_symbol_list)
                self.base_mexc.set_subscribe_trade(subscribe_symbol_list)
                debugger.info('subscribe {}'.format(Exchanges.MEXC.value))

    def _convert_exchange_rate(self, symbol, price):
        market, trade = symbol.split('_')
        if market == Markets.USDT:
            usdt_in_krw = self.exchange_rate_dict[ExchangeRateSymbols.KRW_USDT]
            return price * usdt_in_krw
        return price

    def _update_exclude_list(self):
        self._exclude_arbitrage_by_orderbook_high_low_obj_list = list()
        self._exclude_arbitrage_by_trade_price_obj_list = list()

        exclude_list = self.arbitrage_monitor_model.get_excludes_list()
        for each in exclude_list:
            if each['arbitrage_type'] == ArbitrageTypes.ORDERBOOK_HIGH_LOW:
                obj = ArbitrageByOrderBookHighLowPrice(
                    each['trade_symbol'],
                    each['base_exchange'],
                    each['base_exchange_market'],
                    each['target_exchange'],
                    each['target_exchange_market']
                )
                self._exclude_arbitrage_by_orderbook_high_low_obj_list.append(obj)

            elif each['arbitrage_type'] == ArbitrageTypes.TRADE_PRICE:
                obj = ArbitrageByLastTradePrice(
                    each['trade_symbol'],
                    each['base_exchange'],
                    each['base_exchange_market'],
                    each['target_exchange'],
                    each['target_exchange_market']
                )
                self._exclude_arbitrage_by_trade_price_obj_list.append(obj)

    def run(self):
        while True:
            try:
                is_exclude_update_triggered = self.exclude_trigger_queue.get(timeout=0.1)
                if is_exclude_update_triggered:
                    self._update_exclude_list()
            except queue.Empty:
                pass

            self.update_market_exchange_rates()

            self._arbitrage_by_orderbook_high_low_list = list()
            self._arbitrage_by_trade_price_list = list()

            # update orderbook for all exchanges
            self._update_orderbook_high_low()

            for base_exchange_symbol_obj, target_exchange_symbol_obj in self.comparison_pairs:
                trade_symbol = base_exchange_symbol_obj.trade

                # get orderbook high bid price for base & orderbook low ask price for target
                base_high_bid_price = self._get_orderbook_high_low(
                    base_exchange_symbol_obj.exchange,
                    base_exchange_symbol_obj.symbol,
                    Consts.BID
                )
                target_low_ask_price = self._get_orderbook_high_low(
                    target_exchange_symbol_obj.exchange,
                    target_exchange_symbol_obj.symbol,
                    Consts.ASK
                )

                if base_high_bid_price and target_low_ask_price:
                    base_high_bid_price = self._convert_exchange_rate(base_exchange_symbol_obj.symbol,
                                                                      base_high_bid_price)
                    target_low_ask_price = self._convert_exchange_rate(target_exchange_symbol_obj.symbol,
                                                                       target_low_ask_price)

                    arbitrage_by_orderbook_high_low_percent = ((
                                                                           base_high_bid_price - target_low_ask_price) / base_high_bid_price) * 100

                    arbitrage_by_orderbook_high_low_obj = ArbitrageByOrderBookHighLowPrice(
                        trade_symbol,
                        base_exchange_symbol_obj.exchange,
                        base_exchange_symbol_obj.market,
                        target_exchange_symbol_obj.exchange,
                        target_exchange_symbol_obj.market,
                        base_high_bid_price,
                        target_low_ask_price,
                        arbitrage_by_orderbook_high_low_percent
                    )

                    # exclude user's exclude list for arbitrage by orderbook high low
                    if arbitrage_by_orderbook_high_low_obj not in self._exclude_arbitrage_by_orderbook_high_low_obj_list:
                        self._arbitrage_by_orderbook_high_low_list.append(arbitrage_by_orderbook_high_low_obj)
                        # debugger.info(str(arbitrage_by_orderbook_high_low_obj))

                # get trade price for base & trade price for target
                base_trade_price = self._get_last_trade(
                    base_exchange_symbol_obj.exchange,
                    base_exchange_symbol_obj.symbol
                )
                target_trade_price = self._get_last_trade(
                    target_exchange_symbol_obj.exchange,
                    target_exchange_symbol_obj.symbol
                )

                if base_trade_price and target_trade_price:
                    base_trade_price = self._convert_exchange_rate(base_exchange_symbol_obj.symbol, base_trade_price)
                    target_trade_price = self._convert_exchange_rate(target_exchange_symbol_obj.symbol,
                                                                     target_trade_price)

                    arbitrage_by_trade_price_percent = ((
                                                                    base_trade_price - target_trade_price) / base_trade_price) * 100
                    arbitrage_by_trade_price_obj = ArbitrageByLastTradePrice(
                        trade_symbol,
                        base_exchange_symbol_obj.exchange,
                        base_exchange_symbol_obj.market,
                        target_exchange_symbol_obj.exchange,
                        target_exchange_symbol_obj.market,
                        base_trade_price,
                        target_trade_price,
                        arbitrage_by_trade_price_percent
                    )

                    # exclude user's exclude list for arbitrage by trade price
                    if arbitrage_by_trade_price_obj not in self._exclude_arbitrage_by_trade_price_obj_list:
                        self._arbitrage_by_trade_price_list.append(arbitrage_by_trade_price_obj)
                        # debugger.info(str(arbitrage_by_trade_price_obj))

            self._arbitrage_dict = {
                ArbitrageTypes.ORDERBOOK_HIGH_LOW: self._arbitrage_by_orderbook_high_low_list,
                ArbitrageTypes.TRADE_PRICE: self._arbitrage_by_trade_price_list,
                Consts.EXCHANGE_RATES: self.exchange_rate_dict
            }

            self.arbitrage_queue.put(self._arbitrage_dict)

    def _update_orderbook_high_low(self):
        self.binance_orderbook_high_low = self.base_binance.get_orderbook_high_low_sync()
        self.bithumb_orderbook_high_low = self.base_bithumb.get_orderbook_high_low_sync()
        self.upbit_orderbook_high_low = self.base_upbit.get_orderbook_high_low_sync()
        self.huobi_orderbook_high_low = self.base_huobi.get_orderbook_high_low_sync()
        self.mexc_orderbook_high_low = self.base_mexc.get_orderbook_high_low_sync()

    def _get_orderbook_high_low(self, exchange, symbol, ask_or_bid):
        if exchange == Exchanges.BINANCE.value:
            result = self.binance_orderbook_high_low

        elif exchange == Exchanges.BITHUMB.value:
            result = self.bithumb_orderbook_high_low

        elif exchange == Exchanges.UPBIT.value:
            result = self.upbit_orderbook_high_low

        elif exchange == Exchanges.HUOBI.value:
            result = self.huobi_orderbook_high_low

        elif exchange == Exchanges.MEXC.value:
            result = self.mexc_orderbook_high_low

        else:
            debugger.info('exchange [{}] does not exist'.format(exchange))
            return None

        if result.success:
            orderbook_high_low = result.data.get(symbol, None)
            if orderbook_high_low:
                if ask_or_bid == Consts.BID:
                    return orderbook_high_low['bid']
                return orderbook_high_low['ask']
            debugger.debug('exchange - [{}], symbol - [{}] not exist in orderbook high low'.format(exchange, symbol))
        return None

    def _get_last_trade(self, exchange, symbol):
        if exchange == Exchanges.BINANCE.value:
            result = self.base_binance.get_latest_trade()

        elif exchange == Exchanges.BITHUMB.value:
            result = self.base_bithumb.get_latest_trade()

        elif exchange == Exchanges.UPBIT.value:
            result = self.base_upbit.get_latest_trade()

        elif exchange == Exchanges.HUOBI.value:
            result = self.base_huobi.get_latest_trade()

        elif exchange == Exchanges.MEXC.value:
            result = self.base_mexc.get_latest_trade()

        else:
            debugger.info('exchange [{}] does not exist'.format(exchange))
            return None

        if result.success:
            trade = result.data.get(symbol, None)
            if trade:
                return trade['price']
            debugger.debug('exchange - [{}], symbol - [{}] not exist in trade'.format(exchange, symbol))
        return None


class ArbitrageMonitor(threading.Thread):
    """
        for pyqt,
        read two types of object (ArbitrageByOrderBookHighLowPrice, ArbitrageByLastTradePrice)
        if trigger_exclude_queue() is called, then MultiExchangeCrawler thread will update exclude list
    """

    def __init__(self, arbitrage_queue, exclude_trigger_queue):
        super(ArbitrageMonitor, self).__init__()
        self.arbitrage_queue = arbitrage_queue
        self.exclude_trigger_queue = exclude_trigger_queue

        self.arbitrage_monitor_model = ArbitrageMonitorModel()
        self.arbitrage_monitor_model.migrate()

    def run(self):
        while True:
            try:
                data = self.arbitrage_queue.get(timeout=10)
            except queue.Empty:
                continue

            arbitrage_by_orderbook_high_low_obj_list = data[ArbitrageTypes.ORDERBOOK_HIGH_LOW]
            for obj in arbitrage_by_orderbook_high_low_obj_list:
                # display obj attributes, use comma formatted value
                print(obj.trade_symbol)
                print(obj.base_exchange)
                print(obj.base_exchange_market)
                print(obj.target_exchange)
                print(obj.target_exchange_market)

                # comma separated format ex) 12,142,111
                print(obj.base_high_bid_price_with_comma)
                print(obj.target_low_ask_price_with_comma)
                print(obj.arbitrage_percent_with_comma)

                # telegram send logic
                if abs(obj.arbitrage_percent) >= TELEGRAM_ORDERBOOK_HIGH_LOW:
                    message = obj
                    send_telegram(message)

            arbitrage_by_orderbook_trade_price_list = data[ArbitrageTypes.TRADE_PRICE]
            for obj in arbitrage_by_orderbook_trade_price_list:
                # display obj attributes
                print(obj.trade_symbol)
                print(obj.base_exchange)
                print(obj.base_exchange_market)
                print(obj.target_exchange)
                print(obj.target_exchange_market)

                # comma separated format ex) 12,142,111
                print(obj.base_trade_price)
                print(obj.target_trade_price)
                print(obj.arbitrage_percent_with_comma)

                # telegram send logic
                if abs(obj.arbitrage_percent) >= TELEGRAM_TRADE_PRICE:
                    message = obj
                    send_telegram(message)

            # display KRW_BTC, KRW_ETH, KRW_USDT
            exchange_rates = data[Consts.EXCHANGE_RATES]
            krw_btc = exchange_rates[ExchangeRateSymbols.KRW_BTC]
            if krw_btc:
                krw_btc = format_comma(round(krw_btc, MAX_ZERO))

            krw_eth = exchange_rates[ExchangeRateSymbols.KRW_ETH]
            if krw_eth:
                krw_eth = format_comma(round(krw_eth, MAX_ZERO))

            krw_usdt = exchange_rates[ExchangeRateSymbols.KRW_USDT]
            if krw_usdt:
                krw_usdt = format_comma(round(krw_usdt, MAX_ZERO))

            krw_usd = exchange_rates[ExchangeRateSymbols.KRW_USD]
            if krw_usd:
                krw_usd = format_comma(round(krw_usd, MAX_ZERO))

            debugger.info('KRW_BTC - [{}], KRW_ETH - [{}], KRW_USDT - [{}], KRW_USD - [{}]'.format(
                krw_btc, krw_eth, krw_usdt, krw_usd)
            )

    def trigger_exclude_queue(self):
        trigger_flag = True
        self.exclude_trigger_queue.put(trigger_flag)

    def register_exclude(self, arbitrage_type, trade_symbol, base_exchange, base_exchange_market, target_exchange,
                         target_exchange_market):
        """
            usage: register_exclude('ArbitrageTypes.ORDERBOOK_HIGH_LOW', 'DOGE', 'upbit', 'KRW', 'bithumb', 'KRW')
                   register_exclude('ArbitrageTypes.TRADE_PRICE', 'ETH', 'upbit', 'KRW', 'binance', 'USDT')
        """
        self.arbitrage_monitor_model.register_exclude(
            arbitrage_type,
            trade_symbol,
            base_exchange,
            base_exchange_market,
            target_exchange,
            target_exchange_market
        )

    def revert_exclude(self, arbitrage_type, trade_symbol, base_exchange, base_exchange_market, target_exchange,
                       target_exchange_market):
        """
            usage: revert_exclude('ArbitrageTypes.ORDERBOOK_HIGH_LOW', 'DOGE', 'upbit', 'KRW', 'bithumb', 'KRW')
                   revert_exclude('ArbitrageTypes.TRADE_PRICE', 'ETH', 'upbit', 'KRW', 'binance', 'USDT')
        """
        self.arbitrage_monitor_model.revert_exclude(
            arbitrage_type,
            trade_symbol,
            base_exchange,
            base_exchange_market,
            target_exchange,
            target_exchange_market
        )


if __name__ == '__main__':
    arbitrage_q = multiprocessing.Queue()
    exclude_q = multiprocessing.Queue()

    multi_exchange = MultiExchangeCrawler(arbitrage_q, exclude_q)
    multi_exchange.start()

    arbitrage_monitor = ArbitrageMonitor(arbitrage_q, exclude_q)
    arbitrage_monitor.start()

    multi_exchange.join()
    arbitrage_monitor.join()
