from email import message
from telethon import TelegramClient,events
from telethon.tl.types import PeerChat, PeerChannel
from MetaTraderExecute import MetaTrader
import datetime, copy
import re
import configparser
import logging
import sys
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("Tele.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
x = datetime.datetime(2022, 2, 21)

def extractInfor(mess):
    # split message by '\n'
    detail = re.split("\n", mess.text)
    id=1
    # infor [24737  , 'XAUUSD', 'BUY'     , '1889.93', 'high', 30 , 60 , 81 , 30]
    #       [mess id,  pair   ,  BuyOrSell,  entry   ,  risk , TP1, TP2, TP3, SL]
    # TP, SL is pip
    position_detail = {'comment': str(mess.id)}
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
msg_ticket_detail = {}

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
# @client.on(events.NewMessage(from_users='mForex - Private Signal'))
@client.on(events.NewMessage(from_users='me'))
async def my_event_handler(event):
    # filter messages haveing PAIR in its content
    if re.search("^PAIR*", event.message.text):
        mess=event.message
        mess_id = event.message.id
        mess_context = event.message.text
        logging.info("Message id is ={}".format(mess_id))
        logging.info("Message content: ")
        logging.info(mess_context)

        ticket = extractInfor(mess)
        msg_ticket_detail[mess_id] = []
        # Rapair ticket with correct information
        # Change to correct key, delete unused key
        ticket['symbol'] = ticket['PAIR']
        del ticket['PAIR']
        ticket['order_type'] = ticket['TYPE']
        del ticket['TYPE']
        ticket['price'] = ticket['Open Price']
        del ticket['Open Price']
        # if PAIR of position_detail has '.' at the end, then dont add '.' to the end
        # Open new position
        if ticket['symbol'][len(ticket['symbol'])-1]!='.':
            ticket['symbol'] = ticket['symbol']+'.'
        ticket['TP1'] = ticket['TP1'] * 10
        ticket['TP2'] = ticket['TP2'] * 10
        ticket['TP3'] = ticket['TP3'] * 10
        ticket['SL'] = ticket['SL'] * 10
        ticket['price'] = float(ticket['price'])
        logging.info("Position's detail after extracting:\n{}".format(ticket))
        # add trailing stop
        
        # Create 3 types of ticket:
        # 1st type: close a position if it hits TP1
        # 2nd type: if a position hits TP1, then move SL to entry
        #           if a position hits TP2, then close the position
        # 3rd type: if a position hits TP1, then move SL to entry
        #           if a position hits TP2, then move SL to TP1
        #           if a position hits TP3, then close the position

        ticket_trailing_stop_tp3 = copy.copy(ticket)
        ticket_trailing_stop_tp2 = copy.copy(ticket)

        ticket['trailing_stop'] = 'TP1'
        ticket['comment']='TP1'
        ticket_trailing_stop_tp3['trailing_stop']='TP3'
        ticket_trailing_stop_tp3['comment']='TP3'   
        ticket_trailing_stop_tp2['trailing_stop']='TP2'
        ticket_trailing_stop_tp2['comment']='TP2'
        
        ticket_id = MetaTrader(ticket).place_order()
        ticket_id_trailing_stop_tp3 = MetaTrader(ticket_trailing_stop_tp3).place_order()
        ticket_id_trailing_stop_tp2 = MetaTrader(ticket_trailing_stop_tp2).place_order()
        if ticket_id != -1:
            # order is a ticket being placed
            # position is a ticket being execute
            msg_ticket_detail[mess_id].append(ticket)
        if ticket_id_trailing_stop_tp3 != -1:
            # order is a ticket being placed
            # position is a ticket being execute
            msg_ticket_detail[mess_id].append(ticket_trailing_stop_tp3)
        if ticket_id_trailing_stop_tp2 != -1:
            # order is a ticket being placed
            # position is a ticket being execute
            msg_ticket_detail[mess_id].append(ticket_trailing_stop_tp2)
        # msg_ticket_detail[mess_id]["OrderOrPosition"] = 'Order'
        
        if ticket_id_trailing_stop_tp3 != -1 and ticket_id != -1 and ticket_id_trailing_stop_tp2 != -1:
            logging.info("All positions were created: ")
            logging.info(msg_ticket_detail)

    if event.message.is_reply:
        reply_mess = await event.message.get_reply_message()
        logging.info("Replied message id is: {}".format(reply_mess.id))
        # search key of message id in msg_position_detail
        if reply_mess.id in msg_ticket_detail:
            # search key of order id msg_position_detail[reply_mess.id]
            if "id" in msg_ticket_detail[reply_mess.id]:
                logging.info(msg_ticket_detail[reply_mess.id]["id"])
        else:
            pass

client.run_until_disconnected()