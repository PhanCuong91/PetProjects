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
private_telegram_group = 'me'

VOLUME = 0.01 # volume of lot

def extractInfor(mess):
    """
    Input: mess gets from private telegram group
    this function is not a common function, due to the each signal of a group is different with other groups
    example: one group has a signal like this one bwlow in mess.text:

    Open Price: 160.288
    Risk: high
    TP1: 160.18800000000002(30.00pip)
    TP2: 160.08800000000002(60.00pip)
    TP3: 159.988(81.00pip)
    SL: 160.388(30.00pip)

    It converts to text as:
    mess.text  is 'PAIR: XAUUSD\nTYPE: BUY\nOpen Price: 1889.93\nRisk: high\nTP1: 1892.93(30.00pip)\nTP2: 1895.93(60.00pip)\nTP3: 1898.03(81.00pip)\nSL: 1886.93(30.00pip)'
    Return position detail from message if the message is a signal:
    symbol
    buy/sell
    price
    take profit
    stop loss
    Return None, if not
    """
    # the message is a signal if it contains this text "PAIR"
    if re.search("^PAIR*", mess):
        
        position_detail = {}
        # get symbol
        matches  = re.search(r'(GBP\w+|\w*USD\w*|CAD\w+|AUD\w+|NZD\w+|EURD\w+|CHF\w+)', mess)
        position_detail['symbol'] = matches[1]
        # if symbol of position_detail has '.' at the end, then dont add '.' to the end
        if position_detail['symbol'][len(position_detail['symbol'])-1]!='.':
            position_detail['symbol'] = position_detail['symbol']+'.'
        
        # get buy/sell
        matches  = re.search(r'(BUY|SELL)', mess)
        position_detail['order_type'] = matches[1]
        
        # get take profit
        matches  = re.search(r'TP1\s*:\s*(\d+.\d+)', mess)
        position_detail['TP'] = matches[1]
        
        # get stop loss
        matches  = re.search(r'SL\s*:*\s*(\d+.\d+)', mess)
        position_detail['SL'] = matches[1]
 
        # get price
        matches  = re.search(r'Price\s*:*\s*(\d+.\d+)', mess)
        position_detail['entry'] = matches[1]

        return position_detail
    return None

def meta_trader(position_detail):
    if not mt5.initialize(login=meta_trader_id,password=meta_trader_password,server=meta_trader_server):
        print("initialize() failed, error code =",mt5.last_error())
        quit()
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
    if _order['price'] >= _ask_price:

        if _order['order_type'] == "BUY" :
            _order['type'] = mt5.ORDER_TYPE_BUY_STOP
        else:
            _order['type'] = mt5.ORDER_TYPE_SELL_LIMIT
    # case 3
    # buy : BUY LIMT - sell: SELL STOP
    elif _order['price'] <= _bid_price:

        if _order['order_type'] == "BUY" :
            _order['type'] = mt5.ORDER_TYPE_BUY_LIMIT
        else:
            _order['type'] = mt5.ORDER_TYPE_SELL_STOP
    # case 2: market exectuion
    else:
        if _order['order_type'] == "BUY" :
            _order['action'] = mt5.TRADE_ACTION_DEAL
            _order['type'] = mt5.ORDER_TYPE_BUY
        else:
            _order['action'] = mt5.TRADE_ACTION_DEAL
            _order['type'] = mt5.ORDER_TYPE_SELL

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
    result = mt5.order_send(request)
    mt5.shutdown()
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print("Order_send failed, retcode={}".format(config['RETURN_CODE'][str(result.retcode)]))
        return None
    else:
        print("Order_send succeed, retcode={}".format(config['RETURN_CODE'][str(result.retcode)]))
        print(result._asdict())
        return result.order

def telegram():
    # access telegram
    client = TelegramClient('anon', api_id, api_hash)
    client.start()
    # creating an event when receiving message in private group
    @client.on(events.NewMessage(from_users=private_telegram_group))
    # above event shall trigger this fucntion 
    async def my_event_handler(event):
        print(event.message.text)
        # get position detail once having a signal
        posittion_detail = extractInfor(event.message.text)
        print(posittion_detail)
        if posittion_detail is not None: 
            # execute above position in meta trader
            ticket = meta_trader(posittion_detail)
            if ticket is None:
                print("Ticket is not created")
            else:
                print("Ticket was created with id: {}".format(ticket))
        else:
            print("this message: < {} > is not a signal".format(event.message.text))
    client.run_until_disconnected()

if __name__ == "__main__":
    telegram()