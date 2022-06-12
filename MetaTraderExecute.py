import MetaTrader5 as mt5
import configparser, globalVariables,logging

VOLUME = 0.01
DEVIATION=50
BUY=1
SELL=0
TIMEOUT_COUNTER=10
PERCENT=0.5 #-> 0.5%
PIP=50
ADDING_PIP=5
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
                return False
            self._init = True
            logging.info("{}: Initialize is successful".format(desc))
            return True
        return False

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

        if not self.prepare_oder_sl_tp():
            self.shutdown()
            return -1
        if not self.prepare_ticket():
            logging.error("Error: Ticket preparation has error")
            self.shutdown()
            return -1
        request = self.order_request()
        result = self.execute(request)
        if DEBUG:
            # create arrays to log values
            results = []
            ask_prices= []
            bid_prices = []
            prices = []
        # attempt 2 more times
        ATTEMP = 2 
        while result.retcode != mt5.TRADE_RETCODE_DONE:
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
            if  len(results)<=ATTEMP:
                result = self.execute(request)
            else:
                break
        if len(results) == 0:
            logging.info("Ask price: {}".format(self._ask_price))
            logging.info("Bid price: {}".format(self._bid_price))
            logging.info("Order request with symbol: {}, order_type: {}, price: {}, TP: {}, SL: {}, Trailing Stop: {}, filling type {}".format(self._ticket['symbol'],order_type(self._type),self._ticket['price'],self._ticket['tp'],self._ticket['sl'],self._ticket['trailing_stop'], self._type_filling))
        else:
            if DEBUG:
                # print all logs
                logging.info("Retry creating the order {} time(s).".format(len(results)))
                for i in range(0,len(results)):
                    logging.info("Ask price {}: {}".format(i, ask_prices[i]))
                    logging.info("Bid price {}: {}".format(i, bid_prices[i]))
                    logging.info("Order_send failed, retcode of {}: {}".format(i,return_code(results[i])))
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
        # get bid and ask price to choose action and type accordingly
        self._ask_price = mt5.symbol_info(self._ticket['symbol'])._asdict()['ask']
        self._bid_price = mt5.symbol_info(self._ticket['symbol'])._asdict()['bid']
        if self._ask_price - self._bid_price > PIP*self._point:
            logging.info("Info: The spread is  more than {}. The market is volatile, then do not create any order.".format(PIP*self._point))
            return False
        # do a comparision to set buy, buy stop, buy limit, sell, sell stop and sell limit 
        if self._ticket['price'] > self._ask_price:
            self._action = mt5.TRADE_ACTION_PENDING
            if self._ticket['order_type'] == "BUY" :
                self._type = mt5.ORDER_TYPE_BUY_STOP
            else:
                self._type = mt5.ORDER_TYPE_SELL_LIMIT
        elif self._ticket['price'] < self._bid_price:
            self._action = mt5.TRADE_ACTION_PENDING
            if self._ticket['order_type'] == "BUY" :
                self._type = mt5.ORDER_TYPE_BUY_LIMIT
            else:
                self._type = mt5.ORDER_TYPE_SELL_STOP
        else:
            # TODO: need to improvise later
            if self._ticket['order_type'] == "BUY" :
                if abs(self._price - self._ask_price) < PIP*self._point:
                    self._ticket['price'] = self._ask_price+ADDING_PIP*self._point
            else:
                if abs(self._price - self._ask_price) < PIP*self._point:
                    self._ticket['price'] = self._bid_price-ADDING_PIP*self._point
            self.prepare_ticket()
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

    def __init__(self, position) -> None:
        super().__init__()
        self._position_type = None
        if position is not None:
            self._position = position
        else:
            logging.error("Error: position has not been set")
        # convert position as a dictionary
        self._position = position._asdict()


    def tp_sl_request(self):
        # create a request for changing sl and tp
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": self._position['symbol'],
            "position": self._position['ticket'],
            "sl": self._position['sl'],
            "tp": self._position['tp'],
            "magic": 234000,}
        return request

    def change_sl_tp_position(self, sl_pips= None, tp_pips = None):

        if sl_pips is None and tp_pips is None:
            self.shutdown()
            logging.info("There is no change in sl and tp. Since this, a new request for changing sl and tp shall be canceled")
            return -1
        # get new sl and tp
        if sl_pips is not None:
            self._sl_pips = sl_pips
            self._new_sl = self.create_new_sl()
            if self._new_sl is not None:
                self._position['sl'] = self._new_sl
        if tp_pips is not None:
            self._tp_pips = tp_pips    
            self._new_tp = self.create_new_tp()
            if self._new_tp is not None:
                self._position['tp'] = self._new_tp

        self.initalize()
        request = self.tp_sl_request()
        result = self.execute(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            self.shutdown()
            logging.error("Error: There is an error when creating a new request for changing sl and tp. The error is {}".format(return_code(result.retcode)))
            return -1
        logging.info("Position {}: price {}, SL was changed to {} and and TP was changed to {}".format(self._position['ticket'], self._position['price_open'], self._position['sl'], self._position['tp']))
        self.shutdown()
        return result

    def create_new_tp(self, type='default'):
        self.initalize()
        if self._tp_pips is None:
            return None
        if type == 'default':
            return None
        return None

    def create_new_sl(self, type = 'default'):
        self.initalize()
        if self._sl_pips is None:
            return None
        if type == 'default':
            if self._position_type is None:
                if  self._position['price_current'] > self._position['price_open']: 
                    if self._position['profit'] > 0.0: 
                        self._position_type = 'BUY'
                        logging.info("this is a {} position, because price current {} > price open {} and profit is {}".format(self._position_type,self._position['price_current'], self._position['price_open'],self._position['profit']))
                    elif self._position['profit'] < 0.0: 
                        self._position_type = 'SELL'
                        logging.info("this is a {} position, because price current {} > price open {} and profit is {}".format(self._position_type,self._position['price_current'], self._position['price_open'],self._position['profit']))
                elif self._position['price_current'] < self._position['price_open']:
                    if self._position['profit'] > 0.0:
                        self._position_type = 'SELL'
                        logging.info("this is a {} position, because price current {} > price open {} and profit is {}".format(self._position_type,self._position['price_current'], self._position['price_open'],self._position['profit']))
                    elif self._position['profit'] < 0.0: 
                        self._position_type = 'BUY'
                        logging.info("this is a {} position, because price current {} > price open {} and profit is {}".format(self._position_type,self._position['price_current'], self._position['price_open'],self._position['profit']))
                else:
                    return None
            
            self._point= mt5.symbol_info(self._position['symbol']).point  
            if self._position_type == 'BUY':
                sl = self._position['price_open'] + (self._sl_pips * self._point)
            else:
                sl = self._position['price_open'] - (self._sl_pips * self._point)
            # using abs(self._position['sl'] - sl) < self._point
            # due to self._position['sl'] is 162.527 and sl is 162.18900000000002
            if abs(self._position['sl'] - sl) < self._point:
                return None 
            else:
                logging.info("new sl is {}".format(sl))
                return sl
        return None

class GetOrdersPosition(MetaTraderInit):

    def __init__(self) -> None:
        super().__init__()

    def get_positions(self):
        if self.initalize(desc="Get all positions"):
            positions = mt5.positions_get()
            self.shutdown(desc="Get all positions")
            return positions
        logging.info("Cannot login to meta trader 5")
        return None
    def get_orders(self, ticket=None):
        self.initalize(desc="Get all orders")
        if ticket is None:
            orders = mt5.orders_get()
        else:
            orders = mt5.orders_get(ticket=ticket)
        self.shutdown(desc="Get all orders")
        return orders

class RemovePendingOrder(GetOrdersPosition):
    
    def __init__(self) -> None:
        super().__init__()
    
    def remove_pending_order(self, order_ticket):
        self._order_ticket = order_ticket
        order = self.get_orders(ticket=self._order_ticket)
        if order is None:
            logging.info("There is no pending order ticket {}".format(self._order_ticket))
        else:
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order ": self._order_ticket,}
            result = self.execute(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logging.error("Error: Removing pending order {} is failed with {}".format(self._order_ticket, return_code(result.retcode)))
                return False
            else:
                logging.info("Removing pending order {} is successfull".format(self._order_ticket))
                return True
import copy
if __name__ == "__main__":
    TEST_CREATE_ORDER = False
    GET_POSITION_FOR_TESTING = True 
    GETPOSITION = True
    if TEST_CREATE_ORDER:
        MetaTraderInit().initalize()
        ask =mt5.symbol_info('GBPJPY.')._asdict()['ask']
        bid =mt5.symbol_info('GBPJPY.')._asdict()['bid']
        price = bid + 3*mt5.symbol_info('GBPJPY.').point
        MetaTraderInit().shutdown()
        order_detail = {'comment': '26004', 'symbol': 'GBPJPY.', 'order_type': 'SELL', 'price': price, 'Risk': 'high', 'TP1': 30, 'TP2': 56, 'TP3': 620, 'SL': 320, 'trailing_stop': 'TP3'}
        print(type(order_detail))
        print('ask {},bid {}, price {}'.format(ask,bid, price))
        a = MetaTraderOrder(order_detail)
        a.place_order()
    if GET_POSITION_FOR_TESTING:
        positions = GetOrdersPosition().get_positions()
        print(type(positions))
        print(positions)
        v = []
        i = 0
        for pos in positions:
            v.append(pos._asdict())
            v[i]['mess_id'] = 10
            v[i]['TP2'] = 10
            v[i]['TP1'] = 10
            v[i]['sl_lvl'] = -1
            v[i]['id'] = pos._asdict()['identifier']
            i=i+1
        # ChangeSlTp(positions[0]).change_sl_tp_position(100)
        print(v)
    if GETPOSITION:
        positions = GetOrdersPosition().get_positions()
        # p1 = copy.copy(positions)
        cur_list_positions=[]
        pre_list_positions=[]
        for pos in positions:
            cur_list_positions.append(pos._asdict())
        # print(cur_list_positions)
        pre_list_positions=copy.copy(cur_list_positions)
        pre_list_positions.pop()
        # print(pre_list_positions)
        for pos in cur_list_positions :
            print(pos)
            if pos not in pre_list_positions:
                # pos is a removed tickets
                print('removed postion')
                print(pos)
        # for pos in positions:
        #     print(pos)

    pass
    