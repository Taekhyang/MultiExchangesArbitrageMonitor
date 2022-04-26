import sqlite3
import threading

from util import debugger


DB_NAME = 'arbitrage_monitor'


class ArbitrageMonitorModel(object):
    def __init__(self):
        self.conn = None
        self.cursor = None
        self._lock = threading.Lock()

        self._connect()

    def migrate(self):
        self._create_excludes_table()

    def _create_excludes_table(self):
        with self._lock:
            sql = """
                CREATE TABLE IF NOT EXISTS exclude_set (
                arbitrage_type         VARCHAR(255) NOT NULL,
                trade_symbol           VARCHAR(255) NOT NULL,
                base_exchange          VARCHAR(255) NOT NULL,
                base_exchange_market   VARCHAR(255) NOT NULL,
                target_exchange        VARCHAR(255) NOT NULL,
                target_exchange_market VARCHAR(255) NOT NULL,
                PRIMARY KEY(arbitrage_type, trade_symbol, base_exchange, base_exchange_market, target_exchange, target_exchange_market)
            )
            """
            self.cursor.execute(sql)
            self.conn.commit()

    def _connect(self):
        self.conn = sqlite3.connect('{}.db'.format(DB_NAME), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # for dict

        self.cursor = self.conn.cursor()

    def get_excludes_list(self):
        with self._lock:
            sql = """
                SELECT * FROM exclude_set
            """

            for _ in range(3):
                try:
                    self.cursor.execute(sql)
                    break
                except Exception:
                    self.conn.close()
                    self._connect()
                    debugger.exception('get_excludes_list() ::: Error occurred while executing')
            else:
                debugger.warning('get_excludes_list() ::: tried several times but failed')
                return False

            _results = self.cursor.fetchall()
            results = [dict(result) for result in _results]
            return results

    def register_exclude(self, arbitrage_type, trade_symbol, base_exchange, base_exchange_market, target_exchange, target_exchange_market):
        """
            arbitrage_type: it should be either ArbitrageTypes.ORDERBOOK_HIGH_LOW or ArbitrageTypes.TRADE_PRICE
            trade_symbol: only trade symbol ex) BTC, ETH from KRW_BTC, USDT_ETH (sai)
            base_exchange: base exchange ex) Exchanges.BINANCE
            base_exchange_market: base exchange market ex) BTC, USDT from KRW_BTC, USDT_ETH (sai)
            target_exchange: target exchange
            target_exchange_market: target exchange market
        """
        with self._lock:
            sql = """
                INSERT OR IGNORE
                INTO exclude_set (arbitrage_type, trade_symbol, base_exchange, base_exchange_market, target_exchange, target_exchange_market)
                VALUES (?, ?, ?, ?, ?, ?)
            """

            values = (
                arbitrage_type,
                trade_symbol,
                base_exchange,
                base_exchange_market,
                target_exchange,
                target_exchange_market
            )

            for _ in range(3):
                try:
                    self.cursor.execute(sql, values)
                    self.conn.commit()
                    break
                except Exception:
                    self.conn.close()
                    self._connect()
                    debugger.exception('register_exclude() ::: Error occurred while executing, retry again')
            else:
                debugger.warning('register_exclude() ::: tried several times but failed')
                return False

            debugger.info('exclude set registered success ::: {}'.format(values))
            return True

    def revert_exclude(self, arbitrage_type, trade_symbol, base_exchange, base_exchange_market, target_exchange,
                         target_exchange_market):
        """
            arbitrage_type: it should be either ArbitrageTypes.ORDERBOOK_HIGH_LOW or ArbitrageTypes.TRADE_PRICE
            trade_symbol: only trade symbol ex) BTC, ETH from KRW_BTC, USDT_ETH (sai)
            base_exchange: base exchange ex) Exchanges.BINANCE
            base_exchange_market: base exchange market ex) BTC, USDT from KRW_BTC, USDT_ETH (sai)
            target_exchange: target exchange
            target_exchange_market: target exchange market
        """
        with self._lock:
            sql = """
                   DELETE FROM exclude_set
                   WHERE 
                    arbitrage_type = ? AND
                    trade_symbol = ? AND
                    base_exchange = ? AND
                    base_exchange_market = ? AND
                    target_exchange = ? AND
                    target_exchange_market = ?
               """

            values = (
                arbitrage_type,
                trade_symbol,
                base_exchange,
                base_exchange_market,
                target_exchange,
                target_exchange_market
            )

            for _ in range(3):
                try:
                    self.cursor.execute(sql, values)
                    self.conn.commit()
                    break
                except Exception:
                    self.conn.close()
                    self._connect()
                    debugger.exception('register_exclude() ::: Error occurred while executing, retry again')
            else:
                debugger.warning('register_exclude() ::: tried several times but failed')
                return False

            debugger.info('exclude set reverted success ::: {}'.format(values))
            return True


if __name__ == '__main__':
    model = ArbitrageMonitorModel()

    model.migrate()
    model.revert_exclude('orderbook_high_low', 'DOGE', 'upbit', 'KRW', 'bithumb', 'KRW')

    res = model.get_excludes_list()
    print(res)
