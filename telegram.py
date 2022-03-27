from telethon import TelegramClient,events
from mforex import MForex
import logging, configparser
import globalVariables

# define log for whole project
globalVariables.log

WAIT_SECONDS = 10
# get telegram configuration
config= configparser.ConfigParser()
config.read('config.ini')
api_id=int(config['TELEGRAM']['api_id'])
api_hash = config['TELEGRAM']['api_hash']

logging.info('Program is started')

# access telegram
client = TelegramClient('anon', api_id, api_hash)
client.start()
me='me'

# async def main():
#     # Getting information about yourself
#     me = await client.get_me()

# @client.on(events.NewMessage(from_users=MForex.mforex))
@client.on(events.NewMessage(from_users=me))
async def my_event_handler(event):

    mf = MForex()
    mf.mforex_create_order(event)
    if event.message.is_reply:
        reply_mess = await event.message.get_reply_message()
        logging.info("Replied message id {}: {}".format(reply_mess.id, event.message.text))
        # adding trailing stop
        mf.mforex_change_sl_tp_of_positions(period=WAIT_SECONDS)
        # search key of message id in msg_position_detail
        if reply_mess.id in globalVariables.msg_ticket_detail:
            # search key of order id msg_position_detail[reply_mess.id]
            if "id" in globalVariables.msg_ticket_detail[reply_mess.id]:
                logging.info(globalVariables.msg_ticket_detail[reply_mess.id]["id"])
                pass
        else:
            pass

client.run_until_disconnected()