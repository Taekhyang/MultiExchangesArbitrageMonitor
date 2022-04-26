import sys
import time
import asyncio

from BaseApi.Huobi.base_huobi import BaseHuobi
from BaseApi.Binance.base_binance import BaseBinance
from BaseApi.Upbit.base_upbit import BaseUpbit
from BaseApi.Bithumb.base_bithumb import BaseBithumb
from BaseApi.Mexc.base_mexc import BaseMexc


def test_huobi_subscription():
    loop = asyncio.get_event_loop()

    base_huobi = BaseHuobi(None, None)
    available = base_huobi.get_available()
    print(available)

    base_huobi.set_subscriber()

    base_huobi.set_subscribe_trade(['USDT_MIR', 'BTC_RCN', 'ETH_RENBTC', 'USDT_BNT', 'USDT_UTK', 'BTC_18C', 'ETH_LRC'])
    base_huobi.set_subscribe_orderbook(['USDT_MIR', 'BTC_RCN', 'ETH_RENBTC', 'USDT_BNT', 'USDT_UTK', 'BTC_18C', 'ETH_LRC'])

    time.sleep(10)

    _orderbook = base_huobi.get_orderbook_high_low()
    orderbook = loop.run_until_complete(_orderbook)

    trade = base_huobi.get_latest_trade()
    print(trade.data)
    print(orderbook.data)

    return orderbook.data, trade.data


def test_binance_subscription():
    loop = asyncio.get_event_loop()

    base_binance = BaseBinance(None, None)
    availble = base_binance.get_available()
    print(availble)

    base_binance.set_subscriber()
    base_binance.set_subscribe_trade(['BTC_META', 'KRW_MOC', 'BTC_ANKR', 'BTC_CRO', 'KRW_ENJ'])
    base_binance.set_subscribe_orderbook(['BTC_META', 'KRW_MOC', 'BTC_ANKR', 'BTC_CRO', 'KRW_ENJ'])
    time.sleep(60)

    _orderbook = base_binance.get_orderbook_high_low()
    orderbook = loop.run_until_complete(_orderbook)

    trade = base_binance.get_latest_trade()
    print(trade.data)
    print(orderbook.data)

    return orderbook.data, trade.data


def test_upbit_subscription():
    loop = asyncio.get_event_loop()

    base_upbit = BaseUpbit(None, None)
    available = base_upbit.get_available()
    print(available)

    base_upbit.set_subscriber()

    base_upbit.set_subscribe_trade(['BTC_META', 'KRW_MOC', 'BTC_ANKR', 'BTC_CRO', 'KRW_ENJ'])
    base_upbit.set_subscribe_orderbook(['BTC_META', 'KRW_MOC', 'BTC_ANKR', 'BTC_CRO', 'KRW_ENJ'])

    time.sleep(120)

    _orderbook = base_upbit.get_orderbook_high_low()
    orderbook = loop.run_until_complete(_orderbook)

    trade = base_upbit.get_latest_trade()
    print(trade.data)
    print(orderbook.data)

    return orderbook.data, trade.data


def test_bithumb_subscription():
    loop = asyncio.get_event_loop()

    base_bithumb = BaseBithumb(None, None)
    available = base_bithumb.get_available()
    print(available)

    base_bithumb.set_subscriber()

    base_bithumb.set_subscribe_trade(['KRW_BTG', 'KRW_EOS', 'KRW_ICX', 'KRW_TRX', 'KRW_ELF'])
    base_bithumb.set_subscribe_orderbook(['KRW_BTG', 'KRW_EOS', 'KRW_ICX', 'KRW_TRX', 'KRW_ELF'])

    time.sleep(120)

    _orderbook = base_bithumb.get_orderbook_high_low()
    orderbook = loop.run_until_complete(_orderbook)

    trade = base_bithumb.get_latest_trade()
    return orderbook.data, trade.data


def test_mexc_subscription():
    loop = asyncio.get_event_loop()

    base_mexc = BaseMexc(None, None)
    available = base_mexc.get_available()
    print(available)
    base_mexc.set_subscriber()

    base_mexc.set_subscribe_orderbook(['USDT_ETH', 'USDT_DAISY', 'USDT_ROCKS', 'USDT_BTT3S', 'USDT_IDEX'])
    base_mexc.set_subscribe_trade(['USDT_ETH', 'USDT_DAISY', 'USDT_ROCKS', 'USDT_BTT3S', 'USDT_IDEX'])

    time.sleep(120)

    _orderbook = base_mexc.get_orderbook_high_low()
    orderbook = loop.run_until_complete(_orderbook)

    trade = base_mexc.get_latest_trade()
    print(trade.data)
    print(orderbook.data)

    return orderbook.data, trade.data


if __name__ == '__main__':
    # binance_test = test_binance_subscription()
    # huobi_test = test_huobi_subscription()
    # upbit_test = test_upbit_subscription()
    # bithumb_test = test_bithumb_subscription()
    # mexc_test = test_mexc_subscription()

    # print(binance_test)
    # print(huobi_test)
    # print(upbit_test)
    # print(bithumb_test)
    # print(mexc_test)

    sys.exit(0)
