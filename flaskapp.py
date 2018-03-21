from config import config
from bot import bot, handle
from flask import Flask, request
from telepot.loop import OrderedWebhook
from uuid import uuid4

app = Flask(__name__)

bot.setWebhook(config.webhook_addr, max_connections=1)

webhook = OrderedWebhook(bot, handle)
webhook.run_as_thread()

@app.route(f'/{config.webhook_addr}', methods=["POST"])
def telegram_webhook():
    raise Exception('cheat')
    webhook.feed(request.data)
    return "OK"