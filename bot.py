import os
from telepot import Bot
from model import Channel, session
from config import config
from sqlalchemy.orm import Session
assert isinstance(session,Session)



token = os.environ.get('SECRET')
print(token)
bot = Bot(token)
bot.deleteWebhook()

# {'message_id': 1027, 'from': {'id': 391834810, 'is_bot': False, 'first_name': 'Sergey', 'last_name': 'Bobkov',
# 'username': 'WillDrug', 'language_code': 'en-US'}, 'chat': {'id': 391834810, 'first_name': 'Sergey',
# 'last_name': 'Bobkov', 'username': 'WillDrug', 'type
# ': 'private'}, 'date': 1521465604, 'text': 'test'}
c = Channel(id='test', name='test2')
session.add(c)
session.commit()
def handle(msg):
    c = session.query(Channel).first()
    bot.sendMessage(msg['from']['id'], c.name)