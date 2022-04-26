import itertools
import json
import logging

from investpy import currency_crosses


debugger = logging.logger()



def get_exchange_combinations(exchange_list):
    """
        get exchange combinations
        ex) (binance, upbit), (upbit, bithumb), ...
    """
    return itertools.permutations(exchange_list, 2)


def filter_market(market_list, symbol_list):
    filtered = list()
    for symbol in symbol_list:
        market, trade = symbol.split('_')
        if market in market_list:
            filtered.append(symbol)
    return filtered


def format_comma(number):
    if number:
        return format(number, ',')
    return number


def send_telegram(message):
    pass


def get_current_krw_usd_exchange_rate():
    try:
        data = currency_crosses.get_currency_cross_recent_data(currency_cross='USD/KRW', as_json=True, order='desc')
        json_data = json.loads(data)

        recent = json_data.get('recent', None)
        if recent:
            close = recent[0]['close']
            return close
    except Exception:
        debugger.exception('get_current_krw_usd_exchange_rate failed')
        return None
    return None
