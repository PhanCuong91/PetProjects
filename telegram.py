from email import message
from telethon import TelegramClient,events
from telethon.tl.types import PeerChat, PeerChannel
from execute import Execute
import datetime
import re
import configparser
x = datetime.datetime(2022, 2, 21)

def extractInfor(mess):
    # split message by '\n'
    x = re.split("\n", mess.text)
    id=1
    # infor [24737  , 'XAUUSD', 'BUY'     , '1889.93', 'high', 30 , 60 , 81 , 30]
    #       [mess id,  pair   ,  BuyOrSell,  entry   ,  risk , TP1, TP2, TP3, SL]
    # TP, SL is pip
    infor=[mess.id]
    for i in x:
        # split message by ':'
        infor.append((re.split(": ", i))[1])
        #get only pips in TP and SL 
        # ex: TP1: 1.91940(31.00pip) -> get only 31
        if len(re.findall("\((.*?)(pip)\)", infor[id]))!=0:
            infor[id]=int(float(re.findall("\((.*?)(pip)\)", infor[id])[0][0]))
        id=id+1
    return infor

config= configparser.ConfigParser()
config.read('config.ini')
api_id=int(config['TELEGRAM']['api_id'])
api_hash = config['TELEGRAM']['api_hash']
client = TelegramClient('anon', api_id, api_hash)
positions = []
client.start()
async def main():
    # Getting information about yourself
    me = await client.get_me()

    # "me" is a user object. You can pretty-print
    # any Telegram object with the "stringify" method:
    print(me.stringify())

    # When you print something, you see a representation of it.
    # You can access all attributes of Telegram objects with
    # the dot operator. For example, to get the username:
    username = me.username
    print(username)
    print(me.phone)

    # You can print all the dialogs/conversations that you are part of:
    async for dialog in client.iter_dialogs():
        print(dialog.name, 'has ID', dialog.id)

    # You can print the message history of any chat:
    async for message in client.iter_messages('mForex - Private Signal'):
        if message.date.timestamp() < x.timestamp():
            break 
        if re.search("^PAIR*", message.text):
            infor = extractInfor(message)

# @client.loop.run_until_complete(main()) 
@client.on(events.NewMessage(from_users='mForex - Private Signal'))
# @client.on(events.NewMessage(from_users='me'))
async def my_event_handler(event):
    # filter messages haveing PAIR in its content
    if re.search("^PAIR*", event.message.text):
        print(event.message.text)
        position_detail = extractInfor(event.message)
        print(position_detail)
        # position_detail [24737  , 'XAUUSD', 'BUY'     , '1889.93', 'high', 30 , 60 , 81 , 30]
        #                 [mess id,  pair   ,  BuyOrSell,  entry   ,  risk , TP1, TP2, TP3, SL]
        # if PAIR of position_detail has '.' at the end, then dont add '.' to the end
        if position_detail[1][len(position_detail[1])-1]=='.':
            open_position = Execute(position_detail[1], position_detail[2], float(position_detail[3]), position_detail[5]*10,position_detail[8]*10)
        else:
            open_position = Execute(position_detail[1]+'.', position_detail[2], float(position_detail[3]), position_detail[5]*10,position_detail[8]*10)
        #open position
        open_position.open()

    if event.message.is_reply:
        reply_mess = await event.message.get_reply_message()
        print(reply_mess.id)



client.run_until_disconnected()

