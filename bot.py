import os, sys
from telepot.exception import TelegramError
from telepot import Bot, glance
from model import Channel, session
from config import config
from sqlalchemy.orm import Session
assert isinstance(session,Session)

import logging
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)


token = os.environ.get('SECRET')

bot = Bot(token)
bot.deleteWebhook()

# {'message_id': 1027, 'from': {'id': 391834810, 'is_bot': False, 'first_name': 'Sergey', 'last_name': 'Bobkov',
# 'username': 'WillDrug', 'language_code': 'en-US'}, 'chat': {'id': 391834810, 'first_name': 'Sergey',
# 'last_name': 'Bobkov', 'username': 'WillDrug', 'type
# ': 'private'}, 'date': 1521465604, 'text': 'test'}
def handle(msg):
    #c = session.query(Channel).first()
    #bot.sendMessage(msg['from']['id'], c.name)
    try:
        text = glance(msg)[0]
        logging.debug('text is ok')
    except Exception as e:
        logging.debug(f'text is {e.__str__()}')
        text = "ERROR"

    bot.sendMessage(msg['from']['id'], text)


"""
Menu:
    Submit
        -> Choose channel  # DEEPLINK
            -> post
    Manage
        -> Choose channel  # DEEPLINK?
            -> Ban List /w Pagination
            -> Unban
                -> write nick  # NO BUTTONS
            -> Moderator List
                -> Demote
    Approve
        -> Choose channel  # DEEPLINK FROM INLINE
            -> Approve
            -> Dismiss
            -> Ban

Posts to approve are sent to moderators who are in approve session;
After timeout (handling?) it is resent to another;

"""