from telethon import TelegramClient,events
from MetaTraderExecute import DEBUG, MetaTraderOrder,GetOrdersPosition,ChangeSlTp
import re, logging, threading, copy
import globalVariables
from datetime import datetime
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
        self.previous_pos = None
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
            ticket['mess_id'] = mess_id
            ticket['sl_lvl'] = -1
            # ticket['status'] = 'placed'
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
                # ticket_trailing_stop_tp1['status'] = 'placed'
                globalVariables.msg_ticket_detail.append(ticket_trailing_stop_tp1)
            if ticket_id_trailing_stop_tp2 != -1:
                # ticket_trailing_stop_tp1['status'] = 'placed'
                globalVariables.msg_ticket_detail.append(ticket_trailing_stop_tp2)
            if ticket_id_trailing_stop_tp3 != -1:
                # ticket_trailing_stop_tp1['status'] = 'placed'
                globalVariables.msg_ticket_detail.append(ticket_trailing_stop_tp3)
            
            if ticket_id_trailing_stop_tp3 != -1 and ticket_id_trailing_stop_tp1 != -1 and ticket_id_trailing_stop_tp2 != -1:
                logging.info("All positions were created: ")
                logging.info(globalVariables.msg_ticket_detail)
        return globalVariables.msg_ticket_detail

    def mforex_change_sl_tp_of_positions(self, period=10):
        # Create 3 types of ticket:
        # 1st type: close a position if it hits TP1
        # 2nd type: if a position hits TP1, then move SL to entry
        #           if a position hits TP2, then close the position
        # 3rd type: if a position hits TP1, then move SL to entry
        #           if a position hits TP2, then move SL to TP1
        #           if a position hits TP3, then close the position
        positions = GetOrdersPosition().get_positions()
        
        # if len(positions) == 0:
        #     threading.Timer(period, self.mforex_change_sl_tp_of_positions).cancel()
        #     logging.info("There is no position in meta trader")
        #     self.previous_pos = len(positions)
        mess_id = []
        if self.previous_pos is not None and len(positions) < len(self.previous_pos):
            print("less")
            if DEBUG:
                pre = datetime.now()
            print("positions: {}".format(positions))
            print("self.pre_pos {}".format(self.previous_pos))
            cur_list_positions = []
            pre_list_positions = []
            for pos in positions:
                cur_list_positions.append(pos._asdict()['identifier'])
            for pos in self.previous_pos:
                pre_list_positions.append(pos._asdict())
            print("positions: {}".format(cur_list_positions))
            print("self.pre_pos {}".format(pre_list_positions))
            # get a list of message id from removed tickets
            # removed ticket is in previous postions but not in current positions
            for pos in pre_list_positions :
                if pos['identifier'] not in cur_list_positions:
                    # pos is a removed tickets
                    print('removed postion')
                    print(pos)
                    # convert tuple to dict
                
                    # get a list of message id
                    for msg_ticket in globalVariables.msg_ticket_detail:
                        print("mess_ticket")
                        print(msg_ticket)
                        if msg_ticket['id'] == pos['identifier']:
                            mess_id.append(msg_ticket['mess_id'])
                            print(mess_id)
                            globalVariables.msg_ticket_detail.remove(msg_ticket)
                       
            if len(mess_id) != 0:
                print("list of mess {}".format(mess_id))
                for m_id in mess_id:
                    for msg_ticket in globalVariables.msg_ticket_detail:
                        print("msg_ticket is {}  and m_id is {}".format(msg_ticket['mess_id'], m_id))
                        if msg_ticket['mess_id'] == m_id:
                            if msg_ticket['sl_lvl'] == -1:
                                sl_pips = 0
                            elif msg_ticket['sl_lvl'] == 0:
                                sl_pips = msg_ticket['TP1']
                            msg_ticket['sl_lvl'] = msg_ticket['sl_lvl'] + 1
                            for pos in positions:
                                if pos._asdict()['identifier'] == msg_ticket['id']:
                                    print("pos {}".format(pos))
                                    ret = ChangeSlTp(pos).change_sl_tp_position(sl_pips=sl_pips)
                                    if ret == -1:
                                        logging.error("Error: Cannot change to new sl and tp")
            if DEBUG:
                now = datetime.now()
                logging.info("The time for changing sl of positions is {}".format(now-pre))
 
        self.previous_pos = copy.copy(positions)

        threading.Timer(period, self.mforex_change_sl_tp_of_positions).start()   

if __name__ == "__main__":
    globalVariables.msg_ticket_detail=[{'ticket': 50045023350, 'time': 1649094396, 'time_msc': 1649094396455, 'time_update': 1649094396, 'time_update_msc': 1649094396455, 'type': 1, 'magic': 234000, 'identifier': 50045023350, 'reason': 3, 'volume': 0.01, 'price_open': 161.1, 'sl': 161.427, 'tp': 160.487, 'price_current': 161.108, 'swap': 0.0, 'profit': -0.07, 'symbol': 'GBPJPY.', 'comment': '26004', 'external_id': '', 'mess_id': 10, 'TP2': 10, 'TP1': 10, 'sl_lvl': -1, 'id': 50045023350}, {'ticket': 50045023353, 'time': 1649094404, 'time_msc': 1649094404010, 'time_update': 1649094404, 'time_update_msc': 1649094404010, 'type': 1, 'magic': 234000, 'identifier': 50045023353, 'reason': 3, 'volume': 0.01, 'price_open': 161.094, 'sl': 161.426, 'tp': 160.486, 'price_current': 161.108, 'swap': 0.0, 'profit': -0.11, 'symbol': 'GBPJPY.', 'comment': '26004', 'external_id': '', 'mess_id': 10, 'TP2': 10, 'TP1': 10, 'sl_lvl': -1, 'id': 50045023353}, {'ticket': 50045023361, 'time': 1649094405, 'time_msc': 1649094405924, 'time_update': 1649094405, 'time_update_msc': 1649094405924, 'type': 1, 'magic': 234000, 'identifier': 50045023361, 'reason': 3, 'volume': 0.01, 'price_open': 161.099, 'sl': 161.427, 'tp': 160.487, 'price_current': 161.108, 'swap': 0.0, 'profit': -0.07, 'symbol': 'GBPJPY.', 'comment': '26004', 'external_id': '', 'mess_id': 10, 'TP2': 10, 'TP1': 10, 'sl_lvl': -1, 'id': 50045023361}]
    MForex().mforex_change_sl_tp_of_positions(period=10)