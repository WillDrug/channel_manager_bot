from config import config
from bot import bot, handle
from flask import Flask, request


app = Flask(__name__)

bot.setWebhook(config.webhook_addr, max_connections=1)

@app.route(f'/{config.path}', methods=["POST"])
def telegram_webhook():
    update = request.get_json()
    if 'message' in update.keys():
        handle(update['message'])
    return "OK"