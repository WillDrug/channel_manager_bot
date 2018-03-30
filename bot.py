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
    9) /remind -- remind a mod about your submission if you didn't get a response (for admin reminds all mods in a channel)
    PLANNED:
    9) /notifyban --
    10) /notifydecline --
    11) /notifyaccept --
"""
# TODO: no submissions for admins, mods don't approve their own content
from time import time
import os
from uuid import uuid4
from telepot import Bot, glance, flavor
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, InlineQuery, InlineQueryResultArticle, \
    ChosenInlineResult, InputTextMessageContent, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telepot.exception import TelegramError
from model import Channel, UserContext, Mod, Ban, Message, Invite, Bullshit, new_session
from config import config
from sqlalchemy import func, asc, or_
import logging as l
import sys

token = os.environ.get('SECRET')

bot = Bot(token)
bot.deleteWebhook()

current_username = bot.getMe().get("username")


# TODO: cleanup when bot is kicked.

# ENTRYPOINT

def handle(msg):
    l.debug(f'Handling msg')
    session = new_session()  # sql session to be shared between functions
    inbound_field = do_route(
        {'message': 'message', 'inline_query': 'inline_query',
         'chosen_inline_result': 'chosen_inline_result', 'callback_query': 'callback_query'},
        msg
    )
    if inbound_field is not False:
        cid = msg.get(inbound_field, {}).get('from', {}).get('id')
        bullshit_session = new_session()
        bullshit = bullshit_session.query(Bullshit).filter(Bullshit.id == cid).first()
        if bullshit is None:
            bullshit = Bullshit(id=cid, counter=0)
            bullshit_session.add(bullshit)
        if is_bullshitter(bullshit):
            on_bullshit(bullshit)
            return False
    try:
        res = route_message(msg, session)
        if not res:
            l.info(f'Got bullshit msg')
            if inbound_field is not False:
                on_bullshit(bullshit)
            session.commit()
            #return False
        else:
            l.info(f'Got ok msg')
            if inbound_field is not False:
                on_success(bullshit)
            session.commit()
            #return True
    except Exception as e:
        if inbound_field is not False:
            on_bullshit(bullshit)
        l.critical(f'Exception: {e.__str__()}; {sys.exc_info()}')
        session.rollback()
        #return False
    if inbound_field is not False:
        bullshit_session.commit()


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


def on_bullshit(bullshit):
    bullshit.counter += 1
    if bullshit.counter >= config.bullshit_threshhold and not bullshit.sent_warning:
        bot.sendMessage(bullshit.id, 'You have sent too much failed queries and has been banned for 24 hours.\n'
                                     'Note that doing that again will extend your ban time. Be patient.')
        bullshit.took_the_piss_at = int(time())


def on_success(bullshit):
    bullshit.counter = int(bullshit.counter / 2)


def is_bullshitter(bullshit):
    print(bullshit.counter)
    if bullshit.took_the_piss_at is not None:
        if int(time()) - bullshit.took_the_piss_at > config.bullshit_punish:
            bullshit.took_the_piss_at = None
            bullshit.sent_warning = False
            bullshit.counter = int(bullshit.counter/2)
            return False
        return True
    else:
        return False

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


def handle_message_text(msg, session,
                        context):  # DONE # TODO: reply_to_message TODO: redo to class with self.msg\session\context
    routing_table = {  # all commands are returned as generics, always.
        '/help': send_help,
        '/mod': send_mod_button,
        '/modlist': send_mod_list,
        '/unmod': send_unmod_prompt,
        '/banlist': send_ban_list,
        '/unban': send_unban_prompt,
        '/start': parse_stupid_start,
        '/unmanage': send_unmanage_prompt,
        '/cancel': cancel_prompt,
        '/poke': poke_mod,
        '/submit': submit_command,
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
        'choose': choose_channel_callback,  # choosen a channel or bullshit
        'unmod': unmod_callback,  # chosen who to unmod or bullshit
        'unban': unban_callback,  # chosen who to unban or bullshit
        'unmanage': unmanage_callback,  # awaiting accept to unmanage command or bullshit
        'submit': submit_to_review,  # awaiting accept to submit or bullshit
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
    # if no command issued - a new submission is presumed
    pending = session.query(Message).filter(Message.from_id == context.id).filter(
        Message.channel == context.channel).filter(Message.assigned_mod is None).first()
    if pending is not None:
        session.delete(pending)
    message = Message(from_id=context.id, channel=context.channel, message_id=msg.get('message_id'))
    session.add(message)
    print(message)
    # request channel if none chosen
    if context.channel is None:
        context.context = 'choose'
        context.next = '/submit'
        banned_sq = session.query(Ban.channel).filter(Ban.user == context.id)
        channels = session.query(Channel).filter(Channel.id.notin_(banned_sq)).all()
        if channels.__len__() == 0:
            bot.sendMessage(context.id, 'You can\'t submit to any channels I manage.\n'
                                        'Consider starting your own! Add me as an admin and run /manage in your channel!')
            context.context = None
            context.next = None
            return False
        return send_channel_choice(context.id, channels)
    # if chosen we can go into submit command right away
    else:
        return submit_command(msg, session, context, force_message=message)

def submit_command(msg,session,context, force_message=None):
    l.debug(f'Submit command issued, with {force_message} force')
    if force_message is None:
        message = session.query(Message).filter(Message.from_id == context.id).first()
        l.debug(f'Pending message is {message}')
        if message is None:
            bot.sendMessage(context.id, 'Just send me anything and I\'ll make a channel post out of it.\n'
                                        'Use /cancel if you have changed your ming',
                            reply_markup=ReplyKeyboardRemove())
            return True
    else:
        message = force_message
    if context.channel is None:
        context.context = 'choose'
        context.next = '/submit'
        banned_sq = session.query(Ban.channel).filter(Ban.user == context.id)
        channels = session.query(Channel).filter(Channel.id.notin_(banned_sq)).all()
        if channels.__len__() == 0:
            context.context = None
            context.next = None
            bot.sendMessage(context.id, 'You can\'t submit to any channels I manage.\n'
                                        'Consider starting your own! Add me as an admin and run /manage in your channel!',
                            reply_markup=ReplyKeyboardRemove())
            return False
        return send_channel_choice(context.id, channels)
    message.channel = context.channel
    context.context = 'submit'
    context.next = None
    channel = session.query(Channel).filter(Channel.id == context.channel).first()
    if channel is None:
        # what? TODO: alert demiurge
        return False
    l.debug(f'Context is {context.context}')
    bot.sendMessage(context.id, f'Would you like to submit that to {channel.name}?',
                    reply_to_message_id=message.message_id,
                    reply_markup=ReplyKeyboardMarkup(keyboard=[[
                        KeyboardButton(text='Submit'),
                        KeyboardButton(text='Another channel'),
                        KeyboardButton(text='/cancel')
                    ]]))
    return True

def submit_to_review(msg, session, context, exclude=None):
    message = session.query(Message).filter(Message.channel == context.channel).filter(Message.from_id == context.id).filter(Message.submit_on.is_(None)).first()
    if message is None:  # WHAT?! TODO: alert demiurge
        return False
    text = msg.get('text')
    if text not in ['Submit', 'Another channel']:
        session.delete(message)
        return False
    if text == 'Another channel':
        context.channel = None
        context.context = None
        context.next = '/submit'
        return True
    context.context = None
    # TODO: check if poster is owner \ admin and go with automatic
    # TODO: OR EITHER don't even handle submissions to owned channels. Why would you?
    if exclude is None:  # TODO: graceful query handling, although nothing really is affected here
        mod = session.query(Mod.user, func.count(Message.id).label('total')).outerjoin(Message, Message.assigned_mod == Mod.user).filter(Mod.channel == context.channel).group_by(Mod.user).order_by(asc('total')).first()
    else:
        mod = session.query(Mod.user, func.count(Message.id).label('total')).outerjoin(Message, Message.assigned_mod == Mod.user).filter(Mod.channel == context.channel).filter(Mod.user != exclude).group_by(Mod.user).order_by(asc('total')).first()
    if mod is None:
        mod = session.query(UserContext.id).join(Channel, Channel.owner == UserContext.id).filter(Channel.id == context.channel).first()
    if mod is None:
        # TODO: really should alert demiurge here
        return False
    mod = mod[0]
    bot.forwardMessage(mod, context.id, message.message_id, disable_notification=True)
    sent = bot.sendMessage(mod, f'This is a submission! Choose what to do with is!',
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Approve', callback_data=f'approve_{message.from_id}_{message.message_id}'),
                               InlineKeyboardButton(text='Decline', callback_data=f'decline_{message.from_id}_{message.message_id}'),
                               InlineKeyboardButton(text='Ban', callback_data=f'ban_{message.from_id}_{message.message_id}'),
                           ]]))
    message.assigned_mod = mod
    message.assigned_id = sent.get('message_id')
    message.submit_on = int(time())
    bot.sendMessage(context.id, 'Sent for review', reply_markup=ReplyKeyboardRemove())
    return True


def send_mod_button(msg, session, context):
    bot.sendMessage(context.id, f'Use this button and choose a chat. '
                                f'You will be prompted to choose a channel for invite generation',
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text='Invite a mod', switch_inline_query=uuid4().__str__())
                    ]]))
    return True

def poke_mod(msg, session, context):
    if context.channel is None:
        context.context = 'choose'
        context.next = None
        banned_sq = session.query(Ban.channel).filter(Ban.user == context.id)
        messages_sq = session.query(Message.channel).filter(Message.from_id == context.id)
        channels = session.query(Channel).filter(Channel.id.notin_(banned_sq)).filter(Channel.id.in_(messages_sq)).all()
        if channels.__len__() == 0:
            bot.sendMessage(context.id, 'You have no posts pending approval.')
            return False
        return send_channel_choice(context.id, channels)
    channel = session.query(Channel).filter(Channel.id == context.channel).first()
    if channel is None:
        # TODO: alert demiurge ? something's fucked
        return False
    if context.id == channel.owner:
        messages = session.query(Message).filter(Message.channel == context.channel).filter(Message.submit_on.isnot_(None)).all()
    else:
        messages = session.query(Message).filter(Message.from_id == context.id).filter(Message.channel == context.channel).filter(Message.submit_on.isnot_(None)).first()
        if messages is None:
            messages = []
        else:
            messages = [messages]  # top kek
    if messages.__len__() == 0:
        bot.sendMessage(context.id, 'No posts are pending approval in this channel')
        return False
    counter_remind = 0
    counter_resend = 0
    for message in messages:
        if int(time()) - message.submit_on > 43200:  # 12 hours, reminder
            bot.sendMessage(message.assigned_mod, f'Someone really wants this message to be submitted!', reply_to_message_id=message.assigned_id)
            counter_remind += 1
        elif int(time()) - message.submit_on > 86400: # 24 hours, resend
            bot.editMessageReplyMarkup((message.assigned_mod, message.assigned_id), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
            submit_to_review(message)
            counter_resend = 0
    response = ""
    if counter_remind == 0 and counter_resend == 0:
        bot.sendMessage(context.id, f'No message waited more than 12 hours.')
        return False
    if counter_remind > 0:
        response += f"Reminded ({counter_remind}) moderators to do their job!"
    if counter_resend > 0:
        if counter_remind > 0:
            response += '\n'
        response += f"Took messages pending from ({counter_resend}) moderators"
    bot.sendMessage(context.id, response)
    return True





def send_help(msg, session, context, expanded=True):  # ONGOING
    try:
        modding = session.query(Channel.name).join(Mod, Channel.id == Mod.channel).filter(Mod.user == context.id).all()
        modding = list_to_readable(modding)
        channels = session.query(Channel.name).filter(Channel.owner == context.id).all()
        channels = channels.__str__()[1:-1].replace("'", '')
        current = session.query(Channel.name).filter(Channel.id == context.channel).first()
        if current is not None:
            current = current[0]
        response = f"*~~Channel Manager Bot~~*\n" \
                   f"*Current channel*: _{current}_\n" \
                   f"*You mod the following channels:* {'_'+modding+'_' if modding != '' else modding}\n" \
                   f"*You admin the following channels:* {'_'+channels+'_' if channels != '' else channels}\n" \
                   f"You can find me [at my github](https://github.com/WillDrug/channel_manager_bot/) " \
                   f"to yell, critique or request features."
        if expanded:
            response += f'*Commands:*\n' \
                        f'/help : Display this message\n' \
                        f'/modlist : List mods for a channel you own\n' \
                        f'/banlist : List banned users for a channel you own\n' \
                        f'/unmod : Stop modding a channel or demote a mod from a channel you own\n' \
                        f'/unban : Unban a user from a channel you own\n' \
                        f'/unmanage : Stop managing a channel (note: bot will leave it)\n' \
                        f'/cancel : Clear current channel and cancel current request\n' \
                        f'/poke : Poke if moderators are taking too long with your post. ' \
                        f'12 hours delay will send a reminder, 24 hour delay will re-send message for approval. ' \
                        f'_If you are the owner, all lazy mods will be poked._'
        bot.sendMessage(context.id, response,
                        disable_web_page_preview=True,
                        parse_mode='markdown',
                        reply_markup=ReplyKeyboardRemove())  # TODO: ??
        l.debug(f'Help returning TRUE')
        return True
    except TelegramError as e:
        l.error(f'{e.__str__()}, {sys.exc_info()}')
        return False


def send_ban_list(msg, session, context):  ## DONE TODO: flat send_*_list into one function
    if context.channel is None or not check_admin(context.channel, context.id)[1]:
        context.context = 'choose'
        context.next = '/banlist'
        channels = session.query(Channel).filter(Channel.owner == context.id).all()  # all admining
        if channels.__len__() == 0:
            bot.sendMessage(context.id,
                            'There are no channels where you\'re and admin. \n '
                            'Just add me to a channel as an admin and do /manage')
            return False
        return send_channel_choice(context.id, channels)
    banned = session.query(UserContext.username).join(Ban, Ban.user == UserContext.id).filter(
        Ban.channel == context.channel).all()  # TODO: move to UTILITY
    if banned.__len__() == 0:
        bot.sendMessage(context.id, 'Noone seems to be banned. Keep it that way!', reply_markup=ReplyKeyboardRemove())
        return True
    banned = list_to_readable([ban[0] for ban in banned], repl='\n')
    bot.sendMessage(context.id, f"Banned:\n{banned}", reply_markup=ReplyKeyboardRemove())
    context.context = None
    context.next = None
    return True  #send_help(msg, session, context)


def send_mod_list(msg, session, context):  # DONE
    if context.channel is None or not check_admin(context.channel, context.id)[1]:
        context.context = 'choose'
        context.next = '/modlist'
        channels = session.query(Channel).filter(Channel.owner == context.id).all()  # all admining
        if channels.__len__() == 0:
            bot.sendMessage(context.id,
                            'There are no channels where you\'re and admin. \n '
                            'Just add me to a channel as an admin and do /manage')
            return False
        return send_channel_choice(context.id, channels)
    mods = session.query(UserContext.username).join(Mod, Mod.user == UserContext.id).filter(
        Mod.channel == context.channel).all()  # TODO: move to UTILITY
    context.context = None
    context.next = None
    if mods.__len__() == 0:
        bot.sendMessage(context.id, 'No moderators are added to the channel yet', reply_markup=ReplyKeyboardRemove())
        return True
    mods = list_to_readable([mod[0] for mod in mods], repl='\n')
    bot.sendMessage(context.id, f"Moderating:\n{mods}", reply_markup=ReplyKeyboardRemove())
    return True  #send_help(msg, session, context)


def send_unmod_prompt(msg, session, context):  # DONE TODO: squash
    if context.channel is None:
        context.context = 'choose'
        context.next = '/unmod'
        mod_sq = session.query(Mod.channel).filter(Mod.user == context.id)
        channels = session.query(Channel).filter(or_(Channel.owner == context.id, Channel.id.in_(mod_sq))).all()  # all admining
        if channels.__len__() == 0:
            bot.sendMessage(context.id,
                            'There are no channels where you\'re and admin or a mod. \n '
                            'Just add me to a channel as an admin and do /manage')
            return False
        return send_channel_choice(context.id, channels)
    channel = session.query(Channel).filter(Channel.id == context.channel).first()
    mod = session.query(Mod).filter(Mod.channel == context.channel).filter(Mod.user == context.id).first()
    if mod is not None:  # user not admin, but mod
        bot.sendMessage(mod.user, f'You are no longer a mod in "{channel.name}"', reply_markup=ReplyKeyboardRemove())
        bot.sendMessage(channel.owner, f'{context.username} is no longer a moderator in "{channel.name}"')
        session.delete(mod)
        return True
    if context.id != channel.owner:
        context.channel = None
        context.context = None
        context.next = None
        bot.sendMessage(context.id, f'You are not an admin or mod here.', reply_markup=ReplyKeyboardRemove())
        return False
    mods = session.query(UserContext.username).join(Mod, Mod.user == UserContext.id).filter(
        Mod.channel == context.channel).all()
    if mods.__len__() == 0:
        bot.sendMessage(context.id, 'There are no mods in this channel', reply_markup=ReplyKeyboardRemove())
        return False
    counter = 0
    keyboard = [[]]
    for mod in [m[0] for m in mods]:
        keyboard[-1].append(KeyboardButton(text=mod))
        if counter % 2 == 0:  # todo config literal
            keyboard.append([])
    keyboard.append([KeyboardButton(text='Another Channel')])
    keyboard.append([KeyboardButton(text='/cancel')])
    context.context = 'unmod'
    context.next = None
    bot.sendMessage(context.id, f'Whose moderator privileges do you want to revoke?',
                    reply_markup=ReplyKeyboardMarkup(keyboard=keyboard))
    return True


def send_unban_prompt(msg, session, context):  # DONE TODO: squash
    if context.channel is None or not check_admin(context.channel, context.id)[1]:
        context.context = 'choose'
        context.next = '/unban'
        channels = session.query(Channel).filter(Channel.owner == context.id).all()  # all admining
        if channels.__len__() == 0:
            bot.sendMessage(context.id,
                            'There are no channels where you\'re and admin. \n '
                            'Just add me to a channel as an admin and do /manage')
            return False
        return send_channel_choice(context.id, channels)
    banned = session.query(UserContext.username).join(Ban, Ban.user == UserContext.id).filter(
        Ban.channel == context.channel).all()
    if banned.__len__() == 0:
        bot.sendMessage(context.id, 'No one is banned yet. Use /cancel to switch channel', reply_markup=ReplyKeyboardRemove())
        return False
    counter = 0
    keyboard = [[]]
    for ban in [m[0] for m in banned]:
        keyboard[-1].append(KeyboardButton(text=ban))
        if counter % 2 == 0:  # todo config literal
            keyboard.append([])
    keyboard.append([KeyboardButton(text='Another Channel')])
    keyboard.append([KeyboardButton(text='/cancel')])
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
            bot.sendMessage(context.id,
                            'There are no channels where you\'re and admin. \n Just add me to a channel as an admin and do /manage')  # TODO: squash
            return False
        return send_channel_choice(context.id, channels)
    context.context = 'unmanage'
    context.next = None
    bot.sendMessage(context.id, 'Accept if you\'re sure.',
                    reply_markup=ReplyKeyboardMarkup(keyboard=[[
                        KeyboardButton(text='Accept'),
                        KeyboardButton(text='/cancel')
                    ]]))
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
    l.debug(f'start has {text.__len__()-1} additional info')
    if text.__len__() == 1:
        return send_help(msg, session, context)
    if text[1].startswith('mod'):
        l.debug(f'Adding a mod!')
        command = text[1].split('_')
        if command.__len__() == 1:
            send_help(msg, session, context)
            return False
        command = command[1]
        invite = session.query(Invite).filter(Invite.code == command).first()
        if invite is None:
            send_help(msg, session, context)
            return False  # clear bullshit
        # make a mod
        mod = Mod(user=context.id, channel=invite.channel)
        channel = session.query(Channel).filter(Channel.id == mod.channel).first()
        if channel is None:
            # TODO: ALERT DEMIURGE THIS IS BOGUS
            return False
        ban = session.query(Ban).filter(Ban.channel == channel.id).filter(Ban.user == context.id).first()
        if ban is not None:
            session.delete(ban)
            bot.sendMessage(context.id, f'You are unbanned from channel "{channel.name}" because you were invited to mod it.')
            bot.sendMessage(channel.owner, f'User, {context.username} was unbanned from "{channel.name}" due to mod status')
        if channel.owner == context.id:
            bot.sendMessage(context.id, 'You don\'t need to make yourself a mod.')
            return False
        session.add(mod)
        bot.sendMessage(context.id, f'You are now a mod in "{channel.name}" and will be getting submissions to approve')
        bot.sendMessage(channel.owner, f'Congratulations, {context.username} agreed to mod "{channel.name}"')
        return True
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
    if poor_bastard == 'Another Channel':
        context.context = None
        context.channel = None
        context.next = '/unmod'
        return True
    mod = session.query(Mod).join(UserContext, UserContext.id == Mod.user).filter(
        Mod.channel == context.channel).filter(UserContext.username == poor_bastard).first()
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
    if lucky_bastard == 'Another Channel':
        context.channel = None
        context.next = '/unban'
        context.context = None
        return True
    ban = session.query(Ban).join(UserContext, UserContext.id == Ban.user).filter(
        Ban.channel == context.channel).filter(UserContext.username == lucky_bastard).first()
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
        keyboard.append([KeyboardButton(text='/cancel')])
        bot.sendMessage(cid, f'Choose a channel',
                        reply_markup=ReplyKeyboardMarkup(keyboard=keyboard))
        return True
    except TelegramError:
        return False


# channel
def handle_channel(msg, session):  # Only listen for /manage and /unmanage commands  DONE
    # TODO:
    # {'channel_post': {'message_id': 299,
    #                  'chat': {'id': -1001204546755, 'title': 'Test Channel This is, yes', 'username': 'test_ch_ch_ch',
    #                           'type': 'channel'}, 'date': 1522263302, 'new_chat_title': 'Test Channel This is, yes'}}
    msg = msg['channel_post']
    routing_table = {
        'text': handle_channel_command,
        'new_chat_title': new_chat_title
    }
    route = do_route(routing_table, msg)
    if route is False:  # only parse text
        return route
    else:
        return route(msg, session)


def handle_channel_command(msg, session):  # DONE
    # if msg['text'] in ['/unmanage', f'/unmanage@{current_username}']:  # TODO: may be config literals?
    #    return unmanage_channel(msg['chat']['chat_id'], True, session)  # No unmanaging from channel itself.
    if msg['text'] in ['/manage', f'/manage@{current_username}']:
        chat = msg.get('chat', {})
        return manage_channel(chat, session)  # Working with Telegram Objects
    else:
        return False

def new_chat_title(msg, session):
    inner_session = new_session()
    channel = session.query(Channel).filter(Channel.id == msg.get('chat', {}).get('id')).first()
    if channel is None:
        return False
    channel.name = msg.get('new_chat_title')
    inner_session.commit()
    inner_session.close()
    return True


def manage_channel(chat, session):  # id, name, link, owner DONE
    # id, name, link, owner
    l.debug(f'Trying to manage {chat}')
    bot_is_admin, issued_by_owner = check_admin(chat.get('id'), -1)
    if not bot_is_admin:
        try:
            bot.sendMessage(chat.get('id'), 'Make me an admin with post and edit permissions first!')
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
        bot.sendMessage(owner,
                        f'You started managing {channel.name}\nTo undo this you can use /unmanage from anywhere.')
        session.commit()  # make sure all is well before messaging.
        msg_to_pin = bot.sendMessage(chat.get('id'),
                                     f"This channel is now managed by a bot!\n"
                                     f"If you want to submit something to this channel, "
                                     f"message @{current_username} and choose this channel\n"
                                     f"Or just go [here](http://t.me/"
                                     f"{bot.getMe().get('username')}?start={chat.get('id')})",
                                     disable_web_page_preview=True,
                                     disable_notification=True, )
        bot.pinChatMessage(channel.id, msg_to_pin['message_id'])
        return True
    except TelegramError:
        bot.sendMessage(chat.get('id'), f"[The owner needs to message the bot first.]"
                                        f"(http://t.me/{current_username})")  # TODO: something user-friendly here.
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
    #query = msg.get('query') # DISREGARDING QUERY
    query_id = msg.get('id')
    from_id = msg.get('from', {}).get('id')
    channels = session.query(Channel).filter(Channel.owner == from_id).all()
    l.debug(f'{from_id} has {channels.__len__()} channels')
    articles = []
    for channel in channels:
        code = uuid4().__str__()
        l.debug(f'Adding {channel.name}')
        articles.append(
            InlineQueryResultArticle(
                id=f'{channel.id}_{code}',
                title=f'Make mod for: {channel.name}',
                input_message_content=InputTextMessageContent(
                    message_text=f'You are invited to be a moderator in {channel.name}\n'
                                 f'If you agree, follow the link below and press start\n'
                                 f'http://t.me/{current_username}/?start=mod_{code}',
                    disable_web_page_preview=True,
                )
            )
        )
    bot.answerInlineQuery(query_id, articles, cache_time=1)
    l.debug(f'Answered')
    return True


def handle_chosen_inline(msg, session):
    msg = msg['chosen_inline_result']
    channel, code = msg.get('result_id').split('_')
    invite = Invite(channel=channel, code=code)
    session.add(invite)
    return True



# callback
def handle_callback_query(msg, session):
    msg = msg['callback_query']
    routing_table = {
        'approve': accept_submission,
        'decline': reject_submission,
        'ban': ban_user,
    }
    try:
        command, from_id, message_id = msg.get('data').split('_')
    except ValueError:
        return False
    route = do_route(routing_table, {command: 'placeholder'})  # TODO: graceful route function?
    message = session.query(Message).filter(Message.message_id == message_id).filter(Message.from_id == from_id).first()
    if route is False:
        # TODO: WHAT?
        return False
    if message is None:
        bot.editMessageReplyMarkup((msg.get('message', {}).get('from', {}).get('id'), msg.get('message', {}).get('message_id')),
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        bot.sendMessage(msg.get('chat_instance'), 'Message seems to be deleted somehow. sorry.')
        return False
    return route(message, session)

def accept_submission(message, session):
    l.debug(f'doing forward to {message.channel} from {message.from_id}:{message.message_id}')
    bot.forwardMessage(message.channel, message.from_id, message.message_id)
    l.debug(f'informing {message.assigned_mod} that message approved')
    bot.sendMessage(message.assigned_mod, 'Message approved', reply_to_message_id=message.assigned_id)
    l.debug(f'informing {message.from_id} author')
    bot.sendMessage(message.from_id, 'Your submission was approved', reply_to_message_id=message.message_id)
    l.debug(f'deleting reply for {message.assigned_mod}:{message.assigned_id}')
    bot.editMessageReplyMarkup((message.assigned_mod, message.assigned_id), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
    session.delete(message)
    return True

def reject_submission(message, session):
    bot.sendMessage(message.assigned_mod, 'Message declined', reply_to_message_id=message.assigned_id)
    bot.sendMessage(message.from_id, 'Your submission was declined', reply_to_message_id=message.message_id)
    bot.editMessageReplyMarkup((message.assigned_mod, message.assigned_id), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
    session.delete(message)
    return True

def ban_user(message, session):
    bannable = True
    # 1) check if user is a mod
    mod = session.query(Mod).filter(Mod.user == message.from_id).filter(Mod.channel == message.channel).first()
    # 2) check if user is owner
    channel = session.query(Channel).filter(Channel.id == message.channel).filter(Channel.owner == message.from_id).first()
    if mod is not None or channel is not None:
        bannable = False
    # 3) else ban
    if bannable:
        session.add(Ban(channel=message.channel, user=message.from_id))
        bot.sendMessage(message.assigned_mod, 'User banned', reply_to_message_id=message.assigned_id)
        bot.sendMessage(message.from_id, 'You were banned in this channel', reply_to_message_id=message.message_id)
        bot.editMessageReplyMarkup((message.assigned_mod, message.assigned_id), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        session.delete(message)
    else:
        bot.sendMessage(message.from_id, 'Submission was declined but the mod was unable to ban you.', reply_to_message_id=message.message_id)
        bot.sendMessage(message.assigned_mod, 'Submission was declined but you can\'t ban this user', reply_to_message_id=message.assigned_id)
        bot.editMessageReplyMarkup((message.assigned_mod, message.assigned_id), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
        session.delete(message)
    return True


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
