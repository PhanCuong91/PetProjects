import MetaTrader5 as mt5

import configparser, globalVariables,logging

VOLUME = 0.01
DEVIATION=50
BUY=1
SELL=0
TIMEOUT_COUNTER=10
PERCENT=0.5 #-> 0.5%
PIP=50
DEBUG = True
# read configuration from congfig.ini
# https://docs.python.org/3/library/configparser.html

config= configparser.ConfigParser()
config.read('config.ini')

# define log for whole project
globalVariables.log

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

class MetaTraderInit:

    def __init__(self) -> None:
        self._id = ID
        self._password = PASSWORD
        self._server = SERVER
        self._init = False

    def initalize(self, desc=""):
        if not self._init:
            if not mt5.initialize(login=self._id,password=self._password,server=self._server):
                logging.error("initialize() failed, error code =",mt5.last_error())
                quit()
            self._init = True
            logging.info("{}: Initialize is successful".format(desc))   

    def shutdown(self, desc=""):
        if self._init:
            mt5.shutdown()
            logging.info("{}: Shutdown is successful".format(desc))  

    def execute(self, request):
        # send a request
        result = mt5.order_send(request)
        logging.info("OrderSend {}".format(mt5.last_error()))  
        return result

class MetaTraderOrder(MetaTraderInit):
    
    def __init__(self, ticket) -> None:
        super().__init__()
        self._ticket = ticket
        self._volume = VOLUME
        self._deviation = DEVIATION
        self._id = ID
        self._password = PASSWORD
        self._server = SERVER
        self._type_filling = mt5.ORDER_FILLING_RETURN
        self._price = self._ticket['price']
        pass

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
        if DEBUG:
            # create arrays to log values
            results = []
            ask_prices= []
            bid_prices = []
            prices = []
        if not self.prepare_oder_sl_tp():
            self.shutdown()
            return -1
        if not self.prepare_ticket():
            logging.error("Error: Ticket preparation has error")
            self.shutdown()
            return -1
        request = self.order_request()
        result = self.execute(request)
        count = 1

        # attempt 2 more times
        ATTEMP = 2 
        while result.retcode != mt5.TRADE_RETCODE_DONE :
            if DEBUG:
                # log values to arrays
                results.append(result.retcode)
                ask_prices.append(self._ask_price)
                bid_prices.append(self._bid_price)
                prices.append(request["price"])
            # The request has created. Then the request shall be not re-created
            # The entry price shall be changed
            self.prepare_ticket()
            request["price"] = self._ticket['price']
            if  count<=ATTEMP:
                result = self.execute(request)
            else:
                break
            count=count+1
        if DEBUG:
            # print all logs
            logging.info("Retry creating the order {} time(s).".format(count))
            for i in range(0,count):
                logging.info("Ask price {}: {}".format(i, ask_prices[i]))
                logging.info("Bid price {}: {}".format(i, bid_prices[i]))
                logging.info("Order_send failed, retcode of {}: {}".format(i,return_code(results[i])))
                logging.info("Order request with symbol: {}, order_type: {}, price: {}, TP: {}, SL: {}, Trailing Stop: {}, filling type {}".format(self._ticket['symbol'],order_type(self._type),self._ticket['price'],self._ticket['tp'],self._ticket['sl'],self._ticket['trailing_stop'], self._type_filling))
        if count == 1:
            logging.info("Order request with symbol: {}, order_type: {}, price: {}, TP: {}, SL: {}, Trailing Stop: {}, filling type {}".format(self._ticket['symbol'],order_type(self._type),self._ticket['price'],self._ticket['tp'],self._ticket['sl'],self._ticket['trailing_stop'], self._type_filling))
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            self.shutdown()
            return -1
        logging.info("This position was created successfully with order is {}".format(result.order))
        self._ticket['id'] = result.order
        self.shutdown()
        return self._ticket['id']

    def prepare_oder_sl_tp(self):
        # calculate SL and TP
        if self._ticket['order_type'] == "BUY" :
            self._ticket['sl']=self._ticket['price']-self._ticket['SL']*self._point
            if self._ticket['trailing_stop'] is not None:
                if self._ticket['trailing_stop']  in self._ticket: 
                    self._ticket['tp']=self._ticket['price']+self._ticket[self._ticket['trailing_stop']]*self._point
                else:
                    logging.error("Error: self._ticket does not have a key {}".format(self._ticket['trailing_stop']))
                    return False
        else:
            self._ticket['sl']=self._ticket['price']+self._ticket['SL']*self._point
            if self._ticket['trailing_stop'] is not None:
                if self._ticket['trailing_stop']  in self._ticket: 
                    self._ticket['tp']=self._ticket['price']-self._ticket[self._ticket['trailing_stop']]*self._point
                else:
                    logging.error("Error: self._ticket does not have a key {}".format(self._ticket['trailing_stop']))
                    return False
        return True

    def prepare_ticket(self):
        
        self._ask_price = mt5.symbol_info(self._ticket['symbol'])._asdict()['ask']
        self._bid_price = mt5.symbol_info(self._ticket['symbol'])._asdict()['bid']
        if self._ask_price - self._bid_price > PIP*self._point:
            logging.info("Info: The spread is  more than {}. The market is volatile, then do not create any order.".format(PIP*self._point))
            return False
        # do a comparision to set buy, buy stop, buy limit, sell, sell stop and sell limit 
        if self._ticket['price'] > self._ask_price:
            self._action = mt5.TRADE_ACTION_PENDING
            if self._ticket['order_type'] == "BUY" :
                self._type = mt5.ORDER_TYPE_BUY_LIMIT
            else:
                self._type = mt5.ORDER_TYPE_SELL_LIMIT
        elif self._ticket['price'] < self._bid_price:
            self._action = mt5.TRADE_ACTION_PENDING
            if self._ticket['order_type'] == "BUY" :
                self._type = mt5.ORDER_TYPE_BUY_STOP
            else:
                self._type = mt5.ORDER_TYPE_SELL_STOP
        else:
            self._action = mt5.TRADE_ACTION_DEAL
            if self._ticket['order_type'] == "BUY" :
                self._type = mt5.ORDER_TYPE_BUY
                if abs(self._price - self._ask_price) < PIP*self._point:
                    self._ticket['price'] = self._ask_price
            else:
                self._type = mt5.ORDER_TYPE_SELL
                if abs(self._price - self._ask_price) < PIP*self._point:
                    self._ticket['price'] = self._bid_price
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
            "type_filling": self._type_filling,}
        return request

class ChangeSlTp(MetaTraderInit):

    def __init__(self, position, sl_pips) -> None:
        super().__init__()
        self._postion_type = None
        self._position = position
        if sl_pips is not None:
            self._sl_pips = sl_pips
        else:
            logging.error("Error: sl_pips has been not set")

    def tp_sl_request(self):
        # create a request for changing sl and tp
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": self._postion['symbol'],
            "position": self._postion['id'],
            "sl": self._postion['sl'],
            "tp": self._postion['tp'],
            "magic": 234000,}
        return request

    def prepare_tp_sl(self):
        '''
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
        '''
        if self._postion_type is None:
            if self._postion['profit'] > 0.0:
                if  self._postion['price_current'] > self._postion['price_open']: 
                    self._postion_type = 'BUY'
                elif self._postion['price_current'] < self._postion['price_open']:
                    self._postion_type = 'SELL'
                else:
                    pass
            elif self._postion['profit'] < 0.0:
                if  self._postion['price_current'] > self._postion['price_open']: 
                    self._postion_type = 'SELL'
                elif self._postion['price_current'] < self._postion['price_open']:
                    self._postion_type = 'BUY'
                else:
                    pass
            else: 
                pass
        if self._postion_type == 'BUY':
            if self._new_sl is not None:
                self._postion['sl'] = self._postion['price_open'] - self._new_sl 
            if self._new_tp is not None:
                self._postion['tp'] = self._postion['price_open'] + self._new_tp                
        else:
            if self._new_sl is not None:
                self._postion['sl'] = self._postion['price_open'] + self._new_sl 
            if self._new_tp is not None:
                self._postion['tp'] = self._postion['price_open'] - self._new_tp 

    def change_sl_tp_position(self, position=None):
        self.initalize()
        # change sl and tp
        if position is not None:
            self._postion = position
        else:
            logging.error("Error: position has not been set")
         
        self._new_sl = self.create_new_sl()
        self._new_tp = self.create_new_tp()
        if self._new_sl is not None:
            self._postion['sl'] = self._new_sl
        if self._new_tp is not None:
            self._postion['tp'] = self._new_tp
        if self._new_tp is None and self._new_sl is None:
            self.shutdown()
            logging.info("There is no change in sl and tp. Since this, a new request for changing sl and tp shall be canceled")
            return -1
        request = self.tp_sl_request()
        result = self.execute(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            self.shutdown()
            logging.error("Error: There is an error when creating a new request for changing sl and tp. The error is {}".format(return_code(result.retcode)))
            return -1
        logging.info("Position {}: price {}, SL was changed to {} and and TP was changed to {}".format(result.order, self._position['price'], self._postion['sl'], self._postion['tp']))
        self.shutdown()
        return result

    def create_new_tp(self, type='default'):
        if type == 'default':
            return None
        return None

    def create_new_sl(self, type = 'default'):
        if type == 'default':
            if self._postion_type is None:
                if  self._position['price_current'] > self._position['price_open']: 
                    if self._position['profit'] > 0.0: self._postion_type = 'BUY'
                    elif self._position['profit'] < 0.0: self._postion_type = 'SELL'
                elif self._position['price_current'] < self._position['price_open']:
                    if self._position['profit'] > 0.0:self._postion_type = 'SELL'
                    elif self._position['profit'] < 0.0: self._postion_type = 'BUY'
                else:
                    return None
            self._point= mt5.symbol_info(self._postion['symbol']).point  
            if self._postion_type == 'BUY':
                return self._position['price_open'] + (self._sl_pips * self._point)
            else:
                return self._position['price_open'] - (self._sl_pips * self._point)
        return None

class CreateNewSlTp(MetaTraderInit):
    def __init__(self, position, condition=None) -> None:
        super().__init__()
        self._position = position
        if condition is not None:
            self._condition = condition
        else:
            logging.error("Error: Condition has been not set")
    
    def create_new_sl(self, type = 'default'):
        if type == 'default':
            if self._postion_type is None:
                if self._position['profit'] > 0.0:
                    if  self._position['price_current'] > self._position['price_open']: 
                        self._postion_type = 'BUY'
                    elif self._position['price_current'] < self._position['price_open']:
                        self._postion_type = 'SELL'
                    else:
                        pass
                elif self._position['profit'] < 0.0:
                    if  self._position['price_current'] > self._position['price_open']: 
                        self._postion_type = 'SELL'
                    elif self._position['price_current'] < self._position['price_open']:
                        self._postion_type = 'BUY'
                    else:
                        pass
                else: 
                    pass
             
            self._point= mt5.symbol_info(self._postion['symbol']).point     
            if self._postion_type == 'BUY':
                if self._position['price_current'] >= self._position['price_open'] + self._condition['TP2']*self._point:
                    return self._position['price_open']+self._condition['TP1']
                elif self._position['price_current'] >= self._position['price_open'] + self._condition['TP1']*self._point:
                    return self._position['price_open'] 
            else:
                if self._position['price_current'] <= self._position['price_open'] - self._condition['TP2']*self._point:
                    return self._position['price_open'] - self._condition['TP1'] 
                elif self._position['price_current'] <= self._position['price_open'] - self._condition['TP1']*self._point:
                    return self._position['price_open']       
        return None

class GetOrdersPosition(MetaTraderInit):

    def __init__(self) -> None:
        super().__init__()

    def get_positions(self):
        self.initalize(desc="Get all positions")
        positions = mt5.positions_get()
        self.shutdown(desc="Get all positions")
        return positions
    
    def get_orders(self):
        self.initalize(desc="Get all orders")
        orders = mt5.orders_get()
        self.shutdown(desc="Get all orders")
        return orders
 
if __name__ == "__main__":
    order_detail = {'comment': '26004', 'symbol': 'GBPUSD.', 'order_type': 'SELL', 'price': 1.31131, 'Risk': 'high', 'TP1': 30, 'TP2': 56, 'TP3': 115, 'SL': 32, 'trailing_stop': 'TP3'}
    a = MetaTraderOrder(order_detail)
    a.place_order()
    # a.initalize()
    # a.place_order()
    pass
    