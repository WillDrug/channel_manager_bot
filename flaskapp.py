from config import config
from bot import bot, handle
from flask import Flask, request
import logging

app = Flask(__name__)

bot.setWebhook(config.webhook_addr, max_connections=1)

@app.route(f'/{config.path}', methods=["POST"])
def telegram_webhook():
    update = request.get_json()
    handle(update[list(update.keys())[1]])  # TODO: handle another way
    return "OK"