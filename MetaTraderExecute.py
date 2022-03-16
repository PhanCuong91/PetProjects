import MetaTrader5 as mt5
import os
import configparser
import logging
import sys



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
        logging.exception("The key is not defined")

def return_code(num):
    try:
        return config['RETURN_CODE'][str(num)]
    except KeyError:
        logging.exception("The key is not defined")

class PlaceOrder:
    
    def __init__(self, symbol, buyOrSell, entry, takeProfit, stopLoss, comment, trailingStop=False) -> None:
        self._symbol = symbol
        self._buyOrSell = buyOrSell
        self._entry = entry
        self._takeProfit = takeProfit
        self._stopLoss = stopLoss
        self._trailingStop = trailingStop
        self._comment = comment
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

    def place_order(self):
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
                    self._entry = self._entry*(1-(float(PERCENT/100)))
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
            "comment": self._comment,
            "deviation": self._deviation,
            "magic": 234000,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,}

        logging.info("PAIR: {}, ODER_TYPE: {}, PRICE: {}, TP: {}, SL: {}".format(self._symbol,order_type(self._type),self._entry,tp,sl))

        # send a trading request
        result = mt5.order_send(request)
        logging.info("OrderSend error {}".format(mt5.last_error()))  
        # check the execution result
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.info("Order_send failed, retcode= {}".format(return_code(result.retcode)))
            logging.info("Shutdown() and quit")
            self.shutdown()
            return -1
        self.shutdown()
        logging.info("This position was created successfully with order is {}".format(result.order)) 
        return result.order

    def shutdown(self):
        mt5.shutdown()

class ModifyPlacePosition:
    pass

if __name__ == "__main__":
    a = PlaceOrder("EURUSD.", 'SELL', 1.0000, 30,30)
    # a.initalize()
    # a.place_order()
    pass
    