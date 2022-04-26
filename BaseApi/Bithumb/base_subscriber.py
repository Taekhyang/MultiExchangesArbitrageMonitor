try:
    import thread
except ImportError:
    import _thread as thread

import json
import websocket
import gzip

from util import debugger
from BaseApi.Bithumb.config import Urls, BithumbConsts
from BaseApi.settings import Consts

from websocket import WebSocketConnectionClosedException
from threading import Event


class BithumbSubscriber(websocket.WebSocketApp):
    def __init__(self, data_store, lock_dic):
        """
            data_store: An object for storing orderbook&candle data, using orderbook&candle queue in this object.
            lock_dic: dictionary for avoid race condition, {orderbook: Lock, candle: Lock}
        """
        debugger.debug('BithumbSubscriber::: start')

        super(BithumbSubscriber, self).__init__(Urls.Websocket.BASE, on_message=self.on_message)

        websocket.enableTrace(True)
        self.data_store = data_store
        self.name = 'bithumb_subscriber'
        self._default_socket_id = 1
        self._unsub_id = 2
        self._stopped = Event()
        self._lock_dic = lock_dic

        self._candle_symbol_set = set()
        self._orderbook_symbol_set = set()
        self._trade_symbol_set = set()

        self.subscribe_set = dict()

        self.start_run_forever_thread()

    def _remove_contents(self, symbol, symbol_set):
        try:
            symbol_set.remove(symbol)
        except Exception as ex:
            debugger.debug('BithumbSubscriber::: remove error, [{}]'.format(ex))

    def _send_with_subscribe_set(self, topic):
        data = self.subscribe_set[topic]
        debugger.debug('Bithumb subscribe topic - [{}], subscribe set - [{}]'.format(topic, data))
        self.send(json.dumps(data))

    def start_run_forever_thread(self):
        debugger.debug('BithumbSubscriber::: start_run_forever_thread')
        self.subscribe_thread = threading.Thread(target=self.run_forever, daemon=True)
        self.subscribe_thread.start()

    def stop(self):
        self._stopped.set()

    def subscribe_orderbook(self, value):
        debugger.debug('BithumbSubscriber::: subscribe_orderbook')
        if isinstance(value, (list, tuple, set)):
            self._orderbook_symbol_set = self._orderbook_symbol_set.union(set(value))

        if Consts.ORDERBOOK not in self.subscribe_set:
            self.subscribe_set.setdefault(Consts.ORDERBOOK, dict())

        self.subscribe_set[Consts.ORDERBOOK] = {
            "type": "{}".format(BithumbConsts.ORDERBOOK),
            "symbols": list(self._orderbook_symbol_set)
        }
        self._send_with_subscribe_set(Consts.ORDERBOOK)

    def unsubscribe_orderbook(self, symbol):
        debugger.debug('BithumbSubscriber::: unsubscribe_orderbook')

        self._remove_contents(symbol, self._orderbook_symbol_set)
        self.subscribe_orderbook(symbol)

    def subscribe_trade(self, value):
        debugger.debug('BithumbSubscriber::: subscribe_trade')
        if isinstance(value, (list, tuple, set)):
            self._trade_symbol_set = self._trade_symbol_set.union(set(value))

        if Consts.TRADE not in self.subscribe_set:
            self.subscribe_set.setdefault(Consts.TRADE, dict())

        self.subscribe_set[Consts.TRADE] = {
            "type": "{}".format(BithumbConsts.TRADE),
            "symbols": list(self._trade_symbol_set)
        }
        self._send_with_subscribe_set(Consts.TRADE)

    def unsubscribe_trade(self, symbol):
        debugger.debug('BithumbSubscriber::: unsubscribe_trade')

        self._remove_contents(symbol, self._trade_symbol_set)
        self.subscribe_trade(symbol)

    def on_message(self, *args):
        message, *_ = args
        try:
            data = json.loads(message)
            type_ = data.get('type', None)
            if not type_:
                return

            if type_ == BithumbConsts.ORDERBOOK:
                self.orderbook_receiver(data)
            elif type_ == BithumbConsts.CANDLE:
                self.candle_receiver(data)
            elif type_ == BithumbConsts.TRADE:
                self.trade_receiver(data)

        except WebSocketConnectionClosedException:
            debugger.debug('BithumbSubscriber::: Disconnected orderbook websocket.')
            self.stop()
            raise WebSocketConnectionClosedException

        except Exception as ex:
            debugger.exception('BithumbSubscriber::: Unexpected error from Websocket thread.')
            self.stop()
            raise ex

    def candle_receiver(self, data):
        pass

    def orderbook_receiver(self, data):
        # data could contain more than one symbol
        with self._lock_dic[Consts.ORDERBOOK]:
            content = data['content']
            orderbook_list = content['list']

            _dic = dict()
            for each in orderbook_list:
                symbol = each['symbol']

                detail_list = _dic.setdefault(symbol, list())
                detail_list.append(each)

            for symbol in _dic:
                if symbol not in self.data_store.orderbook_queue:
                    self.data_store.orderbook_queue.setdefault(symbol, dict(bids=list(), asks=list()))
                else:
                    self.data_store.orderbook_queue[symbol] = dict(bids=list(), asks=list())

                for detail in detail_list:
                    price = detail['price']
                    amount = detail['quantity']
                    order_type = detail['orderType']

                    _detail = dict(price=price, amount=amount)

                    if order_type == Consts.BID:
                        self.data_store.orderbook_queue[symbol][Consts.BIDS].append(_detail)
                    elif order_type == Consts.ASK:
                        self.data_store.orderbook_queue[symbol][Consts.ASKS].append(_detail)

    def trade_receiver(self, data):
        with self._lock_dic[Consts.TRADE]:
            content = data['content']
            transaction_list = content['list']

            _dic = dict()
            for each in transaction_list:
                symbol = each['symbol']

                detail_list = _dic.setdefault(symbol, list())
                detail_list.append(each)

            for symbol in _dic:
                if symbol not in self.data_store.trade_queue:
                    self.data_store.trade_queue.setdefault(symbol, dict(buy=None, sell=None, latest=None))

                for detail in detail_list:
                    price = float(detail['contPrice'])
                    amount = float(detail['contQty'])
                    direction = Consts.SELL if detail['buySellGb'] == '1' else Consts.BUY

                    trade_ = dict(price=price, amount=amount)
                    self.data_store.trade_queue[symbol][direction] = trade_
                    self.data_store.trade_queue[symbol]['latest'] = trade_
