from bot import bot, handle

from flask import Flask, request
from telepot.loop import OrderedWebhook
from config import config

app = Flask(__name__)

bot.setWebhook(config.webhook_addr, max_connections=1)

webhook = OrderedWebhook(bot, handle)
webhook.run_as_thread()

@app.route(f'/{path}', methods=["POST"])
def telegram_webhook():
    webhook.feed(request.data)
    return "OK"