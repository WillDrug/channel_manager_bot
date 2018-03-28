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
    ChosenInlineResult, InputTextMessageContent, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telepot.exception import TelegramError
from model import Channel, UserContext, Mod, Ban, new_session
from config import config
from sqlalchemy import func, asc
import logging as l
import sys

token = os.environ.get('SECRET')

bot = Bot(token)
bot.deleteWebhook()

current_username = bot.getMe().get("username")

# TODO: cleanup when bot is kicked.

# ENTRYPOINT

def handle(msg):
    session = new_session()  # sql session to be shared between functions
    cid = msg.get('from', {}).get('id')
    try:
        res = route_message(msg, session)
        if not res:
            l.info(f'Got bullshit msg')
            on_bullshit(cid, session)
            session.commit()
            return False
        else:
            l.info(f'Got ok msg')
            on_success(cid, session)
            session.commit()
            return True
    except Exception as e:
        on_bullshit(cid, session)
        l.critical(f'Exception: {e.__str__()}; {sys.exc_info()}')
        session.rollback()
        return False

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
        l.info(f'Route failed')
        return False
    else:
        return route(msg, session)


def on_bullshit(cid, session):
    pass


def on_success(cid, session):
    pass


# HANDLE FUNCTIONS
# chat
def handle_message(msg, session):
    msg = msg['message']
    routing_table = {
        'text': handle_message_text,
        'sticker': lambda msg, session, context: False
    }
    cid = msg.get('chat', {}).get('id')
    context = session.query(UserContext).filter(UserContext.id == cid).first()
    if context is None:
        l.debug(f'Context is none, creating')
        context = UserContext(id=cid, username=msg.get('from', {}).get('username'))
        session.add(context)
    route = do_route(routing_table, msg)
    if route is not False:  # different routing rules. in private, everything not a command is a submission
        l.debug(f'Routing to {route}')
        return route(msg, session, context)
    else:
        l.debug(f'Route was false, assuming submission')
        return handle_submission(msg, session, context)


def handle_message_text(msg, session, context):  # DONE # TODO: reply_to_message TODO: redo to class with self.msg\session\context
    routing_table = {  # all commands are returned as generics, always.
        '/help': send_help,
        '/modlist': send_mod_list,
        '/unmod': send_unmod_prompt,
        '/banlist': send_ban_list,
        '/unban': send_unban_prompt,
        '/start': parse_stupid_start,
        '/unmanage': send_unmanage_prompt,
        '/cancel': cancel_prompt,
        # '/manage':   2,
    }
    command = msg.get('text', '').split(' ')[0]
    route = do_route(routing_table, {command: 'placeholder'})
    # check is we've been sent a known command
    if route is not False:
        l.debug(f'Routing to {route}')
        return route(msg, session, context)
    # everything else is either submission, or an answer.
    # check for answer
    context_routing = {
        'choose': choose_channel_callback,  # choose channel and go back
        'unmod': unmod_callback,  # chosen who to unmod
        'unban': unban_callback,  # chosen who to unban
        'unmanage': unmanage_callback, # awaiting accept to unmanage command
    }

    route = do_route(context_routing, {context.context: 'placeholder'})
    l.debug(f'Context route is {route}')
    if route is not False:
        l.debug(f'Doing context routing to {route}')
        result = route(msg, session, context)
        if result:
            l.debug(f'Route succeeded, routing next action')
            route = do_route(routing_table, {context.next: 'placeholder'})
            if route is False:  # kek
                return True
            else:
                l.debug(f'Next action routed to {route}')
                return route(msg, session, context)
        else:
            return False
    # route to NEXT object
    # else submission not starting with /
    if command.startswith('/'):
        return False
    return handle_submission(msg, session, context)


def handle_submission(msg, session, context):
    Message =
    pass


def send_help(msg, session, context, expanded=True):  # ONGOING
    try:
        modding = session.query(Channel.name).join(Mod, Channel.id == Mod.channel).filter(Mod.user == context.id).all()
        modding = list_to_readable(modding)
        channels = session.query(Channel.name).filter(Channel.owner == context.id).all()
        channels = channels.__str__()[1:-1].replace("'", '')
        current = session.query(Channel.name).filter(Channel.id == context.channel).first()
        if current is not None:
            current = current[0]
        response = f"*~~Channel Manager Bot~~*\n"\
                   f"*Current channel*: _{current}_\n"\
                   f"*You mod the following channels:* {'_'+modding+'_' if modding != '' else modding}\n"\
                   f"*You admin the following channels:* {'_'+channels+'_' if channels != '' else channels}\n"
        if expanded:
            response +=  f'*Commands:*\n'\
                         f'/help : Display this message\n'\
                         f'/modlist : List mods for a channel you own\n'\
                         f'/banlist : List banned users for a channel you own\n' \
                         f'/unmod : Stop modding a channel or demote a mod from a channel you own\n'\
                         f'/unban : Unban a user from a channel you own\n'\
                         f'/unmanage : Stop managing a channel (note: bot will leave it)\n'\
                         f'/cancel : Clear current channel and cancel current request\n'
        bot.sendMessage(context.id, response,
                        parse_mode='markdown',
                        reply_markup=ReplyKeyboardRemove())  # TODO: ??
        l.debug(f'Help returning TRUE')
        return True
    except TelegramError as e:
        l.error(f'{e.__str__()}, {sys.exc_info()}')
        return False

def send_ban_list(msg, session, context): ## DONE TODO: flat send_*_list into one function
    if context.channel is None or not check_admin(context.channel, context.id)[1]:
        context.context = 'choose'
        context.next = '/banlist'
        channels = session.query(Channel).filter(Channel.owner == context.id).all()  # all admining
        if channels.__len__() == 0:
            bot.sendMessage(context.id, 'There are no channels where you\'re and admin. \n Just add me to a channel as an admin and do /manage')
            return False
        return send_channel_choice(context.id, channels)
    banned = session.query(UserContext.username).join(Ban, Ban.user == UserContext.id).filter(Ban.channel == context.channel).all()  # TODO: move to UTILITY
    if banned.__len__() == 0:
        bot.sendMessage(context.id, 'Noone seems to be banned. Keep it that way!')
        return True
    banned = list_to_readable([ban[0] for ban in banned], repl='\n')
    bot.sendMessage(context.id, f"Banned:\n{banned}")
    context.context = None
    context.next = None
    return True

def send_mod_list(msg, session, context): # DONE
    if context.channel is None or not check_admin(context.channel, context.id)[1]:
        context.context = 'choose'
        context.next = '/modlist'
        channels = session.query(Channel).filter(Channel.owner == context.id).all()  # all admining
        if channels.__len__() == 0:
            bot.sendMessage(context.id, 'There are no channels where you\'re and admin. \n Just add me to a channel as an admin and do /manage')
            return False
        return send_channel_choice(context.id, channels)
    mods = session.query(UserContext.username).join(Mod, Mod.user == UserContext.id).filter(Mod.channel == context.channel).all()  # TODO: move to UTILITY
    if mods.__len__() == 0:
        bot.sendMessage(context.id, 'No moderators are added to the channel yet')
        return True
    mods = list_to_readable([mod[0] for mod in mods], repl='\n')
    bot.sendMessage(context.id, f"Moderating:\n{mods}")
    context.context = None
    context.next = None
    return True

def send_unmod_prompt(msg, session, context):  # DONE TODO: squash
    if context.channel is None or not check_admin(context.channel, context.id)[1]:
        context.context = 'choose'
        context.next = '/unmod'
        channels = session.query(Channel).filter(Channel.owner == context.id).all()  # all admining
        if channels.__len__() == 0:
            bot.sendMessage(context.id, 'There are no channels where you\'re and admin. \n Just add me to a channel as an admin and do /manage')
            return False
        return send_channel_choice(context.id, channels)
    #to_unmod = msg.get('text', '')
    #mod = session.query(UserContext).join(Mod, Mod.user == UserContext.id).filter(Mod.channel == context.channel).filter(UserContext.username == to_unmod).first()

    mods = session.query(UserContext.username).join(Mod, Mod.user == UserContext.id).filter(Mod.channel == context.channel).all()
    if mods.__len__() == 0:
        bot.sendMessage(context.id, 'There are no mods in this channel', reply_markup=ReplyKeyboardRemove())
        return False
    counter = 0
    keyboard = [[]]
    for mod in [m[0] for m in mods]:
        keyboard[-1].append(KeyboardButton(text=mod))
        if counter % 2 == 0:  # todo config literal
            keyboard.append([])
    context.context = 'unmod'
    context.next = None
    bot.sendMessage(context.id, f'Whose moderator privileges do you want to revoke?', reply_markup=ReplyKeyboardMarkup(keyboard=keyboard))
    return True

def send_unban_prompt(msg, session, context):  # DONE TODO: squash
    if context.channel is None or not check_admin(context.channel, context.id)[1]:
        context.context = 'choose'
        context.next = '/unban'
        channels = session.query(Channel).filter(Channel.owner == context.id).all()  # all admining
        if channels.__len__() == 0:
            bot.sendMessage(context.id, 'There are no channels where you\'re and admin. \n Just add me to a channel as an admin and do /manage')
            return False
        return send_channel_choice(context.id, channels)
    banned = session.query(UserContext.username).join(Ban, Ban.user == UserContext.id).filter(Ban.channel == context.channel).all()
    if banned.__len__() == 0:
        bot.sendMessage(context.id, 'No one is banned yet.', reply_markup=ReplyKeyboardRemove())
        return False
    counter = 0
    keyboard = [[]]
    for ban in [m[0] for m in banned]:
        keyboard[-1].append(KeyboardButton(text=ban))
        if counter % 2 == 0:  # todo config literal
            keyboard.append([])
    context.context = 'unban'
    context.next = None
    bot.sendMessage(context.id, f'Who do you want to unban?', reply_markup=ReplyKeyboardMarkup(keyboard=keyboard))
    return True


def send_unmanage_prompt(msg, session, context):
    if context.channel is None or not check_admin(context.channel, context.id)[1]:
        context.context = 'choose'
        context.next = '/unmanage'
        channels = session.query(Channel).filter(Channel.owner == context.id).all()  # all admining
        if channels.__len__() == 0:
            bot.sendMessage(context.id, 'There are no channels where you\'re and admin. \n Just add me to a channel as an admin and do /manage') # TODO: squash
            return False
        return send_channel_choice(context.id, channels)
    context.context='unmanage'
    context.next = None
    bot.sendMessage(context.id, 'Accept if you\'re sure.',
                    reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Accept')]]))
    return True

def cancel_prompt(msg, session, context):
    context.context = None
    context.channel = None
    context.next = None
    return send_help(msg, session, context)

def parse_stupid_start(msg, session, context):
    # context presumably new.
    text = msg.get('text', '')
    text = text.split(' ')
    if text.__len__() == 1:
        return send_help(msg, session, context)
    channel = session.query(Channel).filter(Channel.id == text[1]).first()
    if channel is None:
        return False
    # else we have a valid channel and a starting point
    if not check_banned(context, channel, session):
        context.channel = channel.id
    return send_help(msg, session, context)  # /start always should send help

def choose_channel_callback(msg, session, context):
    ch_name = msg.get('text', '')
    channel = session.query(Channel).filter(Channel.name == ch_name).first()
    if channel is None:
        bot.sendMessage(context.id, 'That\'s not a channel I know. Try the buttons.')
        return False
    context.channel = channel.id
    context.context = None
    return True
def unmod_callback(msg, session, context):
    if not check_admin(context.channel, context.id)[1]:
        bot.sendMessage(context.id, 'Check yourself before you wreck yourself')
        return False
    poor_bastard = msg.get('text', '')
    mod = session.query(Mod).join(UserContext, UserContext.id == Mod.user).filter(Mod.channel == context.channel).filter(UserContext.username == poor_bastard).first()
    if mod is None:
        bot.sendMessage(context.id, 'That\'s not a moderator. Try the buttons.')
        return False
    channel = session.query(Channel).filter(Channel.id == context.channel).first()
    bot.sendMessage(mod.user, f'You have been demoted and no longer moderate "{channel.name}" channel')
    session.delete(mod)
    bot.sendMessage(context.id, f'Unmodded {poor_bastard} from {channel.name}')
    context.context = None
    return send_help(msg, session, context)

def unban_callback(msg, session, context):
    if not check_admin(context.channel, context.id)[1]:
        bot.sendMessage(context.id, 'Check yourself before you wreck yourself')
        return False
    lucky_bastard = msg.get('text', '')
    ban = session.query(Ban).join(UserContext, UserContext.id == Ban.user).filter(Ban.channel == context.channel).filter(UserContext.username == lucky_bastard).first()
    if ban is None:
        bot.sendMessage(context.id, 'That\'s not a banned user. Try the buttons.')
    channel = session.query(Channel).filter(Channel.id == context.channel).first()
    bot.sendMessage(ban.user, f'Your ban from {channel.name} has been lifted')
    session.delete(ban)
    bot.sendMessage(context.id, f'Unbanned {lucky_bastard} from {channel.name}')
    context.context = None
    return send_help(msg, session, context)

def unmanage_callback(msg, session, context):
    if not check_admin(context.channel, context.id)[1]:
        bot.sendMessage(context.id, 'Check yourself before you wreck yourself')
        return False
    text = msg.get('text', '')
    if text != 'Accept':
        bot.sendMessage(context.id, 'If you\'re not sure issue any command or use /cancel')
        return False
    unmanage_channel(context.channel, context.id, session)
    context.context = None
    return send_help(msg, session, context)

# private utility
def check_banned(context, channel, session):
    if context.id == channel.owner:
        return False  # TODO: complex checks?
    banned = session.query(Ban).filter(Ban.channel == channel.id).filter(Ban.user == context.id).first()
    if banned is None:
        return False
    else:
        return True

def send_channel_choice(cid, channels):  # DONE
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
    msg = msg['channel_post']
    routing_table = {
        'text': handle_channel_command,
    }
    route = do_route(routing_table, msg)
    if route is False:  # only parse text
        return route
    else:
        return route(msg, session)


def handle_channel_command(msg, session):  # DONE
    #if msg['text'] in ['/unmanage', f'/unmanage@{current_username}']:  # TODO: may be config literals?
    #    return unmanage_channel(msg['chat']['chat_id'], True, session)  # No unmanaging from channel itself.
    if msg['text'] in ['/manage', f'/manage@{current_username}']:
        chat = msg.get('chat', {})
        return manage_channel(chat, session)  # Working with Telegram Objects
    else:
        return False


def manage_channel(chat, session):  # id, name, link, owner DONE
    # id, name, link, owner
    l.debug(f'Trying to manage {chat}')
    bot_is_admin, issued_by_owner = check_admin(chat.get('id'), -1)
    if not bot_is_admin:
        try:
            bot.sendMessage(issued_by, 'Make me an admin with post and edit permissions first!')
        except TelegramError:
            return False
    # if all permissions present: check if owner opened a chat
    try:
        admins = bot.getChatAdministrators(chat.get('id'))
        owner = -1
        for admin in admins:
            if admin.get('status') == 'creator':
                    owner = admin.get('user', {}).get('id')
        if owner == -1:
            return False
        channel = Channel(id=chat.get('id'), name=chat.get('title'), link=chat.get('username'), owner=owner)
        session.add(channel)
        bot.sendMessage(owner, f'You started managing {channel.name}\nTo undo this you can use /unmanage from anywhere.')
        session.commit()  # make sure all is well before messaging.
        msg_to_pin = bot.sendMessage(chat.get('id'),
                        f"This channel is now managed by a bot!\n"
                        f"If you want to submit something to this channel, message @{current_username} and choose this channel\n"
                        f"Or just go here: http://t.me/{bot.getMe().get('username')}?start={chat.get('id')}",
                        disable_web_page_preview=True,
                        disable_notification=True,)
        bot.pinChatMessage(channel.id, msg_to_pin['message_id'])
        return True
    except TelegramError:
        bot.sendMessage(chat.get('id'), f"The owner needs to message the bot first.\n"
                                        f"http://t.me/{current_username}")  # TODO: something user-friendly here.
        return False


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
    msg = msg['inline_query']
    query = msg.get('query')


def handle_chosen_inline(msg, session):
    msg = msg['chosen_inline_result']

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
    l.debug(f'Trying to match {switch} to {case}')
    for key in switch:
        if key in case.keys():
            return switch.get(key)
    return False

def list_to_readable(lst, repl=', '):
    return lst.__str__()[1:-1].replace("'", '').replace(', ', repl)