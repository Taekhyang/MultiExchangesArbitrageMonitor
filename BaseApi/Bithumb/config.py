class Urls(object):
    BASE = 'https://api.bithumb.com'

    TICKERS = '/public/ticker/ALL_{market}'

    class Websocket(object):
        BASE = 'wss://pubwss.bithumb.com/pub/ws'


class BithumbConsts(object):
    """
        bithumb는 개별 type 값으로 구분함
        ticker: 현재가
        transaction: 체결
        orderbookdepth: 오더북 호가
    """
    ORDERBOOK = 'orderbookdepth'
    TRADE = 'transaction'
    CANDLE = 'ticker'
