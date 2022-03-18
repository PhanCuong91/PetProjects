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
PIP=30
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
    
    def __init__(self, order_detail) -> None:
        self._symbol = order_detail['symbol']
        self._buyOrSell = order_detail['order_type']
        self._entry = float(order_detail['price'])
        self._trailingStop = order_detail['trailing_stop']
        if self._trailingStop == 'TP3':
            self._takeProfit = order_detail['TP3']*10
        elif self._trailingStop == 'TP2':
            self._takeProfit = order_detail['TP2']*10
        elif self._trailingStop == 'TP1':
            self._takeProfit = order_detail['TP1']*10
        self._stopLoss = order_detail['SL']*10
        self._comment = order_detail['comment']
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

        point = mt5.symbol_info(self._symbol).point

        timeout=1
        # do a comparision to set buy stop or buy limit
        if self._buyOrSell == "BUY" :
            ask_price = mt5.symbol_info(self._symbol)._asdict()['ask']
            logging.info("Ask price 0: {}".format(ask_price))
            while ask_price == self._entry:
                ask_price = mt5.symbol_info(self._symbol)._asdict()['ask']
                logging.info("Ask price {}: {}".format(timeout,ask_price))
                if timeout == TIMEOUT_COUNTER:
                    self._entry = self._entry+(PIP*point)
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
                    self._entry = self._entry-(PIP*point)
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

        logging.info("symbol: {}, order_type: {}, price: {}, TP: {}, SL: {}, Trailing Stop: {}".format(self._symbol,order_type(self._type),self._entry,tp,sl,self._trailingStop))

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

class ModifyPosition:
    def __init__(self, ticket_detail) -> None:
        self._ticket_detail=ticket_detail
        self._symbol = ticket_detail['symbol']
        self._position= ticket_detail['meta_ticket_id']
        self._buyOrSell = ticket_detail['order_type']
        self._entry = ticket_detail['price']

    def initalize(self):
        if not mt5.initialize(login=ID,password=self._password,server=self._server):
            logging.error("initialize() failed, error code =",mt5.last_error())
            quit()
        logging.info("Initialize successful")
        self._init = True
        pass

    def shutdown(self):
        mt5.shutdown()

    def changeStopLoss(self, type_stop_loss='TP3'):
        #initialize if initialization have not done yet
        if not self._init: 
            self.initalize()
        point = mt5.symbol_info(self._symbol,).point

        ask_price = mt5.symbol_info(self._symbol)._asdict()['ask']
        bid_price = mt5.symbol_info(self._symbol)._asdict()['bid']
        if self._buyOrSell == "BUY" :
            tp1=self._entry+self._ticket_detail['TP1']*point
            tp2=self._entry+self._ticket_detail['TP2']*point
            tp3=self._entry+self._ticket_detail['TP3']*point
            if ask_price>tp2:
                sl=tp1    
            elif ask_price>tp1:
                sl=self._entry
        else:
            tp1=self._entry-self._ticket_detail['TP1']*point
            tp2=self._entry-self._ticket_detail['TP2']*point
            tp3=self._entry-self._ticket_detail['TP3']*point
            if bid_price<tp2:
                sl=tp1
            elif bid_price<tp1:
                sl=self._entry
        tp = tp1
        if type_stop_loss == 'TP3':
            tp = tp3
        elif type_stop_loss == 'TP2':
            tp = tp2
        elif type_stop_loss == 'TP1':
            tp = tp1
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": self._symbol,
            "position": self._position,
            "sl": sl,
            "tp": tp,
            "magic": 234000,}

        logging.info("symbol: {}, order_type: {}, price: {}, new SL: {}".format(self._symbol,order_type(self._type),self._entry,sl))
        
        # send a trading request
        result = mt5.order_send(request)
        logging.info("OrderSend error {}".format(mt5.last_error()))  
        # check the execution result
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.info("Order_send failed, retcode= {}".format(return_code(result.retcode)))
            logging.info("Shutdown() and quit")
        self.shutdown()

if __name__ == "__main__":
    # a = PlaceOrder("EURUSD.", 'SELL', 1.0000, 30,30)
    order_detail = {'comment': '26004', 'symbol': 'GBPUSD.', 'order_type': 'SELL', 'price': '1.31131', 'Risk': 'high', 'TP1': 30, 'TP2': 56, 'TP3': 115, 'SL': 32, 'trailing_stop': 'TP3'}
    a = PlaceOrder(order_detail)
    a.place_order()
    # a.initalize()
    # a.place_order()
    pass
    