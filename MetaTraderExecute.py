import MetaTrader5 as mt5
import os
import configparser
import logging
import sys



VOLUME = 0.01
DEVIATION=50
BUY=1
SELL=0
TIMEOUT_COUNTER=10
PERCENT=0.5 #-> 0.5%
PIP=50
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

class MetaTrader:
    
    def __init__(self, ticket) -> None:
        print(ticket)
        self._ticket = ticket
        self._volume = VOLUME
        self._deviation = DEVIATION
        self._id = ID
        self._password = PASSWORD
        self._server = SERVER
        self._action = mt5.TRADE_ACTION_PENDING
        pass

    def initalize(self):
        if not mt5.initialize(login=ID,password=self._password,server=self._server):
            logging.error("initialize() failed, error code =",mt5.last_error())
            quit()
        logging.info("Initialize successful")
        pass
    
    def shutdown(self):
        mt5.shutdown()

    def place_order(self, symbol=None, volume=None, type=None, price=None, sl=None, tp=None, comment=None, trailing_stop=None):
        self.initalize()
        self._point= mt5.symbol_info(self._ticket['symbol']).point
        if symbol is not None:
            self._ticket['symbol'] = symbol
        if volume is not None:
            self._ticket['volume'] = volume
        if type is not None:
            self._ticket['type'] = type
        if price is not None:
            self._ticket['price'] = price
        if sl is not None:
            self._ticket['sl'] = sl*10*self._point
        if tp is not None:
            self._ticket['tp'] = tp*10*self._point
        if comment is not None:
            self._ticket['comment'] = comment
        if trailing_stop is not None:
            self._ticket['trailing_stop'] = trailing_stop
        if not self.prepare_ticket():
            logging.error("Error: Ticket preparation has error")
            return -1
        request = self.order_request()
        result = self.execute(request)
        if result is None:
            return -1
        logging.info("This position was created successfully with order is {}".format(result.order))
        self._ticket['id'] = result.order
        return self._ticket['id']

    def change_sl_tp_position(self, tp=None, sl=None, position=None, symbol=None):
        self._point= mt5.symbol_info(self._ticket['symbol']).point
        if position is not None:
            self._ticket['id'] = position
        if symbol is not None:
             self._ticket['symbol'] = symbol
        if tp is not None and sl is not None:
            self._ticket['tp']=tp*10*self._point
            self._ticket['sl']=sl*10*self._point
        elif tp is  None and sl is  None:
            self.prepare_tp_sl()
        else:
            logging.error("Error: SL and TP shall be set")
        request = self.order_request()
        result = self.execute(request)
        if result is None:
            return -1
        logging.info("Position {}: SL and TP were changed to {} and {}".format(result.order, self._ticket['sl'], self._ticket['tp']))
    
    def prepare_ticket(self):
        
        if self._ticket['order_type'] == "BUY" :
            ask_price = mt5.symbol_info(self._ticket['symbol'])._asdict()['ask']
            logging.info("Ask price: {}".format(ask_price))
            
            if abs(ask_price - self._ticket['price']) <= PIP*self._point:
                self._type = mt5.ORDER_TYPE_BUY
                self._action = mt5.TRADE_ACTION_DEAL
                self._ticket['price'] = ask_price
             # do a comparision to set buy stop or buy limit 
            else:
                if ask_price > self._ticket['price']: self._type = mt5.ORDER_TYPE_BUY_LIMIT
                else: self._type = mt5.ORDER_TYPE_BUY_STOP
            # calculate SL and TP
            self._ticket['sl']=self._ticket['price']-self._ticket['SL']*self._point
            if self._ticket['trailing_stop'] is not None:
                if self._ticket['trailing_stop']  in self._ticket: 
                    self._ticket['tp']=self._ticket['price']+self._ticket[self._ticket['trailing_stop']]*self._point
                else:
                    logging.error("Error: self._ticket does not have a key {}".format(self._ticket['trailing_stop']))
                    return False
        
        else:
            bid_price = mt5.symbol_info(self._ticket['symbol'])._asdict()['bid']
            logging.info("Bid price: {}".format(bid_price))

            if abs(bid_price - self._ticket['price']) <= PIP*self._point:
                self._type = mt5.ORDER_TYPE_SELL
                self._action = mt5.TRADE_ACTION_DEAL
                self._ticket['price'] = bid_price
            # do a comparision to set sell stop or sell limit
            else:
                if bid_price > self._ticket['price']: self._type = mt5.ORDER_TYPE_SELL_STOP
                else: self._type = mt5.ORDER_TYPE_SELL_LIMIT
            # calculate SL and TP
            self._ticket['sl']=self._ticket['price']+self._ticket['SL']*self._point
            if self._ticket['trailing_stop'] is not None:
                if self._ticket['trailing_stop']  in self._ticket: 
                    self._ticket['tp']=self._ticket['price']-self._ticket[self._ticket['trailing_stop']]*self._point
                else:
                    logging.error("Error: self._ticket does not have a key {}".format(self._ticket['trailing_stop']))
                    return False
        return True    

    def order_request(self):
        # create a request for crating new order or position
        request = {
            "action": self._action,
            "symbol": self._ticket['symbol'],
            "volume": self._volume,
            "type": self._type,
            "price": self._ticket['price'],
            "sl": self._ticket['sl'],
            "tp":self._ticket['tp'],
            "comment": self._ticket['comment'],
            "deviation": self._deviation,
            "magic": 234000,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,}
        logging.info("order request with symbol: {}, order_type: {}, price: {}, TP: {}, SL: {}, Trailing Stop: {}".format(self._ticket['symbol'],order_type(self._type),self._ticket['price'],self._ticket['tp'],self._ticket['sl'],self._ticket['trailing_stop']))
        return request

    def tp_sl_request(self):
        # create a request for changing sl and tp
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": self._ticket['symbol'],
            "position": self._ticket['id'],
            "sl": self._ticket['sl'],
            "tp": self._ticket['tp'],
            "magic": 234000,}
        logging.info("symbol: {}, order_type: {}, price: {}, TP: {}, SL: {}".format(self._ticket['symbol'],order_type(self._type),self._ticket['price'],self._ticket['tp'],self._ticket['sl']))
        return request

    def execute(self, request):
        # send a request
        result = mt5.order_send(request)
        logging.info("OrderSend {}".format(mt5.last_error()))  
        # check the execution result
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.info("Order_send failed, retcode= {}".format(return_code(result.retcode)))
            logging.info("Shutdown() and quit")
            return None
        self.shutdown()
        return result

    def prepare_tp_sl(self):
        ask_price = mt5.symbol_info(self._ticket['symbol'])._asdict()['ask']
        logging.info("Ask price 0: {}".format(ask_price))
        bid_price = mt5.symbol_info(self._ticket['symbol'])._asdict()['bid']
        logging.info("Ask price 0: {}".format(bid_price))
        if self._ticket['order_type'] == "BUY" :
            tp1=self._ticket['price']+self._ticket_detail['TP1']*self._point
            tp2=self._ticket['price']+self._ticket_detail['TP2']*self._point
            tp3=self._ticket['price']+self._ticket_detail['TP3']*self._point
            if ask_price>tp2:
                sl=tp1    
            elif ask_price>tp1:
                sl=self._ticket['price']
        else:
            tp1=self._ticket['price']-self._ticket_detail['TP1']*self._point
            tp2=self._ticket['price']-self._ticket_detail['TP2']*self._point
            tp3=self._ticket['price']-self._ticket_detail['TP3']*self._point
            if bid_price<tp2:
                sl=tp1
            elif bid_price<tp1:
                sl=self._ticket['price']
        tp = tp1
        if self._ticket['trailing_stop'] == 'TP3':
            tp = tp3
        elif self._ticket['trailing_stop'] == 'TP2':
            tp = tp2
        elif self._ticket['trailing_stop'] == 'TP1':
            tp = tp1
        self._ticket['tp']=tp
        self._ticket['sl']=sl
 

if __name__ == "__main__":
    order_detail = {'comment': '26004', 'symbol': 'GBPUSD.', 'order_type': 'SELL', 'price': 1.31131, 'Risk': 'high', 'TP1': 30, 'TP2': 56, 'TP3': 115, 'SL': 32, 'trailing_stop': 'TP3'}
    a = MetaTrader(order_detail)
    a.place_order()
    # a.initalize()
    # a.place_order()
    pass
    