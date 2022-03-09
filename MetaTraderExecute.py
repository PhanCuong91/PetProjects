import MetaTrader5 as mt5
import os
import configparser
import logging
import sys

RETURN_CODE = {
10004 : "TRADE_RETCODE_REQUOTE (Requote)",
10006 : "TRADE_RETCODE_REJECT Request rejected",
10007 : "TRADE_RETCODE_CANCEL Request canceled by trader",
10008 : "TRADE_RETCODE_PLACED Order placed",
10009 : "TRADE_RETCODE_DONE Request completed",
10010 : "TRADE_RETCODE_DONE_PARTIAL Only part of the request was completed",
10011 : "TRADE_RETCODE_ERROR Request processing error",
10012 : "TRADE_RETCODE_TIMEOUT Request canceled by timeout",
10013 : "TRADE_RETCODE_INVALID Invalid request",
10014 : "TRADE_RETCODE_INVALID_VOLUME Invalid volume in the request",
10015 : "TRADE_RETCODE_INVALID_PRICE Invalid price in the request",
10016 : "TRADE_RETCODE_INVALID_STOPS Invalid stops in the request",
10017 : "TRADE_RETCODE_TRADE_DISABLED TRADE is disabled",
10018 : "TRADE_RETCODE_MARKET_CLOSED Market is closed",
10019 : "TRADE_RETCODE_NO_MONEY There is not enough money to complete the request",
10020 : "TRADE_RETCODE_PRICE_CHANGED Prices changed",
10021 : "TRADE_RETCODE_PRICE_OFF There are no quotes to process the request",
10022 : "TRADE_RETCODE_INVALID_EXPIRATION Invalid order expiration date in the request",
10023 : "TRADE_RETCODE_ORDER_CHANGED Order state changed",
10024 : "TRADE_RETCODE_TOO_MANY_REQUESTS Too frequent requests",
10025 : "TRADE_RETCODE_NO_CHANGES No changes in request",
10026 : "TRADE_RETCODE_SERVER_DISABLES_AT Autotrading disabled by server",
10027 : "TRADE_RETCODE_CLIENT_DISABLES_AT Autotrading disabled by client terminal",
10028 : "TRADE_RETCODE_LOCKED Request locked for processing",
10029 : "TRADE_RETCODE_FROZEN Order or position frozen",
10030 : "TRADE_RETCODE_INVALID_FILL Invalid order filling type",
10031 : "TRADE_RETCODE_CONNECTION No connection with the TRADE server",
10032 : "TRADE_RETCODE_ONLY_REAL Operation is allowed only for live accounts",
10033 : "TRADE_RETCODE_LIMIT_ORDERS The number of pending orders has reached the limit",
10034 : "TRADE_RETCODE_LIMIT_VOLUME The volume of orders and positions for the symbol has reached the limit",
10035 : "TRADE_RETCODE_INVALID_ORDER Incorrect or prohibited order type",
10036 : "TRADE_RETCODE_POSITION_CLOSED Position with the specified POSITION_IDENTIFIER has already been closed",
10038 : "TRADE_RETCODE_INVALID_CLOSE_VOLUME A close volume exceeds the current position volume",
10039 : "TRADE_RETCODE_CLOSE_ORDER_EXIST A close order already exists for a specified position. This may happen when working in the hedging system: when attempting to close a position with an opposite one, while close orders for the position already exist when attempting to fully or partially close a position if the total volume of the already present close orders and the newly placed one exceeds the current position volume",
10040 : "TRADE_RETCODE_LIMIT_POSITIONS The number of open positions simultaneously present on an account can be limited by the server settings. After a limit is reached, the server returns the TRADE_RETCODE_LIMIT_POSITIONS error when attempting to place an order. The limitation operates differently depending on the position accounting type: Netting — number of open positions is considered. When a limit is reached, the platform does not let placing new orders whose execution may increase the number of open positions. In fact, the platform allows placing orders only for the symbols that already have open positions. The current pending orders are not considered since their execution may lead to changes in the current positions but it cannot increase their number. Hedging — pending orders are considered together with open positions, since a pending order activation always leads to opening a new position. When a limit is reached, the platform does not allow placing both new market orders for opening positions and pending orders.",
10041 : "TRADE_RETCODE_REJECT_CANCEL The pending order activation request is rejected, the order is canceled",
10042 : "TRADE_RETCODE_LONG_ONLY The request is rejected, because the Only long positions are allowed rule is set for the symbol (POSITION_TYPE_BUY)",
10043 : "TRADE_RETCODE_SHORT_ONLY The request is rejected, because the Only short positions are allowed rule is set for the symbol (POSITION_TYPE_SELL)",
10044 : "TRADE_RETCODE_CLOSE_ONLY The request is rejected, because the Only position closing is allowed rule is set for the symbol",
10045 : "TRADE_RETCODE_FIFO_CLOSE The request is rejected, because Position closing is allowed only by FIFO rule flag is set for the trading account (ACCOUNT_FIFO_CLOSE=true)",
10046 : "TRADE_RETCODE_HEDGE_PROHIBITED The request is rejected, because the Opposite positions on a single symbol are disabled rule is set for the trading account. For example, if the account has a Buy position, then a user cannot open a Sell position or place a pending sell order. The rule is only applied to accounts with hedging accounting system (ACCOUNT_MARGIN_MODE=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING).",
}

VOLUME = 0.01
DEVIATION=20
BUY=1
SELL=0
TIMEOUT_COUNTER=10
PERCENT=0.5 #-> 0.5%
# read configuration from congfig.ini
# https://docs.python.org/3/library/configparser.html

config= configparser.ConfigParser()
config.read('config.ini')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("Execute.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logging.info('Program is started')

ID=int(config['META_TRADER5']['id'])
PASSWORD=config['META_TRADER5']['password']
SERVER=config['META_TRADER5']['server']

def order_type(num):
    try:
        return config['ORDER_TYPE'][str(num)]
    except KeyError:
        logging.exception("The key is not correct")

class MetaTraderExecute:
    
    def __init__(self, symbol, buyOrSell, entry, takeProfit, stopLoss, trailingStop=False) -> None:
        self._symbol = symbol
        self._buyOrSell = buyOrSell
        self._entry = entry
        self._takeProfit = takeProfit
        self._stopLoss = stopLoss
        self._trailingStop = trailingStop
        self._volume = VOLUME
        self._deviation = DEVIATION
        self._id = ID
        self._password = PASSWORD
        self._server = SERVER
        self._init = False
        pass

    def initalize(self):
        if not mt5.initialize(login=ID,password=self._password,server=self._server):
            logging.error("initialize() failed, error code =",mt5.last_error())
            quit()
        logging.info("Initialize successful")
        self._init = True
        pass

    def open(self):
        #initialize if initialization have not done yet
        if not self._init: 
            self.initalize()

        point = mt5.symbol_info(self._symbol,).point

        timeout=1
        # do a comparision to set buy stop or buy limit
        if self._buyOrSell == "BUY" :
            ask_price = mt5.symbol_info(self._symbol)._asdict()['ask']
            logging.info("Ask price 0: {}".format(ask_price))
            while ask_price == self._entry:
                ask_price = mt5.symbol_info(self._symbol)._asdict()['ask']
                logging.info("Ask price {}: {}".format(timeout,ask_price))
                if timeout == TIMEOUT_COUNTER:
                    self._entry = self._entry*(1+(float(PERCENT/100)))
                timeout=timeout+1
            if ask_price > self._entry: self._type = mt5.ORDER_TYPE_BUY_LIMIT
            else: self._type = mt5.ORDER_TYPE_BUY_STOP
            # calculate SL and TP
            sl=self._entry-self._stopLoss*point
            tp=self._entry+self._takeProfit*point
        # do a comparision to set sell stop or sell limit
        else:
            bid_price = mt5.symbol_info(self._symbol)._asdict()['bid']
            logging.info("Bid price 0: {}".format(bid_price))
            while bid_price == self._entry:
                bid_price = mt5.symbol_info(self._symbol)._asdict()['bid']
                logging.info("Bid price {}: {}".format(timeout,bid_price))
                if timeout == TIMEOUT_COUNTER:
                    self._entry = self._entry*(1+(float(PERCENT/100)))
                timeout=timeout+1
            if bid_price > self._entry: self._type = mt5.ORDER_TYPE_SELL_STOP
            else: self._type = mt5.ORDER_TYPE_SELL_LIMIT
            # calculate SL and TP
            sl=self._entry+self._stopLoss*point
            tp=self._entry-self._takeProfit*point

        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self._symbol,
            "volume": self._volume,
            "type": self._type,
            "price": self._entry,
            "sl": sl,
            "tp":tp,
            "deviation": self._deviation,
            "magic": 234000,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,}

        logging.info("PAIR: {}, ODER_TYPE: {}, PRICE: {}, TP: {}, SL: {}".format(self._symbol,order_type(self._type),self._entry,tp,sl))

        # send a trading request
        result = mt5.order_send(request)
        logging.info("OrderSend error %d",mt5.last_error());  
        # check the execution result
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.info("Order_send failed, retcode= {}".format(RETURN_CODE[result.retcode]))
            logging.info("Shutdown() and quit")
            self.shutdown()
            return -1
        self.shutdown()
        logging.info(self._symbol,self._buyOrSell,  self._entry)
        logging.info("This position was created successfully with order is {}".format(result.order)) 
        return result.order

    def shutdown(self):
        mt5.shutdown()

if __name__ == "__main__":
    a = MetaTraderExecute("EURUSD.", 'SELL', 1.0000, 30,30)
    a.initalize()
    a.open()
    pass
    