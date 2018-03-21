import os
from telepot import Bot, glance, flavor
from model import Channel, UserContext, Invite, session
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
    # 1) send  basic menu info
    bot.sendMessage(chat_id, 'Hello! I am Channel Manager Bot!\nPlease pardon the lag, my server is made of potatoes and is free.')
    # 2) If that's main menu we have no channel; Text is treated as a command
    if content_type == 'text':
        command = get_command(msg['text'])
        if command == '/start':
            try:
                command, option, invite_hash = msg['text'].split(';')
            except ValueError:
                # 3) someone has no idea what are they doing at all
                option = ''

            # possible opt+ions:
            # 1) someone registered as mod -> there's a modhash
            if option == 'invite':
                invite = session.query(Invite).filter(invite_hash=invite_hash).first()
                if invite is None:
                    return bot.sendMessage(chat_id, 'You cheating bastard, you!')
                invite.channel
            # 2) someone got here from channel to submit -> set context to choose channel, goto submit menu
            elif option == 'submit':
                pass
            # 3) someone has no idea what are they doing at all
            else:
                bot.sendMessage(chat_id, help_message(),
                                reply_markup=[])  # TODO: reply buttons
        elif command == '/manage':
            # tell him to fuck off from private
            pass

        # 3) everything else is used as submission material -> then we ask for a channel
    else:
        return bot.sendMessage(chat_id, help_message())

# UTILITY
def help_message():
    return 'THIS IS HELP'

def get_command(text):
    return text[:min(text.index('@'), text.index(' '))]

"""
Menu:
    send anything that's not a proper command == submit
        -> Choose channel  # DEEPLINK HERE
            -> submit to moderator
    Approve : no button, auto sends shit to you
        -> Approve # no usernames here
        -> Decline 
        -> Ban
    /admin # only shows up if you're an owner of at least one channel
        -> Choose channel 
            -> /ban list /w Pagination
            -> /unban username
            -> /modlist
            -> /unmod username
            /unmanage -> kills pinned message, send message that this is over, leaves channel (CONFIRM!!)
    -> Register Mod (inline)
        -> Mod registered # DEEPLINK FROM INLINE
    /unmod: #only appears if you're in modlist 
            -> Choose a channel
    /manage???/start own: #not showing up
        1) Registeres channel, owner
        2) Sends and pins a message to channel
        
In channel:
    -> /manage
        0) checks admin privileges; if not : shit, mate.
        1) generates switch chat button or deeplink for owner
        
Posts to approve are sent to moderators who are in approve session;
After timeout (handling?) it is resent to another; ?????

1) If all mods and owner are unreachable -> ok, but warns submitters
2) If channel is unreachable -> kills channel from list with a warning

"""