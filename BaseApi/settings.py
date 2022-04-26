"""
setting of whole exchanges
"""


class Consts(object):
    GET = 'GET'
    POST = 'POST'
    
    ASKS = 'asks'
    BIDS = 'bids'

    ASK = 'ask'
    BID = 'bid'

    BUY = 'buy'
    SELL = 'sell'
    
    MARKET = 'market'
    LIMIT = 'limit'
    PRICE = 'price'
    
    # Selling the BTC from primary, Selling the ALT from secondary
    PRIMARY_TO_SECONDARY = 'primary_to_secondary'
    
    # Selling the ALT from primary, Selling the BTC from secondary
    SECONDARY_TO_PRIMARY = 'secondary_to_primary'
    
    CANDLE_LIMITATION = 100
    ORDERBOOK_LIMITATION = 20
    
    CANDLE = 'candle'
    ORDERBOOK = 'orderbook'
    TICKER = 'ticker'
    TRADE = 'trade'

    OPEN = 'open'
    ON_TRADING = 'on_trading'
    CLOSED = 'closed'
