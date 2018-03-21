from config import config
from bot import bot, handle
from flask import Flask, request
from telepot.loop import OrderedWebhook
from uuid import uuid4

path = uuid4().__str__()

app = Flask(__name__)

bot.setWebhook(config.webhook_addr, max_connections=1)

webhook = OrderedWebhook(bot, handle)
webhook.run_as_thread()

@app.route(f'/{path}', methods=["POST"])
def telegram_webhook():
    app.logger.error(request.data)
    webhook.feed(request.data)
    app.logger.error('fed request to function')
    return "OK"