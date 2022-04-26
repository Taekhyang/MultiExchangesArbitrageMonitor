def sai_to_bithumb_converter(pair):
    # BTC_XRP -> XRP_BTC
    market, trade = pair.split('_')
    return '{}_{}'.format(trade, market)


def bithumb_to_sai_converter(pair):
    # XRP_BTC -> BTC_XRP
    trade, market = pair.split('_')
    return '{}_{}'.format(market, trade)
