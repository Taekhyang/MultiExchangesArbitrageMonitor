class OrderIdObject(object):
    def __init__(self, price, qty, currency, uuid, is_ask):
        self.price = price
        self.qty = qty
        self.currency = currency
        self.uuid = uuid
        self.is_ask = is_ask


class ResultObject(object):
    def __init__(self, success, data=None, message=str(), wait_time=int()):
        self.success = success
        self.data = data
        self.message = message
        self.wait_time = wait_time


class DataStore(object):
    def __init__(self):
        self.channel_set = dict()
        self.activated_channels = list()
        self.orderbook_queue = dict()
        self.balance_queue = dict()
        self.candle_queue = dict()
        self.trade_queue = dict()


class ExchangeInfo(object):
    """
        Exchange object for setting exchange's information like name, balance, fee and etc.
    """
    def __init__(self, name, log):
        self._log = log
        self.__name = None
        self.__name = name

        self.__exchange = None

        self.__balance = None
        self.__orderbook = None
        self.__td_fee = None
        self.__tx_fee = None
        self.__deposit = None

        self.__fee_cnt = None

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, val):
        self.__name = val

    @property
    def exchange(self):
        return self.__exchange

    @exchange.setter
    def exchange(self, val):
        self.__exchange = val

    @property
    def balance(self):
        return self.__balance

    @balance.setter
    def balance(self, val):
        self.__balance = val

    @property
    def orderbook(self):
        return self.__orderbook

    @orderbook.setter
    def orderbook(self, val):
        self.__orderbook = val

    @property
    def trading_fee(self):
        return self.__td_fee

    @trading_fee.setter
    def trading_fee(self, val):
        self.__td_fee = val

    @property
    def transaction_fee(self):
        return self.__tx_fee

    @transaction_fee.setter
    def transaction_fee(self, val):
        self.__tx_fee = val

    @property
    def fee_cnt(self):
        return self.__fee_cnt

    @fee_cnt.setter
    def fee_cnt(self, val):
        self.__fee_cnt = val

    @property
    def deposit(self):
        return self.__deposit

    @deposit.setter
    def deposit(self, val):
        self.__deposit = val
