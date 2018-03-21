import os
from telepot import Bot, glance, flavor
from model import Channel, UserContext, session
from config import config


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
    #bot.sendMessage(msg['from']['id'], glance(msg)[0])
    flavour = flavor(msg)
    if flavour == 'chat':
        #short: (content_type, msg['chat']['type'], msg['chat']['id'])
        content_type, chat_type, chat_id = glance(msg)
        if chat_type != 'private':
            return True
        context = session.query(UserContext).filter(id=chat_id).first()
        if context is None:
            context = UserContext(id=chat_id, username=msg['from']['username'], menu='main_menu')
            session.add(context)
            session.commit()
        return route(context.menu, msg)
    if flavour == 'callback_query':
        pass
    if flavour == 'inline_query':
        pass
    if flavour == 'chosen_inline_result':
        pass
    if flavour == 'shipping_query':
        pass
    if flavour == 'pre_checkout_query':
        pass

def route(menu, msg):
    menus = {
        'main_menu': main_menu,
    }
    if menu in menus:
        return menus[menu](msg)
    else:
        return True

def main_menu(msg):
    # presuming msg is CHAT
    content_type, chat_type, chat_id = glance(msg)
    if content_type == 'text':
        command = get_command(msg['text'])
        if command == 'start':
            pass

    else:
        return help_message(chat_id)

# UTILITY
def help_message(chat_id):
    return bot.sendMessage(chat_id, 'THIS IS HELP')

def get_command(text):
    return text[:min(text.index('@'), text.index(' '))]

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