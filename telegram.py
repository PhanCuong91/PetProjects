from email import message
from telethon import TelegramClient,events
from telethon.tl.types import PeerChat, PeerChannel
from MetaTraderExecute import PlaceOrder
import datetime
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

        msg_ticket_detail[mess_id] = extractInfor(mess)
        order_detail=msg_ticket_detail[mess_id]
        # Change to correct key
        # delete unused key
        order_detail['symbol'] = order_detail['PAIR']
        del order_detail['PAIR']
        order_detail['order_type'] = order_detail['TYPE']
        del order_detail['TYPE']
        order_detail['price'] = order_detail['Open Price']
        del order_detail['Open Price']

        # add trailing stop
        order_detail['trailing_stop'] = None
        logging.info("Position's detail after extracting:\n{}".format(order_detail))
        # if PAIR of position_detail has '.' at the end, then dont add '.' to the end
        # Open new position
        if order_detail['symbol'][len(order_detail['symbol'])-1]!='.':
            order_detail['symbol'] = order_detail['symbol']+'.'
        
        # Create 3 types of ticket:
        # 1st type: close a position if it hits TP1
        # 2nd type: if a position hits TP1, then move SL to entry
        #           if a position hits TP2, then close the position
        # 3rd type: if a position hits TP1, then move SL to entry
        #           if a position hits TP2, then move SL to TP1
        #           if a position hits TP3, then close the position
        
        ticket_id = PlaceOrder(order_detail).place_order()
        order_detai_trailing_stop_tp3 = order_detail
        order_detai_trailing_stop_tp3['trailing_stop']='TP3'
        order_detai_trailing_stop_tp3['comment']='TP3'
        order_detai_trailing_stop_tp2 = order_detail
        order_detai_trailing_stop_tp2['trailing_stop']='TP2'
        order_detai_trailing_stop_tp2['comment']='TP2'
        ticket_id_trailing_stop_tp3 = PlaceOrder(order_detai_trailing_stop_tp3).place_order()
        ticket_id_trailing_stop_tp2 = PlaceOrder(order_detai_trailing_stop_tp2).place_order()
        if ticket_id != -1:
            # order is a ticket being placed
            # position is a ticket being execute
            if len(msg_ticket_detail[mess_id]["meta_ticket_id"])==0:
                msg_ticket_detail[mess_id]["meta_ticket_id"] = {ticket_id}
            else:
                msg_ticket_detail[mess_id]["meta_ticket_id"].append(ticket_id)
        if ticket_id_trailing_stop_tp3 != -1:
            # order is a ticket being placed
            # position is a ticket being execute
            if len(msg_ticket_detail[mess_id]["meta_ticket_id"])==0:
                msg_ticket_detail[mess_id]["meta_ticket_id"] = {ticket_id_trailing_stop_tp3}
            else:
                msg_ticket_detail[mess_id]["meta_ticket_id"].append(ticket_id_trailing_stop_tp3)
        if ticket_id_trailing_stop_tp2 != -1:
            # order is a ticket being placed
            # position is a ticket being execute
            if len(msg_ticket_detail[mess_id]["meta_ticket_id"])==0:
                msg_ticket_detail[mess_id]["meta_ticket_id"] = {ticket_id_trailing_stop_tp2}
            else:
                msg_ticket_detail[mess_id]["meta_ticket_id"].append(ticket_id_trailing_stop_tp2)
        msg_ticket_detail[mess_id]["OrderOrPosition"] = 'Order'
        
        if ticket_id_trailing_stop_tp3 != -1 and ticket_id != -1 and ticket_id_trailing_stop_tp2 != -1:
            logging.info("All positions were created: ")
            logging.info(msg_ticket_detail)

    if event.message.is_reply:
        reply_mess = await event.message.get_reply_message()
        logging.info("Replied message id is: {}".format(reply_mess.id))
        # search key of message id in msg_position_detail
        if reply_mess.id in msg_ticket_detail:
            # search key of order id msg_position_detail[reply_mess.id]
            if "meta_ticket_id" in msg_ticket_detail[reply_mess.id]:
                logging.info(msg_ticket_detail[reply_mess.id]["meta_ticket_id"])
        else:
            pass

client.run_until_disconnected()
