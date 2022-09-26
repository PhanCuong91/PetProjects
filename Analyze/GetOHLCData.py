
import MetaTrader5 as mt5
import pandas as pd
import configparser
from datetime import datetime,timedelta,timezone

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

def get_all_forex_symbols(init=True):
    # must innitialize first
    if init:
        if not mt5.initialize(login=meta_trader_id,password=meta_trader_password,server=meta_trader_server):
            print("initialize() failed, error code =",mt5.last_error())
    # All forex symbols end with dot. EX: EURUSD.
    # get all symbols which end by ".", 
    symbols=mt5.symbols_get(group="*.")
    # convert it to dataframe
    forex_symbols = pd.DataFrame(list(symbols),columns = symbols[0]._asdict().keys())
    # keep only name column
    forex_symbols = forex_symbols.filter(['name'])
    # All forxr symbols will have 6 characters plus dot symbol -> 7 characters
    forex_symbols=forex_symbols[forex_symbols['name'].str.len() == 7]
    if init:
        mt5.shutdown()
    return forex_symbols

def get_tick_data_from_MT5(_from_date=datetime(2022, 8, 4,tzinfo=timezone.utc), _to_date=datetime(2022, 8, 5,tzinfo=timezone.utc), _pair="AUDCAD."):
    """
    Reference this link: https://www.mql5.com/en/docs/integration/python_metatrader5/mt5copyticksrange_py
    Tick data have only bid and ask price once a trade happen on system. 
    Timezone must be utc to avoid local timezone
    """
    if _from_date > _to_date:
        raise ValueError("_from_date should less than _to_date")
    # initialize to Meta Trader 5
    if not mt5.initialize(login=meta_trader_id,password=meta_trader_password,server=meta_trader_server):
        print("Initialize() failed, error code =",mt5.last_error())
    # get all symbols and verify whether_pair parameter is correct or not
    # this is optional. It is disable as defautl. if you want to use, use condition 1==1. 
    if 1==0:
        forex_symbols=get_all_forex_symbols(False)
        if  _pair not in forex_symbols['name'].to_numpy():
            forex_symbols=forex_symbols[forex_symbols['name'].str.match(_pair)]
            print("Pair parameter is incorrect, please use this value for pair parameter {}".format(forex_symbols['name'].values))
            return None
    # copy all ticks from from_date to to_date
    ticks = mt5.copy_ticks_range(_pair, _from_date, _to_date, mt5.COPY_TICKS_ALL)
    # shut down connection to the MetaTrader 5 terminal
    mt5.shutdown()
    return ticks
def convert_tick_data_2_ohlc_dat(ticks , _time_frame='15Min'):
    """
    this function convert tick data (bid and ask price) to OHLC data of bid and ask
    this OHLC data of bid and ask help us simulate the market properly. 
    If you execute a buy position, you will buy at ask price. After holding, you close the position at bid price
    On the other hand, If you execute a sell position, you will sell at bid price. After holding, you close the position at ask price 
    """
    # print("Ticks received:",len(ticks))
    if len(ticks) != 0:
        # create DataFrame out of the obtained data
        ticks_frame = pd.DataFrame(ticks)
        # convert time in seconds into the datetime format
        ticks_frame['time']=pd.to_datetime(ticks_frame['time'], unit='s')
        # set time as index of dataframe, due to resample should use datatimeIndex as default
        ticks_frame = ticks_frame.set_index(ticks_frame['time'])
        # remove time column
        ticks_frame.drop('time',axis=1,inplace=True)
        df = pd.DataFrame()
        for s in ["bid", "ask"]:
            # convert tick data to "ohlc" data
            resample = ticks_frame[s].resample(_time_frame).ohlc(_method='ohlc')
            # print("{} data frame: {}".format(s, resample.head(2)))
            if s == "bid":
                df = df.append(resample)
                df.drop(['open','high','low','close'],axis=1,inplace=True)
            df['%s_open' % s]=resample['open']
            df['%s_high' % s]=resample['high']
            df['%s_low' % s]=resample['low']
            df['%s_close' % s]=resample['close']
        df=df.fillna(method='ffill')
        # print(df.head(2))
        return df
    else:
        print("from {} to {}: dont have any ticks".format(from_date,to_date))
    return None

def save_data_2_df(_pair="AUDCAD.", _from_date=[2022,8,1], _to_date=[2022,8,2], _time_frame="1Min"):
    """
    This funciton will save converted tick data to ohlc data as dataframe:
                            bid_open  bid_high  bid_low  bid_close  ask_open  ask_high  ask_low  ask_close
    time
    2022-08-02 00:00:00   0.90174   0.90329  0.90161    0.90234   0.90191   0.90346  0.90178    0.90251
    2022-08-02 01:00:00   0.90236   0.90267  0.90196    0.90254   0.90253   0.90284  0.90213    0.90271

    pair shall be one element in the array: [ 'AUDCAD.', 'AUDCHF.', 'AUDJPY.', 'AUDNZD.', 'CADCHF.', 'CADJPY.', 'CHFJPY.',
     'EURAUD.', 'EURCAD.', 'EURCHF.', 'EURGBP.', 'EURJPY.', 'EURNZD.', 'GBPAUD.', 'GBPCAD.', 
     'GBPCHF.', 'GBPJPY.', 'GBPNZD.', 'NZDCAD.', 'NZDCHF.', 'NZDJPY.', 'AUDUSD.', 'EURUSD.', 
     'GBPUSD.', 'NZDUSD.', 'USDCAD.', 'USDCHF.', 'USDJPY.']
    _from_date and _to_date shall be an array[3]. first, second and third element of the array represent to year (format:"YYYY"), month (format:"M"), day (format:"D") respectively
    time frame will be [day: "D", hour: "H", minute: "Min", second: "S", milisecond: "L", microsecond: "U"]
    """
    # convert to utc to avoid local time zone
    from_date=datetime(_from_date[0],_from_date[1],_from_date[2],tzinfo=timezone.utc)
    to_date=datetime(_to_date[0],_to_date[1],_to_date[2],tzinfo=timezone.utc)
    # assert date input
    if from_date > to_date:
        raise ValueError("from_date should less than to_date")
    
    df = pd.DataFrame()
    
    time_del = timedelta(days=1)
    while from_date<to_date:
        # convert tick data to ohlc data within a day
        ticks=get_tick_data_from_MT5(_from_date=from_date, _to_date=from_date+time_del,  _pair=_pair)
        # append data frame of each day
        df=df.append(convert_tick_data_2_ohlc_dat(ticks,_time_frame=_time_frame))
        # increase from_date to 1 day
        from_date=from_date+time_del
    return df

def save_data_2_excel(_pair="AUDCAD.", _from_date=[2022,8,1], _to_date=[2022,8,2], _time_frame="1Min", path_and_name=None):
    """
    This funciton will save converted tick data to ohlc data, then save to excel file:
                            bid_open  bid_high  bid_low  bid_close  ask_open  ask_high  ask_low  ask_close
    time
    2022-08-02 00:00:00   0.90174   0.90329  0.90161    0.90234   0.90191   0.90346  0.90178    0.90251
    2022-08-02 01:00:00   0.90236   0.90267  0.90196    0.90254   0.90253   0.90284  0.90213    0.90271
    
    pair shall be one element in the array: [ 'AUDCAD.', 'AUDCHF.', 'AUDJPY.', 'AUDNZD.', 'CADCHF.', 'CADJPY.', 'CHFJPY.',
     'EURAUD.', 'EURCAD.', 'EURCHF.', 'EURGBP.', 'EURJPY.', 'EURNZD.', 'GBPAUD.', 'GBPCAD.', 
     'GBPCHF.', 'GBPJPY.', 'GBPNZD.', 'NZDCAD.', 'NZDCHF.', 'NZDJPY.', 'AUDUSD.', 'EURUSD.', 
     'GBPUSD.', 'NZDUSD.', 'USDCAD.', 'USDCHF.', 'USDJPY.']
    _from_date and _to_date shall be an array[3]. first, second and third element of the array represent to year (format:"YYYY"), month (format:"M"), day (format:"D") respectively
    time frame will be [day: "D", hour: "H", minute: "Min", second: "S", milisecond: "L", microsecond: "U"]
    """
    df=save_data_2_df(_pair=_pair, _from_date=_from_date, _to_date=_to_date, _time_frame=_time_frame)
    if path_and_name==None:
        df.to_excel(_pair+'1.xlsx')
    else:
        df.to_excel(path_and_name)
    
save_data_2_excel(_from_date=[2022,8,1], _to_date=[2022,8,4])
pairs=[ 'AUDCAD.', 'AUDCHF.', 'AUDJPY.', 'AUDNZD.']

