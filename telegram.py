from email import message
from telethon import TelegramClient,events
from telethon.tl.types import PeerChat, PeerChannel
from MetaTraderExecute import MetaTraderExecute
import datetime
import re
import configparser
x = datetime.datetime(2022, 2, 21)

def extractInfor(mess):
    # split message by '\n'
    detail = re.split("\n", mess.text)
    id=1
    # infor [24737  , 'XAUUSD', 'BUY'     , '1889.93', 'high', 30 , 60 , 81 , 30]
    #       [mess id,  pair   ,  BuyOrSell,  entry   ,  risk , TP1, TP2, TP3, SL]
    # TP, SL is pip
    position_detail = {}
    for info in detail:
        # split message by ':'
        position_detail[(re.split(": ", info))[0]]=(re.split(": ", info))[1]
        #get only pips in TP and SL 
        # ex: TP1: 1.91940(31.00pip) -> get only 31
        if len(re.findall("\((.*?)(pip)\)", position_detail[(re.split(": ", info))[0]]))!=0:
            position_detail[(re.split(": ", info))[0]]=int(float(re.findall("\((.*?)(pip)\)", position_detail[(re.split(": ", info))[0]])[0][0]))
        id=id+1
    return position_detail

# Manage all linking meta trader's postions with message id 
# Change the postions according replied message
msg_position_detail = {}

# get telegram configuration
config= configparser.ConfigParser()
config.read('config.ini')
api_id=int(config['TELEGRAM']['api_id'])
api_hash = config['TELEGRAM']['api_hash']

# access telegram
client = TelegramClient('anon', api_id, api_hash)


client.start()

async def main():
    # Getting information about yourself
    me = await client.get_me()

# @client.loop.run_until_complete(main()) 
@client.on(events.NewMessage(from_users='mForex - Private Signal'))
# @client.on(events.NewMessage(from_users='me'))
async def my_event_handler(event):
    # filter messages haveing PAIR in its content
    if re.search("^PAIR*", event.message.text):
        mess=event.message
        mess_id = event.message.id
        mess_context = event.message.text
        print("Message id is ={}".format(mess_id))
        print("Message content: ")
        print(mess_context)

        msg_position_detail[mess_id] = extractInfor(mess)
        position_detail=msg_position_detail[mess_id]
        print("Position's detail after extracting:\n{}".format(position_detail))
        
        # if PAIR of position_detail has '.' at the end, then dont add '.' to the end
        if position_detail['PAIR'][len(position_detail['PAIR'])-1]=='.':
            open_position = MetaTraderExecute(position_detail['PAIR'], position_detail['TYPE'], float(position_detail['Open Price']), position_detail['TP1']*10,position_detail['SL']*10)
        else:
            open_position = MetaTraderExecute(position_detail['PAIR']+'.', position_detail['TYPE'], float(position_detail['Open Price']), position_detail['TP1']*10,position_detail['SL']*10)
        
        # Open new position
        position_id = open_position.open()
        if position_id != -1:
            msg_position_detail[mess_id]["meta_position_id"] = position_id
            print("All positions were created: ")
            print(msg_position_detail)

    if event.message.is_reply:
        reply_mess = await event.message.get_reply_message()
        print("Replied message id is: {}".format(reply_mess.id))
        if reply_mess.id in msg_position_detail:
            print(msg_position_detail[reply_mess.id]["meta_position_id"])
        else:
            pass


client.run_until_disconnected()
