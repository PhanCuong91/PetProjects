from telethon import TelegramClient,events
import MetaTrader5 as mt5
import configparser,re

# read config.ini file
config = configparser.ConfigParser()
config.read('config.ini')
# get telegram configuration
api_id = int(config['TELEGRAM']['api_id'])
api_hash = config['TELEGRAM']['api_hash']
# get meta trader 5 configuration
meta_trader_id = int(config['META_TRADER5']['id'])
meta_trader_password = config['META_TRADER5']['password']
meta_trader_server = config['META_TRADER5']['server']

# private_telegram_group = 'mForex - Private'
private_telegram_group = 'TÍN HIỆU FOREX - CHN SIGNAL'


VOLUME = 0.01 # volume of lot

def extractInfor(mess):
    """
    Input: mess gets from private telegram group
    this function is not a common function, due to the each signal of a group is different with other groups
    example: one group has a signal like this one bwlow in mess.text:

    #SCALPING #GBPCAD📊 
    #CHNBUYSELL
    BUY
    📌 Entry: NGAY hoặc 1.54595
    ✅ Target : 1.54851
    ❌ SL: 1.54340

    Return position detail from message if the message is a signal:
    symbol:  GBPCAD
    buy/sell: BUY
    price: NGAY
    take profit: 1.54851
    stop loss: 1.54340
    Return None, if not
    """
    # special removing #CHNBUYSELL
    mess.text = mess.text.replace("#CHNBUYSELL", "")
    # the message is a signal if it contains this text "PAIR"
    if re.search("^#SCALPING*", mess.text):
        position_detail = {"mess_id" : mess.id}
        matches = re.search(r'(GBP\w+|\w*USD\w*|CAD\w+|AUD\w+|NZD\w+|EUR\w+|CHF\w+)', mess.text)
        position_detail['symbol'] = matches[1]
        matches = re.search(r'(BUY|SELL)', mess.text)
        position_detail['order_type'] = matches[1]
        matches = re.search(r'Target+\s*:\s*(\d+.\d+)', mess.text)
        position_detail['tp'] = matches[1]
        matches = re.search(r'SL\s*:*\s*(\d+.\d+)', mess.text)
        position_detail['sl'] = matches[1]
        position_detail['date'] = mess.date.date()
        position_detail['time'] = mess.date.time()
        # if PAIR of position_detail has '.' at the end, then dont add '.' to the end
        if position_detail['symbol'][len(position_detail['symbol'])-1]!='.':
            position_detail['symbol'] = position_detail['symbol']+'.'
        position_detail['comment'] = "CHN - " + str(mess.id)
        matches = re.search('Entry\s*:\s*(NGAY)', mess.text)
        if matches is None:
            matches = re.search('Entry\s*:.*?(\d+.\d+)', mess.text)
            position_detail['price'] = matches[1]
        else:
            matches = re.search('Entry\s*:.*?(\d+.\d+)', mess.text)
            position_detail['second_price'] = matches[1]
            position_detail['price'] = "Now"

        return position_detail
    return None

def meta_trader(position_detail):
    if not mt5.initialize(login=meta_trader_id,password=meta_trader_password,server=meta_trader_server):
        print("initialize() failed, error code =",mt5.last_error())
        return None
    _order = {}
    _order['symbol'] = position_detail['symbol'] 
    _order['volume'] = VOLUME 
    _order['order_type'] = position_detail['order_type']
    _order['price'] = float(position_detail['entry'])
    _order['sl'] = float(position_detail['SL'])
    _order['tp'] = float(position_detail['TP'])

    # get bid and ask price to choose action and type accordingly
    _ask_price = mt5.symbol_info(_order['symbol'])._asdict()['ask']
    _bid_price = mt5.symbol_info(_order['symbol'])._asdict()['bid']

    if _order['order_type'] == "BUY" :
        _order['tp'] = _order['tp']
    else:
        _order['tp'] = _order['tp']
    print("Ask: {} , bid: {}".format(_ask_price,_bid_price))
    if position_detail['price'] == "Now":
        _order['price'] = _bid_price
        if _order['order_type'] == "BUY" :
            _order['action'] = mt5.TRADE_ACTION_DEAL
            _order['type'] = mt5.ORDER_TYPE_BUY
        else:
            _order['action'] = mt5.TRADE_ACTION_DEAL
            _order['type'] = mt5.ORDER_TYPE_SELL
    else:
        _order['price'] = float(position_detail['price'])
        # get bid and ask price to choose action and type accordingly
        # do a comparision to set buy, buy stop, buy limit, sell, sell stop and sell limit 
        """
        ******* case 1: entry price -> buy : BUY STOP - sell: SELL LIMIT *******
                    v
                    ||
        -----------ask price-------------
                    ^
                    ||
        ******* case 2: entry price -> market execution *******
                    ||
                    v
        -----------bid price-------------
                    ||
                    ^
        ******* case 3: entry price -> buy : BUY LIMT - sell: SELL STOP *******
        """
        _order['action'] = mt5.TRADE_ACTION_PENDING
        # case 1: 
        # buy : BUY STOP - sell: SELL LIMIT
        if _order['price'] > _ask_price:
            if _order['order_type'] == "BUY" :
                _order['type'] = mt5.ORDER_TYPE_BUY_STOP
            else:
                _order['type'] = mt5.ORDER_TYPE_SELL_LIMIT
        # case 3
        # buy : BUY LIMT - sell: SELL STOP
        elif _order['price'] < _bid_price:
            if _order['order_type'] == "BUY" :
                _order['type'] = mt5.ORDER_TYPE_BUY_LIMIT
            else:
                _order['type'] = mt5.ORDER_TYPE_SELL_STOP
        # case 2: market exectuion
        # buy or sell with market price
        else:
            if _order['order_type'] == "BUY" :
                _order['action'] = mt5.TRADE_ACTION_DEAL
                _order['type'] = mt5.ORDER_TYPE_BUY
            else:
                _order['action'] = mt5.TRADE_ACTION_DEAL
                _order['type'] = mt5.ORDER_TYPE_SELL
    print("type of volume: {}".format(type(_order['volume'])))
    request = {
    "action": _order['action'],
    "symbol": _order['symbol'],
    "volume": _order['volume'],
    "type": _order['type'],
    "price": _order['price'],
    "sl": _order['sl'],
    "tp":_order['tp'],
    # "comment": _order['comment'],
    "deviation": 50,
    "magic": 234000,
    "type_time": mt5.ORDER_TIME_DAY,
    # "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    # send a request
    print("request is: {}".format(request))
    result = mt5.order_send(request)
    print("result is {}".format(result))
    mt5.shutdown()
    if result == None or result.retcode != mt5.TRADE_RETCODE_DONE:
        print("Order_send failed, retcode={}".format(config['RETURN_CODE'][str(result.retcode) if result!=None else None]))
        return None
    else:
        print("Order_send succeed, retcode={}".format(config['RETURN_CODE'][str(result.retcode)]))
        # print(result._asdict())
        return result.order

def telegram():
    # access telegram   
    client = TelegramClient('anon', api_id, api_hash)
    if (client.is_connected()):
        client.disconnect()
    client.start()
    # creating an event when receiving message in private group
    @client.on(events.NewMessage(from_users=private_telegram_group))
    # above event shall trigger this fucntion 
    async def my_event_handler(event):
        print(event.message.text)
        # get position detail once having a signal
        posittion_detail = extractInfor(event.message)
        print(posittion_detail)
        if posittion_detail is not None: 
            # execute above position in meta trader
            # pass
            ticket = meta_trader(posittion_detail)
            if ticket is None:
                print("Ticket is not created")
            else:
                print("Ticket was created with id: {}".format(ticket))
        else:
            print("this message: < {} > is not a signal")
    client.run_until_disconnected()

if __name__ == "__main__":
    print("RUN SIMPLETELEGRAM")
    while(1):
        try:
            telegram()
        except ConnectionError as Err:
            pass
