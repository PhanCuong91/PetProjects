import MetaTrader5 as mt5
import os
import configparser

VOLUME = 0.01
DEVIATION=20
BUY=1
SELL=0
# read configuration from congfig.ini
# https://docs.python.org/3/library/configparser.html

config= configparser.ConfigParser()
config.read('config.ini')

ID=int(config['META_TRADER5']['id'])
PASSWORD=config['META_TRADER5']['password']
SERVER=config['META_TRADER5']['server']

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
        print(self._symbol,self._buyOrSell,  self._entry)
        pass

    def initalize(self):
        if not mt5.initialize(login=ID,password=self._password,server=self._server):
            print("initialize() failed, error code =",mt5.last_error())
            quit()
        print("Initialize successful")
        self._init = True
        pass


    def open(self):
        #initialize 
        if not self._init: 
            self.initalize()
        # get ask price
        ask_price = mt5.symbol_info(self._symbol)._asdict()['ask']
        print("Ask price : {}".format(ask_price))
        point = mt5.symbol_info(self._symbol,).point
        # do a comparision to set buy stop or buy limit
        if self._buyOrSell == "BUY" :
            if ask_price > self._entry: self._type = mt5.ORDER_TYPE_BUY_LIMIT
            else: self._type = mt5.ORDER_TYPE_BUY_STOP
            # calculate SL and TP
            sl=self._entry-self._stopLoss*point
            tp=self._entry+self._takeProfit*point
        # do a comparision to set sell stop or sell limit
        else:
            if ask_price > self._entry: self._type = mt5.ORDER_TYPE_SELL_STOP
            else: self._type = mt5.ORDER_TYPE_SELL_LIMIT
            # calculate SL and TP
            sl=self._entry+self._stopLoss*point
            tp=self._entry-self._takeProfit*point,
        
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

        # send a trading request
        result = mt5.order_send(request)
        print("OrderSend error %d",mt5.last_error());  
        # check the execution result
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print("Order_send failed, retcode={}".format(result.retcode))
            print("Shutdown() and quit")
            self.shutdown()
            
        self.shutdown()
        return result.order

    def shutdown(self):
        mt5.shutdown()

if __name__ == "__main__":
    a = Execute("EURUSD.", BUY, 1.10000, 300,300)
    a.initalize()
    # a.open()
    pass
    