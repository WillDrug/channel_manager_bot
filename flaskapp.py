from config import config
from bot import bot, handle
from flask import Flask, request
#from telepot.loop import OrderedWebhook
from uuid import uuid4


app = Flask(__name__)

bot.setWebhook(config.webhook_addr, max_connections=1)

#webhook = OrderedWebhook(bot, handle)
#webhook.run_as_thread()

import logging
@app.route(f'/{config.path}', methods=["POST"])
def telegram_webhook():
    #webhook.feed(request.data)
    update = request.get_json()
    handle(update)
    return "OK"