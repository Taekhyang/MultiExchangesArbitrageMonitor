import requests
import time
import hmac
import hashlib
import threading
import asyncio
import json
import aiohttp

from urllib.parse import urlencode
from decimal import Decimal

from BaseApi.Bithumb.utils import sai_to_bithumb_converter, bithumb_to_sai_converter

from BaseApi.Bithumb.base_subscriber import BithumbSubscriber
from BaseApi.objects import DataStore
from BaseApi.Bithumb.config import Urls
from BaseApi.objects import ResultObject
from BaseApi.settings import Consts
from BaseApi.messages import WarningMessage, MessageDebug
from util import debugger


class BaseBithumb(object):
    name = 'Bithumb'

    def __init__(self, key, secret):
        self._key = key
        self._secret = secret

        self.data_store = DataStore()

        self._get_tickers()

        self._lock_dic = {
            Consts.ORDERBOOK: threading.Lock(),
            Consts.CANDLE: threading.Lock(),
            Consts.TRADE: threading.Lock()
        }

        self._subscriber = None

    def _public_api(self, path, extra=None):
        if extra is None:
            extra = dict()

        try:
            rq = requests.get(Urls.BASE + path, params=extra)
            response = rq.json()

            if 'message' in response:
                message = MessageDebug.FAIL_RESPONSE_DETAILS.format(name=self.name, body=response['message'],
                                                                    path=path, parameter=extra)
                debugger.debug(message)

                user_message = WarningMessage.FAIL_MESSAGE_BODY.format(name=self.name, message=response['message'])
                return ResultObject(False, str(), message=user_message, wait_time=1)
            else:
                return ResultObject(True, response)

        except Exception:
            debugger.exception('FATAL: Bithumb, _public_api')
            return ResultObject(False, str(), message=WarningMessage.EXCEPTION_RAISED.format(name=self.name), wait_time=1)

    def _get_tickers(self):
        for _ in range(3):
            result_object_btc_market = self._public_api(Urls.TICKERS.format(market='BTC'))
            result_object_krw_market = self._public_api(Urls.TICKERS.format(market='KRW'))

            if result_object_btc_market.success and result_object_krw_market.success:
                btc_market_data = result_object_btc_market.data['data']
                krw_market_data = result_object_krw_market.data['data']

                btc_market_data.pop('date')
                krw_market_data.pop('date')

                all_market_pair = dict(
                    btc_market=btc_market_data,
                    krw_market=krw_market_data
                )
                return ResultObject(True, all_market_pair)

            time.sleep(result_object_btc_market.wait_time)
        else:
            return ResultObject(False, str())

    def get_available(self):
        """
            bithumb have only BTC, KRW markets
        """

        result = self._get_tickers()
        if result.success:
            btc_market = result.data.get('btc_market')
            krw_market = result.data.get('krw_market')

            sai_symbols = list()
            for trade in btc_market:
                sai_symbol = 'BTC_{}'.format(trade)
                sai_symbols.append(sai_symbol)

            for trade in krw_market:
                sai_symbol = 'KRW_{}'.format(trade)
                sai_symbols.append(sai_symbol)

            return sai_symbols
        return list()

    def set_subscriber(self):
        self._subscriber = BithumbSubscriber(self.data_store, self._lock_dic)

    def get_orderbook(self):
        with self._lock_dic[Consts.ORDERBOOK]:
            data_dic = self.data_store.orderbook_queue
            if not self.data_store.orderbook_queue:
                return ResultObject(False, message=WarningMessage.ORDERBOOK_NOT_STORED.format(name=self.name),
                                    wait_time=1)

            return ResultObject(True, data_dic)

    def get_trade(self):
        with self._lock_dic[Consts.TRADE]:
            data_dic = self.data_store.trade_queue
            if not self.data_store.trade_queue:
                return ResultObject(False, message=WarningMessage.TRADE_NOT_STORED.format(name=self.name),
                                    wait_time=1)

            return ResultObject(True, data_dic)

    def get_orderbook_high_low_sync(self):
        with self._lock_dic[Consts.ORDERBOOK]:
            data_dic = self.data_store.orderbook_queue
            if not self.data_store.orderbook_queue:
                return ResultObject(False, message=WarningMessage.ORDERBOOK_NOT_STORED.format(name=self.name),
                                    wait_time=1)

            dic_ = dict()
            for key in data_dic:
                sai_key = bithumb_to_sai_converter(key)

                bid_ask_dict = data_dic[key]
                bid, ask = Decimal('-inf'), Decimal('inf')
                dic_.setdefault(sai_key, dict(bid=None, ask=None))

                bids_list = bid_ask_dict[Consts.BIDS]
                asks_list = bid_ask_dict[Consts.ASKS]

                for bid_dict in bids_list:
                    bid_price = float(bid_dict['price'])
                    bid = bid_price if bid_price > bid else bid
                else:
                    if bids_list:
                        dic_[sai_key]['bid'] = bid

                for ask_dict in asks_list:
                    ask_price = float(ask_dict['price'])
                    ask = ask_price if ask_price < ask else ask
                else:
                    if asks_list:
                        dic_[sai_key]['ask'] = ask
            else:
                return ResultObject(True, dic_)

    async def get_orderbook_high_low(self):
        return self.get_orderbook_high_low_sync()

    def get_latest_trade(self):
        with self._lock_dic[Consts.TRADE]:
            data_dic = self.data_store.trade_queue
            if not self.data_store.trade_queue:
                return ResultObject(False, message=WarningMessage.TRADE_NOT_STORED.format(name=self.name),
                                    wait_time=1)

            dic_ = dict()
            for key in data_dic:
                sai_key = bithumb_to_sai_converter(key)
                trade_dic = data_dic[key]

                dic_.setdefault(sai_key, dict())
                dic_[sai_key] = trade_dic['latest']
            else:
                return ResultObject(True, dic_)

    def set_subscribe_orderbook(self, coin):
        """
            subscribe orderbook.
            coin: it can be list or string, [XRP_BTC, ETH_BTC]
        """
        for _ in range(10):
            time.sleep(1)
            if self._subscriber.keep_running:
                break

        coin = list(map(sai_to_bithumb_converter, coin)) if isinstance(coin, (set, list)) \
            else sai_to_bithumb_converter(coin)
        with self._lock_dic[Consts.ORDERBOOK]:
            self._subscriber.subscribe_orderbook(coin)

        return True

    def set_subscribe_trade(self, coin):
        """
            subscribe trade detail.
            coin: it can be list or string, [XRP_BTC, ETH_BTC]
        """
        for _ in range(10):
            time.sleep(1)
            if self._subscriber.keep_running:
                break

        coin = list(map(sai_to_bithumb_converter, coin)) if isinstance(coin, (set, list)) \
            else sai_to_bithumb_converter(coin)

        with self._lock_dic[Consts.TRADE]:
            self._subscriber.subscribe_trade(coin)

        return True
