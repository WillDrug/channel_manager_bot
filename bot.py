from time import time
import os
from uuid import uuid4
from telepot import Bot, glance, flavor
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, InlineQuery, InlineQueryResultArticle, \
    ChosenInlineResult, InputTextMessageContent, ReplyKeyboardMarkup, KeyboardButton
from telepot.exception import TelegramError
from model import Channel, UserContext, Invite, Mod, Banned, Message, new_session, Bullshit
from config import config
from sqlalchemy import func, asc
import logging

# TODO: plan on DB expansion and migrationfff
# TODO: move to config + obfuscate
demiurge = 391834810
bullshit_threshhold = 20

token = os.environ.get('SECRET')

bot = Bot(token)
bot.deleteWebhook()


# MAIN
def handle(msg):
    # Generate a new sqlalchemy session for each request to avoid conflicts
    # TODO: test simultaneous requests
    session = new_session()
    try:
        if handle_handle(msg, session) != 'BULLSHIT':  # if main handle function returned BULLSHIT TODO: something more graceful
            bull = session.query(Bullshit).filter(Bullshit.id == msg.get('chat', {}).get('id')).first()
            if bull is not None:
                bull.counter = int(bull.counter / 2)
        session.commit()
        logging.debug(f'handled {msg}')
    except Exception as e:
        logging.critical(e)
        session.rollback()  # rollback changes made

def handle_handle(msg, session):
    flavour = flavor(msg)
    if flavour == 'chat':  # chatting
        content_type, chat_type, chat_id = glance(msg)
        if is_bullshitter(chat_id, session):
            return bullshit(chat_id, session)  # if someone keeps bullshitting
        if chat_type == 'private':  #
            context = session.query(UserContext).filter(UserContext.id == chat_id).first()
            command = get_command(msg)[0]  # getting a command from a message
            if context is None:  # new user
                bot.sendMessage(chat_id,
                                'Hello! I am Channel Manager Bot!\n'
                                'Please pardon the lag, my server is made of potatoes and is free.\n'
                                '**Feature Creep List**:\n'
                                '`> Shadow-bans`\n'
                                '`> Anonymous submissions`\n'
                                '`> Verbosity switch to not spam creator`\n'
                                'Suggestions are welcome [at my github](https://github.com/WillDrug/channel_manager_bot)',
                                parse_mode='markdown', disable_web_page_preview=True)
                context = UserContext(id=chat_id, username=msg['from']['username'], menu='main_menu')
                session.add(context)
                #session.commit() managed upstream
            if command == '/reset':
                context.menu = 'main_menu'
                context.channel = None
                msg['text'] = '/help'
            return route(msg, context, session)
        elif chat_type == 'channel':
            if content_type == 'text':
                return main_channel_menu(msg, chat_id, session)
            else:
                # bullshit(chat_id) ?
                return True
        else: # someone added a user to a group?
            bot.leaveChat(chat_id)
            bullshit(chat_id, session)
            return True
    elif flavour == 'callback_query':  # TODO: switch literals to config strings?
        query_id, from_id, query_data = glance(msg, flavor='callback_query')

        if is_bullshitter(from_id, session):  # additional check because telegram has different data structures
            bullshit(from_id, session)
            return True
        choice, action, data = query_data.split('_')
        context = session.query(UserContext).filter(UserContext.id == from_id).first()
        if context is None:
            # WHAT?!
            bullshit(from_id, session)
            return True
        if choice == 'choice':  # TODO: pack those globs into functions
            ch = session.query(Channel).filter(Channel.id == data).first()
            # reworked to better suit each option
            # if ch is None or (ban_check is not None and ch.owner != from_id):
            #    return bot.sendMessage(from_id, 'That\' not something I manage... Weird')
            context.channel = ch.id
            context.menu = 'channel_menu'

            success = True
            response = ''

            if action == 'none':
                ban_check = session.query(Banned).filter(Banned.channel == data).filter(Banned.user == from_id).first()  # TODO: proper exception join
                if ban_check and ch.owner != from_id:
                    success = False
                    response = 'You are banned there. how did you even get a button?'

            elif action == 'unmod':
                mod = session.query(Mod).filter(Mod.mod_id == from_id).filter(Mod.channel == data).first()
                if mod is None:
                    #bot.sendMessage(from_id, 'You are not modding that...')
                    context.menu = 'main_menu'
                    context.channel = None
                    success = False #return bullshit(from_id, session)
                    response = 'You are not modding that'
                else:
                    user = mod.mod_name
                    banned = session.query(Banned).filter(Banned.channel == mod.channel).filter(Banned.user == mod.mod_id).first()
                    session.delete(mod)
                    #session.commit()
                    bot.sendMessage(ch.owner, f'{user} is tired and is no longer a mod')
                    bot.sendMessage(from_id, f'Success! You are not a mod anymore. {ch.name} Menu:')
                    if banned is not None:
                        context.menu = 'main_menu'
                        context.channel = None
                        success = False
                        response = 'You are banned, though... Redirecting to main menu.'

            elif action == 'admin':
                if ch.owner != from_id:
                    success = False
                    response = 'You don\'t own that.'
                else:
                    context.menu = 'admin_menu'
                    context.channel = ch.id
                    session.commit()
                    hlp = help_message(menu='admin')
                    bot.sendMessage(from_id, hlp[0], reply_markup=hlp[1])
            else:
                # action contains submission id
                msg_o = session.query(Message).filter(Message.id == action).first()
                to_delete = accept_review(from_id, msg_o.id)
                msg_o.current_request = f"{from_id};{to_delete['message_id']}"
                msg_o.channel = data
            # bullshit!
            try:
                bot.editMessageReplyMarkup((from_id, msg['message']['message_id']), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
            except Exception as e:
                pass

            if not success:
                context.menu = 'main_menu'
                context.channel = None
                bot.sendMessage(from_id, response)
                return bullshit(from_id, session)
            elif context.menu == 'channel_menu':
                hlp = help_message(menu='ch_menu')
                bot.sendMessage(from_id, hlp[0], reply_markup=hlp[1])
                return True
            else:
                return True

        elif choice == 'submission':
            msg_o = session.query(Message).filter(Message.id == data).first()
            if msg_o is None:
                bot.answerCallbackQuery(query_id, text='You have already done that')
                return bullshit(from_id, session)
            else:
                cr_chat, cr_id = msg_o.current_request.split(';')
                bot.editMessageReplyMarkup((cr_chat, cr_id), InlineKeyboardMarkup(inline_keyboard=[[]]))

            if action == 'submit':
                return submit_to_review(msg_o, session)

            elif action == 'cancel':
                session.delete(msg_o)
                #session.commit()
                bot.sendMessage(from_id, 'As you wish')
                return True

            if msg_o.assigned_mod != from_id:
                bot.answerCallbackQuery(query_id, 'Mod has changed for this message')
                return True
            if action == 'approve':
                msg_o_channel = msg_o.channel
                msg_o_from_id = msg_o.from_id
                msg_o_message_id = msg_o.message_id
                session.delete(msg_o)
                #session.commit()
                to_link = bot.forwardMessage(msg_o_channel, msg_o_from_id, msg_o_message_id)
                bot.sendMessage(msg_o_from_id, 'Your post was approved', reply_to_message_id=msg_o_message_id)
                ch = session.query(Channel).filter(Channel.id == msg_o.channel).first()
                result = f"{msg['from']['username']} approved a message in {ch.name}:"
                msg_o.published_on = int(time())
                if ch.link is not None:
                    result += f"\nhttp://t.me/{ch.link}/{to_link['message_id']}"
                #session.commit()
                bot.sendMessage(ch.owner, result)
                return True

            elif action == 'decline':
                chat_id = msg_o.from_id
                reply_to = msg_o.message_id
                session.delete(msg_o)
                #session.commit()
                bot.sendMessage(msg_o.from_id, 'Your submission was declined. Sorry.', reply_to_message_id=reply_to)
                # TODO V2: verbose options to creator
                bot.sendMessage(chat_id, 'Done!')
                return True

            elif action == 'ban':
                ban = Banned(channel=msg_o.channel, user=msg_o.from_id, username=msg_o.from_username)
                session.add(ban)
                msgs_t = session.query(Message).filter(Message.from_id == msg_o.from_id).all()
                for msg_t in msgs_t:
                    session.delete(msg_t)
                context = session.query(UserContext).filter(UserContext.id == ban.user).first()
                if context is not None:
                    context.channel = None
                    context.menu = 'main_menu'
                #session.commit()
                bot.sendMessage(ban.user,
                                'You have been banned by a mod.\nYou can be unbanned only by the channel creator')  # TODO v2: shadowban option
                bot.sendMessage(ban.user, help_message()[0])
                bot.sendMessage(from_id, 'Ban succesfull\nNote that only channel creator can unban!')
                return True
        elif choice == 'admin':
            if action == 'unban':
                ban = session.query(Banned).filter(Banned.channel == context.channel).filter(Banned.user == data).first()
                if ban is None:
                    alert_demiurge(f'Tried to unban non-existent user by button! D:')
                    bot.sendMessage(from_id, 'Not banned... somehow')
                    return True
                ch = session.query(Channel).filter(Channel.id == context.channel).first()
                bot.sendMessage(ban.user, f'You are unbanned from channel {ch.name}')
                session.delete(ban)
                bot.sendMessage(from_id, 'Unbanned and alerted')
                bot.editMessageReplyMarkup((from_id, msg['message']['message_id']), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
                return True
            elif action == 'unmod':

                mod = session.query(Mod).filter(Mod.channel == context.channel).filter(Mod.mod_id == data).first()
                if mod is None:
                    alert_demiurge('Tried to unmod a non-existing mod by button')
                    return True
                ch = session.query(Channel).filter(Channel.id == context.channel).first()
                bot.sendMessage(mod.mod_id, f'You are unmodded from chanenl {ch.name}')
                bot.sendMessage(from_id, 'Unmodded and alerted')
                session.delete(mod)
                bot.editMessageReplyMarkup((from_id, msg['message']['message_id']), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[]]))
                return True
        else:
            return bullshit(from_id, session)

    if flavour == 'inline_query':
        query_id, from_id, query_string = glance(msg, flavor='inline_query')

        channels = session.query(Channel).filter(Channel.owner == from_id).all()

        articles = []
        for channel in channels:
            code = uuid4()
            articles.append(
                InlineQueryResultArticle(
                    id=f'{channel.id}_{code}',
                    title=f'Make mod for: {channel.name}',
                    input_message_content=InputTextMessageContent(
                        message_text=f'You are invited to be a mod in {channel.name}\n'
                                     f'If you agree, follow the link below and press start\n'
                                     f'http://t.me/{bot.getMe().get("username")}/?start=mod_{code}',
                        disable_web_page_preview=True
                    )
                )
            )
        bot.answerInlineQuery(query_id, articles, cache_time=1)
        return articles
    if flavour == 'chosen_inline_result':
        result_id, from_id, query_string = glance(msg, flavor='chosen_inline_result')
        channel, code = result_id.split('_')
        invite = Invite(invite_hash=code, channel=channel)
        session.add(invite)
        #session.commit()
        return True

    if flavour == 'shipping_query':
        pass
    if flavour == 'pre_checkout_query':
        pass


# PRIVATE MESSAGES
def route(msg, context, session):
    if 'text' in msg:  # TODO v2: graceful handling
        if get_command(msg)[0] == '/start':
            context.menu = 'main_menu'
            #session.commit()
    menus = {
        'main_menu': main_private_menu,
        'channel_menu': channel_private_menu,
        'admin_menu': admin_private_menu,
    }
    if context.menu in menus:
        return menus[context.menu](msg, context, session)
    else:
        return bullshit(context.id, session)


def main_private_menu(msg, context, session):
    # presuming msg is CHAT
    content_type, chat_type, chat_id = glance(msg)
    # 1) send  basic menu info
    # REDONE to not be obnoxious
    # 2) If that's main menu we have no channel Text is treated as a command
    if content_type == 'text':
        command, data = get_command(msg)
        if command == '/start':  # TODO: fix shitty start
            try:
                option, command_hash = data.split('_')
            except ValueError:
                # 3) someone has no idea what are they doing at all
                option = ''

            # possible opt+ions:
            # 1) someone registered as mod -> there's a modhash
            if option == 'mod':
                # owner can mod himself in. who cares.
                invite = session.query(Invite).filter(Invite.invite_hash == command_hash).first()
                if invite is None:
                    bullshit(chat_id, session)
                    bot.sendMessage(chat_id, 'You have no invite, you sly guy')
                    return bullshit(chat_id, session)  # DOUBLE BULLSHIT FOR THAT.
                channel = session.query(Channel).filter(Channel.id == invite.channel).first()
                if channel is None:
                    bot.sendMessage(chat_id, 'I don\'t manage the channel you are invited to... weird')
                    return bullshit(chat_id, session)
                new_mod = Mod(channel=invite.channel, mod_id=chat_id, mod_name=msg['from']['username'])
                session.add(new_mod)
                session.delete(invite)
                #session.commit()
                bot.sendMessage(chat_id, f'You will be getting submits to {channel.name} for approval now!\n'
                                                f'To stop this, use /unmod command')
                return True
            # 2) someone got here from channel to submit -> set context to choose channel, goto submit menu
            elif option == 'submit':
                channel = session.query(Channel).filter(Channel.id == command_hash).first()
                if channel is None:
                    context.channel = None
                    context.menu = 'main_menu'
                    hlp = help_message()
                    bot.sendMessage(chat_id, hlp[0], reply_markup=hlp[1])
                    return bullshit(chat_id, session)
                banned = session.query(Banned).filter(Banned.user == chat_id).filter(
                    Banned.channel == command_hash).first()
                if banned is not None:
                    context.channel = None
                    context.menu = 'main_menu'
                    hlp = help_message()
                    bot.sendMessage(chat_id, hlp[0], reply_markup=hlp[1])
                    return bullshit(chat_id, session)
                context.channel = channel.id
                context.menu = 'channel_menu'
                hlp = help_message(menu='ch_menu')
                bot.sendMessage(chat_id, hlp[0], reply_markup=hlp[1])
                return True
            # 3) Someone ran /manage on channel and we have to make sure we can send shit to him
            elif option == 'own':
                channels = session.query(Channel).filter(Channel.owner == chat_id).filter(
                    Channel.pinned_id.is_(None)).all()
                for channel in channels:
                    if not manage_channel(channel):
                        bot.sendMessage(chat_id, f'Couldn\'t manage {channel.name}\n'
                                                 f'Make sure I\'m there and have privileges to pin and post\n'
                                                 f'Then re-click the link.')
                        # bot.leaveChat(channel.id)  --- Yeah, this was bullshit :-D
                        session.delete(channel)
                    else:
                        context.menu = 'admin_menu'
                        context.channel = channel.id
                #session.commit()
                if context.menu == 'admin_menu':
                    hlp = help_message(menu='admin')
                    bot.sendMessage(chat_id, hlp[0], reply_markup=hlp[1])
                    return True
                else:
                    return True
            # 4) someone has no idea what are they doing at all
            else:
                hlp = help_message()
                bot.sendMessage(chat_id, hlp[0], reply_markup=hlp[1])
                return True
        elif command == '/manage':
            bot.sendMessage(chat_id, 'This command is used in channel only for now\n'
                                            'Run /choose to go into a channel or just send something as a submission and '
                                            'I\'ll prompt you')
            return True
        elif command == '/list':
            response = 'You are modding those:'
            mods = session.query(Mod).filter(Mod.mod_id == chat_id).all()
            for mod in mods:
                ch = session.query(Channel).filter(Channel.id == mod.channel).first()
                response += f'\n{ch.name}'
            return bot.sendMessage(chat_id, response)
        elif command == '/choose':  # Specific choose
            return choose_channel(chat_id, session)
        elif command == '/unmod':
            return choose_channel(chat_id, session, context='unmod')
        elif command == '/admin':
            return choose_channel(chat_id, session, context='admin')
        elif command == '/help':
            hlp = help_message()
            return bot.sendMessage(chat_id, hlp[0], reply_markup=hlp[1])
        elif command != '':
            return bullshit(chat_id, session)

    # everything else is submission (no-command text and not-text type (except stickers))
    elif content_type == 'sticker':
        return bullshit(chat_id, session)
    temp_sess = new_session()
    message = Message(from_id=chat_id, from_username=msg['from']['username'], message_id=msg['message_id'],
                      channel=None, assigned_mod=None)
    temp_sess.add(message)
    temp_sess.commit()
    return choose_channel(chat_id, session, context=message.id)

def channel_private_menu(msg, context, session):
    # presuming context.channel is set up
    content_type, chat_type, chat_id = glance(msg)
    ch = session.query(Channel).filter(Channel.id == context.channel).first()
    if ch is None:
        context.channel = None
        #session.commit()
        hlp = help_message()
        return bot.sendMessage(chat_id, hlp[0], reply_markup=hlp[1])
    if content_type == 'text':
        command = get_command(msg)[0]
        if command == '/unmod':
            # TODO v2: confirm
            mod = session.query(Mod).filter(Mod.mod_id == context.id).filter(Mod.channel == context.channel).first()
            if mod is None:
                bot.sendMessage(chat_id, 'You are not a mod, though.')
                return bullshit(chat_id, session)
            msgs_t = session.query(Message).filter(Message.from_id == mod.mod_id).all()
            session.delete(mod)
            for msg_t in msgs_t:
                submit_to_review(msg_t, session)
            session.commit()
            try:
                bot.sendMessage(ch.owner, f'{context.username} just unmodded himself :(')
            except TelegramError:
                return unmanage_channel(ch, session)
            bot.sendMessage(chat_id, f'You will no longer see posts to approve from {ch.name}')
            return True
        elif command == '/admin':
            if context.id != ch.owner:
                bot.sendMessage(chat_id, 'No you can\'t.')
                return bullshit(chat_id, session)
            context.menu = 'admin_menu'
            #session.commit()
            hlp = help_message(menu='admin')
            bot.sendMessage(chat_id, hlp[0], reply_markup=hlp[1])
            return True
        elif command == '/help':
            hlp = help_message(menu='ch_menu')
            bot.sendMessage(chat_id, hlp[0], reply_markup=hlp[1])
            return True
        elif command != '':
            hlp = help_message(menu='ch_menu')
            bot.sendMessage(chat_id, hlp[0], reply_markup=hlp[1])
            return bullshit(chat_id, session)
    elif content_type == 'sticker':
        bot.sendMessage(chat_id, 'No, submitting stickers to a channel is too much. Denied.')
        hlp = help_message(menu='ch_menu')
        bot.sendMessage(chat_id, hlp[0], reply_markup=hlp[1])
        return bullshit(chat_id, session)
    # everything else are submissions
    temp_sess = new_session()
    to_check = Message(from_id=chat_id, from_username=msg['from']['username'], message_id=msg['message_id'],
                       channel=context.channel)
    temp_sess.add(to_check)
    temp_sess.commit()
    to_delete = accept_review(chat_id, to_check.id)
    to_check.current_request = f"{chat_id};{to_delete['message_id']}"
    temp_sess.commit()
    return True
def admin_private_menu(msg, context, session):
    """
    commands:
        /modlist
        /unmod
        /banlist
        /unban
        /ban
        /unmanage
    :param msg:
    :param context:
    :return:
    """
    content_type, chat_type, chat_id = glance(msg)
    if content_type == 'text':
        command, data = get_command(msg)
        if command == '/modlist':
            response = 'Moderator list:'
            mods = session.query(Mod).filter(Mod.channel == context.channel).all()
            for mod in mods:
                response = response + '\n' + mod.mod_name
            bot.sendMessage(chat_id, response)
            return True
        elif command == '/unmod':
            if data == '_':
                mods = session.query(Mod).filter(Mod.channel == context.channel).all()
                if mods.__len__() == 0:
                    bot.sendMessage(chat_id, 'There are no mods yet')
                    return bullshit()
                keyboard = []
                for mod in mods:
                    keyboard.append([InlineKeyboardButton(text=f'{mod.mod_name}', callback_data=f'admin_unmod_{mod.mod_id}'), ])
                bot.sendMessage(chat_id, f'Choose a mod to shame:', reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
                return True
            mod = session.query(Mod).filter(Mod.channel == context.channel).filter(Mod.mod_name == data).first()
            if mod is None:
                bot.sendMessage(chat_id, f'Moderator with {data} username not found.\n'
                                                f'See /modlist for more details')
                return True
            try:
                channel = session.query(Channel).filter(Channel.id == context.id).first()
                bot.sendMessage(mod.mod_id,
                                f'You have been demoted for channel {channel.name} and will no longer be receiving messages to approve.')
            except TelegramError:
                pass
            except AttributeError:
                # What
                pass
            # reroute messages awaiting approval
            msgs = session.query(Message).filter(Message.assigned_mod == mod.mod_id).all()
            for msg in msgs:
                submit_to_review(msg, session)
            session.delete(mod)
            #session.commit()
            bot.sendMessage(chat_id, f'{data} is not a moderator anymore. Te-he-he!')
            return True
        elif command == '/mod':
            bot.sendMessage(chat_id, 'Use this button and select a chat;\n '
                                            'This randomizes the invite code a bit so it\'s not cheated.',
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                       InlineKeyboardButton(
                                           text='Press and choose mod',
                                           switch_inline_query=uuid4().__str__()
                                       )
                                   ]]))
            return True
        elif command == '/banlist':
            response = 'Currently banned:'
            banlist = session.query(Banned).filter(Banned.channel == context.channel).all()
            for banned in banlist:
                response = response + '\n' + banned.username
            bot.sendMessage(chat_id, response)
            return True
        elif command == '/unban':
            if data == '_':
                banned = session.query(Banned).filter(Banned.channel == context.channel).all()
                if banned.__len__() == 0:
                    bot.sendMessage(chat_id, 'Noone is banned yet')
                    return True
                keyboard = []
                for ban in banned:
                    keyboard.append([InlineKeyboardButton(text=f'{ban.username}', callback_data=f'admin_unban_{ban.user}')])
                bot.sendMessage(chat_id, 'Choose a person to unban:', reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
                return True
            ban = session.query(Banned).filter(Banned.username == data).filter(
                Banned.channel == context.channel).first()
            if ban is None:
                bot.sendMessage(chat_id, 'This user doesn\'t seem to be banned.\n'
                                                'Consult with /banlist for more details')
                return True
            session.delete(ban)
            #session.commit()
            return bot.sendMessage(chat_id, 'Done.')
        elif command == '/ban':
            if data == '_':
                bot.sendMessage(chat_id, f'Usage: /ban <username>\nOnly works for people who wrote something at least once')
                return True
            ban_id = session.query(UserContext).filter(UserContext.username == data).first()
            if ban_id is None:
                bot.sendMessage(chat_id, 'I can\'t ban people who didn\'t use me yet :( \n'
                                                'Wait for a submission and then banhammer.')
                return True
            banned = Banned(channel=context.channel, user=ban_id.id, username=ban_id.username)
            ban_id.channel = None
            ban_id.menu = 'main_menu'
            session.add(banned)
            #session.commit()
            bot.sendMessage(chat_id, 'Done.')
            return True
        elif command == '/unmanage':
            channel = session.query(Channel).filter(Channel.id == context.channel).first()
            return unmanage_channel(channel, session)
        elif command == '/help':
            hlp = help_message(menu='admin')
            bot.sendMessage(chat_id, hlp[0], reply_markup=hlp[1])
            return True
        else:
            bot.sendMessage(chat_id, f'That\'s not a proper command, though...\n'
                                     f'I don\'t submit those, either.')
            return bullshit(chat_id, session)
    else:
        bot.sendMessage(chat_id, 'I\'m not ready to submit stuff to a channel from admin menu. \n'
                                 'Use /reset and rejoin')
        return True


# CHANNEL MESSAGES

def main_channel_menu(msg, chat_id, session):
    # presuming CHAT - TEXT
    command = get_command(msg)[0]
    if command == '/manage':
        channel = session.query(Channel).filter(Channel.id == chat_id).first()
        if channel is not None:
            bot.sendMessage(channel.owner, 'I alerady manage that, silly!')
            return bullshit(chat_id, session)
        admins = bot.getChatAdministrators(chat_id)
        owner = 0
        for admin in admins:
            if admin['status'] == 'creator':
                owner = admin['user']['id']
        if owner == 0:
            return alert_demiurge(f'No owner for {chat_id}... what.')
        ch = Channel(id=chat_id, name=msg['chat']['title'], link=msg['chat'].get('username', None), owner=owner)
        session.add(ch)
        #session.commit()
        context = session.query(UserContext).filter(UserContext.id == owner).first()

        try:
            if context is not None:
                context.channel = chat_id
                context.menu = 'admin_menu'
                #session.commit()
                hlp = help_message(menu='admin')
                bot.sendMessage(owner, hlp[0], reply_markup=hlp[1])
                # chat with owner is opened, ok
                if not manage_channel(ch):
                    bot.sendMessage(chat_id, 'Couldn\'t start managing the channel. \n'
                                             'Make sure I can send and edit messages and re-run /manage')
                    return True  # TODO :FALSE?
                else:
                    return True
            else:
                # check admin first!
                if check_admin(chat_id):
                    raise TelegramError('sneaky!', 0, '{}')
                else:
                    try:
                        bot.sendMessage(chat_id, 'Give me rights to post and edit first!')
                        return True
                    except TelegramError:
                        session.delete(ch)
                        #session.commit()
                        return True
        except TelegramError:
            if not check_admin(chat_id):
                session.delete(ch)
                #session.commit()
                return True
            else:
                # no chat with owner. do basic stuff and wait for /own link \ command
                bot.sendMessage(chat_id, f"Ready to manage channel; Use this link and START button to confirm:\n"
                                                f"http://t.me/{bot.getMe().get('username')}?start=own_", )
                return True
    elif command == '/unmanage':
        channel = session.query(Channel).filter(Channel.id == chat_id).first()
        if channel is None:
            bot.sendMessage(chat_id, 'Yeah, I don\'t manage that.')
            return bullshit(chat_id, session)  # TODO: differentiate between good and bad
        else:
            return unmanage_channel(channel, session)  # TODO: confirmation button\personal msg
    else:
        return True

# GENERICS
def bullshit(chat_id, session):
    bull = session.query(Bullshit).filter(Bullshit.id == chat_id).first()
    if bull is None:
        bull = Bullshit(id=chat_id, counter=0)
        session.add(bull)
    bull.counter = bull.counter + 1
    if bull.counter >= bullshit_threshhold and bull.added is None:
        bull.added = int(time())
        bot.sendMessage(chat_id, 'BULLSHIT!')
    #session.commit()
    return 'BULLSHIT'


def is_bullshitter(chat_id, session):
    bull = session.query(Bullshit).filter(Bullshit.id == chat_id).first()
    if bull is None:
        return False
    if bull.added is not None:
        if int(time()) - bull.added >= 86400:
            bull.added = None
            #session.commit()
            return False
        else:
            return True
    return False


def accept_review(send_to, msg_id):
    return bot.sendMessage(send_to, f'Ready to submit!',
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Submit', callback_data=f'submission_submit_{msg_id}'),
                               # InlineKeyboardButton(text='Submit Anonymous', callback_data=f'hsubmit_{msg_id}'),
                               InlineKeyboardButton(text='Cancel', callback_data=f'submission_cancel_{msg_id}')
                           ]])
                           )
    
def submit_to_review(msg: Message, session):
    def submit_message(chat_id, msg_id):
        return bot.sendMessage(chat_id, f'You have a message to review:',
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                        InlineKeyboardButton(text='Approve',
                                                             callback_data=f'submission_approve_{msg_id}'),
                                        InlineKeyboardButton(text='Decline',
                                                             callback_data=f'submission_decline_{msg_id}'),
                                        InlineKeyboardButton(text='Ban!', callback_data=f'submission_ban_{msg_id}')
                                    ]]))
    mods = session.query(Mod, func.count(Message.id).label('total')).outerjoin(Message, Message.assigned_mod == Mod.mod_id).\
        group_by(Mod.id).order_by(asc('total')).all()
    done = False
    for mod in mods:
        try:
            mod_id = mod[0].mod_id
            to_delete = submit_message(mod_id, msg.id)
            done = True
            break
        except TelegramError:
            session.delete(mod[0])
            pass
    if not done:
        try:
            ch = session.query(Channel).filter(Channel.id == msg.channel).first()
            mod_id = ch.owner
            to_delete = submit_message(ch.owner, mod_id)
        except TelegramError:
            unmanage_channel(msg.channel, session)
            return True
    msg.current_request = f"{mod_id};{to_delete['message_id']}"
    msg.submitted_on = int(time())
    msg.assigned_mod = mod_id
    #session.commit()
    bot.forwardMessage(mod_id, msg.from_id, msg.message_id)
    return to_delete


def choose_channel(chat_id, session, context='none'):
    channels = session.query(Channel).filter(Channel.pinned_id.isnot(None)).all()
    if channels.__len__() == 0:
        bot.sendMessage(chat_id, 'I don\'t seem to manage any channels right now. '
                                        'Add me as admin and write /manage in your channel to start!')
        return False
    keyboard = []
    for channel in channels:
        approved = True
        ban_check = session.query(Banned).filter(Banned.channel == channel.id).filter(Banned.user == chat_id).first()
        if context == 'unmod':
            mod = session.query(Mod).filter(Mod.mod_id == chat_id).first()
            if mod is None:
                approved = False
            else:
                is_mod = True
        elif context == 'admin':
            if channel.owner != chat_id:
                approved = False
        elif ban_check:  # ban works only if not admin and not mod.
            approved = False

        if approved:
            keyboard.append([
                InlineKeyboardButton(
                    text=channel.name,
                    callback_data=f"choice_{context}_{channel.id}"
                )
            ])
    if keyboard.__len__() == 0:
        if context == 'none':
            response = 'No channels found\nYou might be banned'
        elif context == 'unmod':
            response = 'You don\'t mod any channels'
        elif context == 'admin':
            response = 'You are not an admin anywhere'
        else:
            msg = session.query(Message).filter(Message.id == context).first()
            if msg is not None:
                session.delete(msg)
            response = 'Your submission doesn\'t go anywhere :C no channels available.'
        bot.sendMessage(chat_id, response)
        return False
    bot.sendMessage(
        chat_id,
        'Choose a channel to submit to or manage:',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    return True


def check_admin(channel_id):
    admins = bot.getChatAdministrators(channel_id)
    self_id = bot.getMe().get('id')
    me = None
    for admin in admins:
        if admin.get('user', {}).get('id') == self_id:
            me = admin
    if me is None:
        return False
    if not me['can_post_messages'] or not me['can_edit_messages']:
        return False
    return True


def manage_channel(channel):
    channel_id = channel.id
    # 1) check admin rights
    if not check_admin(channel_id):
        return False
    # 2) send message
    message_to_pin = bot.sendMessage(
        channel_id,
        f"This channel is now managed by a bot!\n"
        f"If you want to submit something to this channel, message @{bot.getMe().get('username')} personally or just go here:\n"
        f"http://t.me/{bot.getMe().get('username')}?start=submit_{channel_id}",
        disable_web_page_preview=True,
        disable_notification=True,
    )
    # 3) pin message
    bot.pinChatMessage(channel_id, message_to_pin['message_id'], disable_notification=True)
    # 4) save structure
    channel.pinned_id = message_to_pin['message_id']
    #session.commit()  # commit this.
    return True


def unmanage_channel(channel, session):
    bot.unpinChatMessage(channel.id)
    bot.sendMessage(channel.id, 'This channel is no longer managed by the bot')
    bot.leaveChat(channel.id)
    session.delete(channel)
    #session.commit()
    return True


def alert_demiurge(message):
    bot.sendMessage(demiurge, message)
    return True

# UTILITY

def get_command(msg):
    if 'entities' not in msg:
        return '', msg.get('text', '')
    command = ''
    the_rest = msg['text']
    for ent in msg['entities']:
        if ent['type'] == 'bot_command':
            command = msg['text'][ent['offset']:ent['length']]
            the_rest = msg['text'][int(ent['offset']) + int(ent['length']):]
    botname = command.find('@')
    if botname > -1:
        command = command[:botname]
    return command, the_rest.strip()

# GENERATORS

def help_message(menu='main'):
    if menu == 'admin':
        return f'Admin menu. Commands:\n' \
               f'/modlist : Displays current channel moderators\n' \
               f'/unmod : Strip someone\'s mod privileges.\n' \
               f'/mod : Shows a useful button to ask someone to be a mod!\n' \
               f'/banlist : Current banlist (sets up by mod request !!UNIMPLEMENTED!!: or after ' \
               f'{bullshit_threshhold} bullshit messages)\n' \
               f'/unban <username> : Unban some user by username\n' \
               f'/ban <username> : Ban some user by username\n' \
               f'/unmanage : Unmanages this channel. !!!UNIMPLEMENTED!!!: Requires additional acceptance\n' \
               f'There are no submissions from here. Go back with /reset and re-choose your channel.',\
               ReplyKeyboardMarkup(keyboard=[
                   [
                       KeyboardButton(text="/modlist"),
                       KeyboardButton(text="/banlist"),
                   ],
                   [
                       KeyboardButton(text="/mod"),
                       KeyboardButton(text="/ban _"),
                   ],
                   [
                       KeyboardButton(text="/unmod _"),
                       KeyboardButton(text="/unban _"),
                   ],
                   [
                       KeyboardButton(text="/reset"),
                   ],
                   [
                       KeyboardButton(text="/unmanage"),
                   ]
               ])
    elif menu == 'ch_menu':
        return f'You are in channel specific menu.\n' \
               f'Anything you send will be treated as a submission. \n' \
               f'If you want to stop modding use /unmod\n' \
               f'If you\'re an admin you can use /admin\n' \
               f'You can always go back with /reset',\
               ReplyKeyboardMarkup(keyboard=[
                   [
                       KeyboardButton(text="/unmod"),
                       KeyboardButton(text="/admin"),
                       KeyboardButton(text="/reset"),
                   ]
               ])
    else:
        return 'Main menu commands:\n' \
               '/admin : will prompt you to choose a channel to admin' \
               '/unmod : will prompt you to choose a channel to stop being a mod on\n' \
               '/choose : will prompt you to choose a channel and help with menus there\n' \
               '/reset will always get you back here\n' \
               'Anything else will be treated as a submission and you will be prompted to choose a channel to submit to.',\
               ReplyKeyboardMarkup(keyboard=[
                   [
                       KeyboardButton(text="/admin"),
                   ],
                   [
                       KeyboardButton(text="/unmod"),
                   ],
                   [
                       KeyboardButton(text="/choose"),
                   ],
                   [
                       KeyboardButton(text="/reset"),
                   ]
               ])

"""
Menu:
    
    send anything that's not a proper command == submit
        -> Choose channel  or cancel # DEEPLINK HERE
            -> submit to moderator
    /admin # only shows up if you're an owner of at least one channel
        -> Choose channel 
            -> /ban list /w Pagination
            -> /unban username
            -> /modlist
            -> /unmod username
            /unmanage -> kills pinned message, send message that this is over, leaves channel (CONFIRM!!)
        
    /unmod: #only appears if you're in modlist 
            -> Choose a channel
    /start$own$ #not showing up --> DONE
        1) Registeres channel, owner
        2) Sends and pins a message to channel
    
    -> Register Mod (inline) -> /start$manage$hash
        -> Mod registered # DEEPLINK FROM INLINE    
    Approve : no button, auto sends shit to you
        -> Approve # no usernames here
        -> Decline 
        -> Ban
In channel:
    -> /manage --> DONE
        0) checks admin privileges$ if not : shit, mate.
        1) generates switch chat button or deeplink for owner --> TODO
    -> /unmanage --> DONE
Posts to approve are sent to moderators who are in approve session$
After timeout (handling?) it is resent to another$ ?????

1) If all mods and owner are unreachable -> ok, but warns submitters
2) If channel is unreachable -> kills channel from list with a warning

========================== REWORKED MENU ==========================
handle()
/reset                          resets menus and channel choice

main_menu()
/start-> own                    activates channel managing
         invite                 adds a mod
         submit                 auto-choice for channel$
         empty                  help()
/choose                         chooses a channel to admin or submit to
-----> inline buttons
channel_menu()
[Submit]
/unmod
/admin->
admin_menu()
  -> /modlist               lists mods
  -> /unmod username        tries to unmod (no username = self)
  -> /banlist               lists bans
  -> /unban username        tries to unban
  -> /ban username
                
[Approve] -> Automatic
========================= REWORKED AGAIN ================================
/reset -> resets
/admin -> choose channel by callback
submission deep link -> channel chosen
/unmod -> choose channel by callback
"""
