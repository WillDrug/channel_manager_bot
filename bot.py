import os
from telepot import Bot
from model import Channel, session
from config import config
from sqlalchemy.orm import Session
assert isinstance(session,Session)
config.init_proxy()


token = os.environ.get('SECRET')

bot = Bot(token)
bot.deleteWebhook()

def handle(msg):
    bot.sendMessage(msg['chat_Id'], 'test')