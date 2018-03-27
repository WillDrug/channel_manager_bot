from config import config
from bot import bot, handle
from flask import Flask, request
import logging

app = Flask(__name__)

bot.setWebhook(config.webhook_addr, max_connections=1)

@app.route(f'/{config.path}', methods=["POST"])
def telegram_webhook():
    update = request.get_json()
    if 'message' in update.keys():
        handle(update['message'])
    elif 'channel_post' in update.keys():
        handle(update['channel_post'])
    else:
        logging.critical(f'Weird message {update} received')
    return "OK"