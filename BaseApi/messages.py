class WarningMessage(object):
    MESSAGE_NOT_FOUND = '[{name}]응답 메세지를 찾을 수 없습니다.'
    ORDERBOOK_NOT_STORED = '[{name}]오더북 데이터를 찾을 수 없습니다.'
    CANDLE_NOT_STORED = '[{name}]캔들 데이터를 찾을 수 없습니다.'
    TRADE_NOT_STORED = '[{name}]체결 데이터를 찾을 수 없습니다.'
    PRECISION_NOT_FOUND = '[{name}]호가 정보를 찾을 수 없습니다.'
    TRANSACTION_FAILED = '[{name}] 출금 비용 정보를 찾을 수 없습니다.'
    EXCEPTION_RAISED = '[{name}] 정상적으로 프로그램이 동작하지 않았습니다. 작성자에게 문의 부탁드립니다.'
    FAIL_MESSAGE_BODY = '[{name}] 정상적으로 동작하지 않았습니다. 원인은 다음과 같습니다. [{message}]'


class CriticalMessage(object):
    pass


class MessageDebug(object):
    ENTRANCE = '{name}, fn={fn}, data={join_data}'
    FAIL_RESPONSE_DETAILS = '{name}, body: [{body}], path: [{path}], parameter: [{parameter}]'
