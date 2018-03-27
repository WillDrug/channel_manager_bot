"""
Reworked a third time: --- TWO-MENUS-IN STRUCTURE ---
    - Current channel: {context}
    - Modding: []
    - Owning: []
    - /cmd1 - help
    - /cmd2 - help
    [BUTTON: switch inline to mod]
    -----------
    1) /help -- ^ this message
    2) /unmod -- clear current channel if mod, select modded channels if not
    3) /banlist -- banlist for current channel if admin, select admin channel if not
    4) /unban -- choose username if admin, choose channel if not
    5) /start -- choose channel from link, activate if owner
    6) /unmanage -- accept if current channel admin, choose channel if not
    7) /manage -- from channel only
    8) /cancel -- resets chosen channel, stops current option
    PLANNED:
    9) /notifyban --
    10) /notifydecline --
    11) /notifyaccept --
"""
from time import time
import os
from uuid import uuid4
from telepot import Bot, glance, flavor
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, InlineQuery, InlineQueryResultArticle, \
    ChosenInlineResult, InputTextMessageContent, ReplyKeyboardMarkup, KeyboardButton
from telepot.exception import TelegramError
from model import Channel, UserContext, Mod, new_session
from config import config
from sqlalchemy import func, asc
import logging

token = os.environ.get('SECRET')

bot = Bot(token)
bot.deleteWebhook()

current_username = bot.getMe().get("username")


# ENTRYPOINT

def handle(msg):
    session = new_session()  # sql session to be shared between functions
    cid = msg.get('from', {}).get('id')
    try:
        res = route_message(msg, session)
        if not res:
            on_bullshit(cid, session)
        else:
            on_success(cid, session)
    except Exception as e:
        on_bullshit(cid, session)
        logging.critical(e)
        session.rollback()
    return True


def route_message(msg, session):
    routing_table = {
        'message': handle_message,
        # 'edited_message': ,  #
        'channel_post': handle_channel,
        # 'edited_channel_post': ,  # no need
        'inline_query': handle_inline,
        'chosen_inline_result': handle_chosen_inline,
        'callback_query': handle_callback_query,
    }
    route = do_route(routing_table, msg)
    if route is False:
        return False
    else:
        route(msg, session)


def on_bullshit(cid, session):
    pass


def on_success(cid, session):
    pass


# HANDLE FUNCTIONS
# chat
def handle_message(msg, session):
    routing_table = {
        'text': handle_message_text,
        'sticker': lambda msg, session, context: False
    }
    cid = msg.get('chat', {}).get('id')
    context = session.query(UserContext).filter(UserContext.id == cid).first()
    if context is None:
        context = UserContext(id=cid)
        session.add(context)
    route = do_route(routing_table, msg)
    if route is not False:  # different routing rules. in private, everything not a command is a submission
        return route(msg, session, context)
    else:
        return handle_submission(msg, session, context)


def handle_message_text(msg, session, context):  # DONE
    routing_table = {  # all commands are returned as generics, always.
        '/help': send_help,
        '/unmod': 2,
        '/banlist': send_ban_list,
        '/unban': 2,
        '/start': 2,
        '/unmanage': 2,
        '/cancel': 2,
        # '/manage':   2,
    }

    route = do_route(routing_table, {msg.get('text', ''): 'placeholder'})
    # check is we've been sent a known command
    if route is not False:
        return route(msg, session)
    # everything else is either submission, or an answer.
    # check for answer
    context_routing = {
        'choose': 2,  # choose channel and go back
        'unmod': 2,  # choose who to unmod
        'unban': 2,  # choose who to unban
    }

    route = do_route(context_routing, {context.context: 'placeholder'})
    if route is not False:
        result = route(msg, session, context)
        if result:
            route = do_route(routing_table, {context.next: 'placeholder'})
            if route is False:  # kek
                return True
            else:
                return route(msg, session, context)
        else:
            return False
    # route to NEXT object
    # else submission:
    return handle_submission(msg, session, context)


def handle_submission(msg, session, context):
    pass


def send_help(msg, session, context):
    try:
        modding = session.query(Channel.name).join(Mod, Channel.id == Mod.channel).filter(Mod.user == context.id).all()
        modding = modding.__str__()[1:-1].replace("'", '')
        channels = session.query(Channel.name).filter(Channel.owner == context.id).all()
        channels = channels.__str__()[1:-1].replace("'", '')
        current = session.query(Channel.name).filter(Channel.id == context.channel).first()
        bot.sendMessage(context.id, f'*~~Channel Manager Bot~~*\n'
                                    f'_Current channel_: {current}\n'
                                    f'_You mod the following channels:_ {modding}\n'
                                    f'_You admin the following channels:_ {channels}\n'
                                    f'_Commands:_\n'
                                    f'/help : Display this message\n'
                                    f'/modlist : List mods for a channel you own\n'
                                    f'/banlist : List banned users for a channel you own\n'
                                    f'/unmod : Stop modding a channel or demote a mod from a channel you own\n'
                                    f'/unban : Unban a user from a channel you own\n'
                                    f'/unmanage : Stop managing a channel (note: bot will leave it)\n'
                                    f'/cancel : Clear current channel and cancel current request\n',
                        parse_mode='markdown')
    except TelegramError:
        return False
    return True

def send_ban_list(msg, session, context):
    if context.channel is None:
        context.context = 'choose'
        context.next = '/banlist'
        channels = session.query(Channel).filter(Channel.owner == context.id).all()  # all admining
        return send_channel_choice(context.id, channels)


def send_channel_choice(cid, channels):
    try:
        keyboard = []
        for ch in channels:
            keyboard.append([KeyboardButton(text=ch.name)])
        bot.sendMessage(cid, f'Choose a channel',
                        reply_markup=ReplyKeyboardMarkup(keyboard=keyboard))
        return True
    except TelegramError:
        return False


# channel
def handle_channel(msg, session):  # Only listen for /manage and /unmanage commands  DONE
    routing_table = {
        'text': handle_channel_command,
    }
    route = do_route(routing_table, msg)
    if route is False:  # only parse text
        return route
    else:
        return route(msg, session)


def handle_channel_command(msg, session):  # DONE
    if msg['text'] in ['/unmanage', f'/unmanage@{current_username}']:  # TODO: may be config literals?
        return unmanage_channel(msg['chat']['chat_id'], msg['from']['id'], session)
    elif msg['text'] in ['/manage', f'/manage@{current_username}']:
        chat = msg.get('chat', {})
        return manage_channel(chat, msg['from']['id'], session)  # Working with Telegram Objects
    else:
        return False


def manage_channel(chat, issued_by, session):  # id, name, link, owner DONE
    # id, name, link, owner
    bot_is_admin, issued_by_owner = check_admin(chat.get('id'), issued_by)
    if not issued_by_owner:
        return False
    if not bot_is_admin:
        try:
            bot.sendMessage(issued_by, 'Make me an admin with post and edit permissions first!')
        except TelegramError:
            return False
    # if all permissions present: check if owner opened a chat
    try:
        bot.sendMessage(issued_by, f'You started managing {name}\nTo undo this you can use /unmanage from anywhere.')
        channel = Channel(id=chat.get('id'), name=chat.get('title'), link=chat.get('username'), owner=issued_by)
        session.add(channel)
        session.commit()  # make sure all is well before messaging.
        bot.sendMessage(chat.get('id'),
                        f"This channel is now managed by a bot!\n"
                        f"If you want to submit something to this channel, message @{current_username} and choose this channel\n"
                        f"Or just go here: http://t.me/{bot.getMe().get('username')}?start={chat.get('id')}",
                        disable_web_page_preview=True,
                        disable_notification=True)
        return True
    except TelegramError:
        bot.sendMessage(chat.get('id'), f"To start managing, press this:\n"
                                        f"http://t.me/{current_username}/?start={chat.get('id')}")
        return True


def unmanage_channel(cid, issued_by, session):  # DONE
    ch = session.query(Channel).filter(Channel.id == cid).first()
    if ch is None:
        return False
    if ch.owner != issued_by:
        return False
    # channel exists and request is by owner
    session.delete(ch)
    bot.unpinChatMessage(cid)
    bot.sendMessage(cid, "This chat is no longer managed.\nChannel Manager Bot has left the building!")
    bot.leaveChat(cid)


# inline
def handle_inline(msg, session):
    pass


def handle_chosen_inline(msg, session):
    pass


# callback
def handle_callback_query(msg, session):
    pass


# UTILITY - return from these functions should be parsed after usage
def check_admin(channel_id, issued_by):
    admins = bot.getChatAdministrators(channel_id)
    self_id = bot.getMe().get('id')
    bot_is_admin = False
    issued_by_owner = False
    for admin in admins:
        if admin.get('user', {}).get('id') == self_id:
            if admin.get('can_post_messages') and admin.get('can_edit_messages'):
                bot_is_admin = True
        if admin.get('user', {}).get('id') == issued_by:
            if admin.get('status') == 'creator':
                issued_by_owner = True
    return bot_is_admin, issued_by_owner


def do_route(switch, case):
    for key in switch:
        if key in case.keys():
            return switch.get(key)
    return False
