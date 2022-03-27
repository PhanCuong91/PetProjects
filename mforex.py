from telethon import TelegramClient,events
from MetaTraderExecute import DEBUG, MetaTraderOrder,GetOrdersPosition,ChangeSlTp,CreateNewSlTp
import re, logging, threading, copy, time,sys
import globalVariables

# define log for whole project
globalVariables.log

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

class MForex:
    mforex='mForex - Private Signal'
    def __init__(self) -> None:
        self.previous_pos = 0
        pass
    def mforex_create_order(self, event):
        
        # filter messages haveing PAIR in its content
        if re.search("^PAIR*", event.message.text):
            mess=event.message
            mess_id = event.message.id
            mess_context = event.message.text
            logging.info("Message id is = {}".format(mess_id))
            logging.info("Message content: ")
            logging.info(mess_context)

            ticket = extractInfor(mess)
            globalVariables.msg_ticket_detail[mess_id] = []
            # Adjust the ticket with correct information
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
            
            # Create 3 types of ticket:
            # 1st order: Tp is TP1
            # 2nd order: Tp is TP2
            # 3rd order: Tp is TP3
            ticket_trailing_stop_tp1 = ticket
            ticket_trailing_stop_tp2 = copy.copy(ticket)
            ticket_trailing_stop_tp3 = copy.copy(ticket)

            ticket_trailing_stop_tp1['trailing_stop'] = 'TP1'
            ticket_trailing_stop_tp1['comment'] = 'TP1'
            ticket_trailing_stop_tp2['trailing_stop'] = 'TP2'
            ticket_trailing_stop_tp2['comment'] = 'TP2'
            ticket_trailing_stop_tp3['trailing_stop'] = 'TP3'
            ticket_trailing_stop_tp3['comment'] = 'TP3'   
            
            ticket_id_trailing_stop_tp1 = MetaTraderOrder(ticket_trailing_stop_tp1).place_order()
            ticket_id_trailing_stop_tp2 = MetaTraderOrder(ticket_trailing_stop_tp2).place_order()
            ticket_id_trailing_stop_tp3 = MetaTraderOrder(ticket_trailing_stop_tp3).place_order()
            # order is a ticket being placed
            # position is a ticket being execute
            if ticket_id_trailing_stop_tp1 != -1:
                globalVariables.msg_ticket_detail[mess_id].append(ticket_trailing_stop_tp1)
            if ticket_id_trailing_stop_tp2 != -1:
                globalVariables.msg_ticket_detail[mess_id].append(ticket_trailing_stop_tp2)
            if ticket_id_trailing_stop_tp3 != -1:
                globalVariables.msg_ticket_detail[mess_id].append(ticket_trailing_stop_tp3)
            # msg_ticket_detail[mess_id]["OrderOrPosition"] = 'Order'
            
            if ticket_id_trailing_stop_tp3 != -1 and ticket_id_trailing_stop_tp1 != -1 and ticket_id_trailing_stop_tp2 != -1:
                logging.info("All positions were created: ")
                logging.info(globalVariables.msg_ticket_detail)
        return globalVariables.msg_ticket_detail

    def mforex_change_sl_tp_of_positions(self, period=30):
        # Create 3 types of ticket:
        # 1st type: close a position if it hits TP1
        # 2nd type: if a position hits TP1, then move SL to entry
        #           if a position hits TP2, then close the position
        # 3rd type: if a position hits TP, then move SL to entry
        #           if a position hits TP2, then move SL to TP1
        #           if a position hits TP3, then close the position
        positions = GetOrdersPosition().get_positions()
        # if len(positions) == 0:
        #     threading.Timer(period, self.mforex_change_sl_tp_of_positions).cancel()
        #     logging.info("There is no position in meta trader")
        #     self.previous_pos = len(positions)
        if len(positions) < self.previous_pos:
            for position in positions:
                for mess_id in globalVariables.msg_ticket_detail:
                    for ticket in globalVariables.msg_ticket_detail[mess_id]:
                        if ticket['id'] == position['identifier']:
                            if DEBUG:
                                pre = time.now()
                            condition = {'TP1' : ticket['TP1']}
                            condition['TP2'] = ticket['TP2']
                            new_sl = CreateNewSlTp(position,condition).create_new_sl()
                            ret = ChangeSlTp().change_sl_tp_position(new_sl=new_sl, position=position)
                            if DEBUG:
                                now = time.now()
                            if ret != -1:
                                if DEBUG:
                                    logging.info("The time for changing sl of position {} is {}".format(position['identifier'],now-pre))
                                pass
                            else:
                                logging.error("Error: Cannot change to new sl and tp")

        self.previous_pos = len(positions)   
        threading.Timer(period, self.mforex_change_sl_tp_of_positions).start()   
