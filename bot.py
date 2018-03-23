import os
from uuid import uuid4
from telepot import Bot, glance, flavor
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, InlineQuery, InlineQueryResultArticle, ChosenInlineResult, InputTextMessageContent
from telepot.exception import TelegramError
from model import Channel, UserContext, Invite, Mod, Banned, Message, session
from config import config
from sqlalchemy import func

demiurge = 391834810 # TODO: add maintainer chat id
bullshit_threshhold = 20

token = os.environ.get('SECRET')

bot = Bot(token)
bot.deleteWebhook()

# {'message_id': 1027, 'from': {'id': 391834810, 'is_bot': False, 'first_name': 'Sergey', 'last_name': 'Bobkov',
# 'username': 'WillDrug', 'language_code': 'en-US'}, 'chat': {'id': 391834810, 'first_name': 'Sergey',
# 'last_name': 'Bobkov', 'username': 'WillDrug', 'type
# ': 'private'}, 'date': 1521465604, 'text': 'test'}
def accept_review(send_to, msg_id):
    return bot.sendMessage(send_to, f'Ready to submit! Choose if you want your username displayed:',
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                               InlineKeyboardButton(text='Submit', callback_data=f'submit_{msg_id}'),
                               #InlineKeyboardButton(text='Submit Anonymous', callback_data=f'hsubmit_{msg_id}'),
                               InlineKeyboardButton(text='Cancel', callback_data=f'cancel_{msg_id}')
                           ]])
                           )


def handle(msg):
    print(msg)
    flavour = flavor(msg)
    if flavour == 'chat':
        #short: (content_type, msg['chat']['type'], msg['chat']['id'])
        content_type, chat_type, chat_id = glance(msg)
        if chat_type == 'private':
            context = session.query(UserContext).filter(UserContext.id == chat_id).first()
            command = get_command(msg)[0]
            if context is None:
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
                session.commit()
            if command == '/reset':
                context.menu = 'main_menu'
                context.channel = None
                session.commit()
                msg['text'] = '/help'
            return route(msg, context)
        elif chat_type == 'channel':
            if content_type == 'text':
                return main_channel_menu(msg, chat_id)
            else:
                return True
        else:
            return True
    if flavour == 'callback_query':
        query_id, from_id, query_data = glance(msg, flavor='callback_query')
        choice, data = query_data.split('_')
        context = session.query(UserContext).filter(UserContext.id == from_id).first()
        if context is None:
            # WHAT?!
            return True
        if choice in ['choice', 'schoice', 'uchoice']:  # TODO: switch those blocks to another SPLIT
            ch = session.query(Channel).filter(Channel.id == data).first()
            if ch is None:
                return bot.sendMessage(from_id, 'That\' not something I manage... Weird')
            context.channel = ch.id
            context.menu = 'channel_menu'
            session.commit()
        if choice == 'choice':
            return bot.sendMessage(from_id, f'Okay, chosen!\nSend me something as a submission'
                                            f'Use /unmod if you are modding and tired of it\n'
                                            f'or /admin if you\'re an admin\n'
                                            f'/reset will get you back')
        elif choice == 'schoice':
            # already chosen channel. now do submitting
            # TODO: submission check
            msg = session.query(Message).filter().first()
            to_delete = accept_review(from_id, '@tofix') # TODO
            msg.current_request = f"{from_id};{to_delete['message_id']}"
            session.commit()
        elif choice == 'uchoice':
            mod = session.query(Mod).filter(Mod.id == from_id).filter(Mod.channel == data).first()
            if mod is None:
                return bot.sendMessage(from_id, 'You are not modding that...')
            else:
                user = mod.mod_name
                session.delete(mod)
                session.commit()
                bot.sendMessage(ch.owner, f'{user} is tired and is no longer a mod')
                return bot.sendMessage(from_id, 'Success! You are not submitting to {ch.name}\nUser /reset to go back')

        if choice in ['submit', 'cancel', 'approve', 'decline', 'ban']:
            msg = session.query(Message).filter(Message.id == data).first()
            if msg is None:
                return bot.answerCallbackQuery(query_id, text='You have already done that')
            else:
                cr_chat, cr_id = msg.current_request.split(';')
                bot.editMessageReplyMarkup((cr_chat, cr_id), InlineKeyboardMarkup(inline_keyboard=[[]]))
        if choice == 'submit':
            return submit_to_review(msg)

        elif choice == 'cancel':
            session.delete(msg)
            session.commit()
            return bot.sendMessage(from_id, 'As you wish')

        elif choice == 'approve':
            # TODO: info creator
            msg_channel = msg.channel
            msg_from_id = msg.from_id
            msg_message_id = msg.message_id
            session.delete(msg)
            session.commit()
            return bot.forwardMessage(msg_channel, msg_from_id, msg_message_id)

        elif choice == 'decline':
            chat_id = msg.from_id
            reply_to = msg.message_id
            session.delete(msg)
            session.commit()
            bot.sendMessage(msg.from_id, 'Your submission was declined. Sorry.', reply_to_message_id=reply_to)
            return bot.sendMessage(chat_id, 'Done!')

        elif choice == 'ban':
            ban = Banned(channel=msg.channel, user=msg.from_id, username=msg.from_username)
            session.add(ban)
            session.delete(msg)
            session.commit()
            bot.sendMessage(ban.user, 'You have been banned by a mod.\nYou can be unbanned only by the channel creator')
            return bot.sendMessage(from_id, 'Ban succesfull\nNote that only channel creator can unban!')
        else:
            return True  # TODO may be something?
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
        bot.answerInlineQuery(query_id, articles)
        return articles
    if flavour == 'chosen_inline_result':
        result_id, from_id, query_string = glance(msg, flavor='chosen_inline_result')
        channel, code = result_id.split('_')
        invite = Invite(invite_hash=code, channel=channel)
        session.add(invite)
        session.commit()
        return True

    if flavour == 'shipping_query':
        pass
    if flavour == 'pre_checkout_query':
        pass

def route(msg, context):
    if 'text' in msg:  # TODO: graceful handling
        if get_command(msg)[0] == '/start':
            context.menu = 'main_menu'
            session.commit()
    menus = {
        'main_menu': main_private_menu,
        'channel_menu': channel_private_menu,
        'admin_menu': admin_private_menu,
    }
    if context.menu in menus:
        return menus[context.menu](msg, context)
    else:
        return True


def submit_to_review(msg: Message):
    mod = session.query(Mod, func.count(Message.assigned_mod).label('total')).join(Message).group_by(Mod).order_by('total ASC').first()
    if mod is None:
        mod = session.query(Channel).filter(Channel.id == msg.channel).first()
        mod_id = mod.owner
    else:
        mod_id = mod.id
    to_delete = bot.sendMessage(mod_id, f'You have a message to review:', reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='Approve', callback_data=f'approve_{msg.id}'),
        InlineKeyboardButton(text='Decline', callback_data=f'decline_{msg.id}'),
        InlineKeyboardButton(text='Ban!', callback_data=f'ban_{msg.id}')
    ]]))
    msg.current_request = f"{mod_id};{to_delete['message_id']}"
    session.commit()
    return bot.forwardMessage(mod_id, msg.from_id, msg.message_id)



def admin_private_menu(msg, context):
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
            return bot.sendMessage(chat_id, response)
        elif command == '/unmod':
            mod = session.query(Mod).filter(Mod.channel == context.channel).filter(Mod.mod_name == data).first()
            if mod is None:
                return bot.sendMessage(chat_id, f'Moderator with {data} username not found.\n'
                                                f'See /modlist for more details')
            try:
                channel = session.query(Channel).filter(Channel.id == context.id).first()
                bot.sendMessage(mod.mod_id, f'You have been demoted for channel {channel.name} and will no longer be receiving messages to approve.')
            except TelegramError:
                pass
            except AttributeError:
                # What
                pass
            # reroute messages awaiting approval
            msgs = session.query(Message).filter(Message.assigned_mod == mod.mod_id).all()
            for msg in msgs:
                submit_to_review(msg)
            session.delete(mod)
            session.commit()
            return bot.sendMessage(chat_id, f'{data} is not a moderator anymore. Te-he-he!')
        elif command == '/mod':
            return bot.sendMessage(chat_id, 'Use this button and select a chat', reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text='Press and choose mod', switch_inline_query='true')
            ]]))
        elif command == '/banlist':
            response = 'Currently banned:'
            banlist = session.query(Banned).filter(Banned.channel == context.channel).all()
            for banned in banlist:
                response = response+'\n'+banned.username
            return bot.sendMessage(chat_id, response)
        elif command == '/unban':
            pass
        elif command == '/ban':
            pass
        elif command == '/unmanage':
            channel = session.query(Channel).filter(Channel.id == context.channel).first()
            return unmanage_channel(channel)
        else:
            bot.sendMessage(chat_id, f'That\'s not a proper command, though...\n'
                                     f'I don\'t submit those, either.')
    else:
        bot.sendMessage(chat_id, 'I\'m not ready to submit stuff to channel from admin menu. \n'
                                 'Use /reset and rejoin')


def channel_private_menu(msg, context):
    # presuming context.channel is set up
    content_type, chat_type, chat_id = glance(msg)
    ch = session.query(Channel).filter(Channel.id == context.channel).first()
    if content_type == 'text':
        command = get_command(msg)[0]
        if command == '/unmod':
            # TODO: confirm
            mod = session.query(Mod).filter(Mod.mod_id == context.id).filter(Mod.channel == context.channel).first()
            if mod is None:
                return bot.sendMessage(chat_id, 'You are not a mod, though.')
            session.delete(mod)
            session.commit()
            try:
                bot.sendMessage(ch.owner, f'{context.username} just unmodded himself :(')
            except TelegramError:
                pass  # TODO: inform demiurge
            return bot.sendMessage(chat_id, f'You will no longer see posts to approve from {ch.name}')
        elif command == '/admin':
            if context.id != ch.owner:
                return bot.sendMessage(chat_id, 'No you can\'t.')
            context.menu = 'admin_menu'
            session.commit()
            return bot.sendMessage(chat_id, help_message(menu='admin'))
    # everything else are submissions
    to_check = Message(from_id=chat_id, from_username=msg['from']['username'], message_id=msg['message_id'],
            channel=context.channel)
    session.add(to_check)
    session.commit()
    to_delete = accept_review(chat_id, to_check.id)
    to_check.current_request = f"{chat_id};{to_delete['message_id']}"
    session.commit()
    return True

def main_private_menu(msg, context):
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
                # TODO: check if mod is owner OR redo that owner always is a mod
                invite = session.query(Invite).filter(Invite.invite_hash == command_hash).first()
                if invite is None:
                    # TODO: add bullshit counter++
                    return bot.sendMessage(chat_id, 'You have no invite, you sly guy')
                channel = session.query(Channel).filter(Channel.id == invite.channel).first()
                if channel is None:
                    # TODO: alarm the demiurge
                    return bot.sendMessage(chat_id, 'I don\'t manage the channel you are invited to... weird')
                new_mod = Mod(channel=invite.channel, mod_id=chat_id, mod_name=msg['from']['username'])
                session.add(new_mod)
                session.commit()
                return bot.sendMessage(chat_id, f'You will be getting submits to {channel.name} for approval now!\n'
                                         f'To stop this, use /unmod command')
            # 2) someone got here from channel to submit -> set context to choose channel, goto submit menu
            elif option == 'submit':
                # TODO: reroute to submit menu from here
                pass
            # 3) Someone ran /manage on channel and we have to make sure we can send shit to him
            elif option == 'own':
                channels = session.query(Channel).filter(Channel.owner == chat_id).filter(Channel.pinned_id.is_(None)).all()
                for channel in channels:
                    if not manage_channel(channel):
                        bot.sendMessage(chat_id, f'Couldn\'t manage {channel.name}\n'
                                                 f'Make sure I\'m there and have privileges to pin and post')
                        bot.leaveChat(channel.id)  # lol
                        session.delete(channel)
                    else:
                        context.menu = 'admin_menu'
                        context.channel = channel.id
                session.commit()
                return bot.sendMessage(chat_id, help_message(menu='admin'))
            # 4) someone has no idea what are they doing at all
            else:
                return bot.sendMessage(chat_id, help_message())
        elif command == '/manage':
            return bot.sendMessage(chat_id, 'This command is used in channel only for now\n'
                                     'Run /choose to go into a channel or just send something as a submission and '
                                     'I\'ll prompt you')
        elif command == '/choose':  # Specific choose
            return choose_channel(chat_id)
        elif command == '/unmod':
            return choose_channel(chat_id, context='uchoice')
        elif command == '/help':
            return bot.sendMessage(chat_id, help_message())
    # everything else is submission (no-command text and not-text type
    elif content_type == 'sticker':
        return True  # can't submit stickers, thats bullshit
    # TODO: submission stuff
    return choose_channel(chat_id, context='schoice')  #

# channel comms
def main_channel_menu(msg, chat_id):
    # presuming CHAT - TEXT
    command = get_command(msg)[0]
    if command == '/manage':
        channel = session.query(Channel).filter(Channel.id == chat_id).first()
        if channel is not None:
            bot.sendMessage(channel.owner, 'I alerady manage that, silly!')
        admins = bot.getChatAdministrators(chat_id)
        owner = 0
        for admin in admins:
            if admin['status'] == 'creator':
                owner = admin['user']['id']
        if owner == 0:
            alert_demiurge(f'No owner for {chat_id}... what.')
        ch = Channel(id=chat_id, name=msg['chat']['title'], owner=owner)
        session.add(ch)
        session.commit()
        context = session.query(UserContext).filter(UserContext.id == owner).first()

        try:
            if context is not None:
                context.channel = chat_id
                context.menu = 'admin_menu'
                session.commit()
                bot.sendMessage(owner, help_message(menu='admin'))
                # chat with owner is opened, ok
                if not manage_channel(ch):
                    session.delete(ch)
                    session.commit()
                    bot.sendMessage(chat_id, 'Couldn\'t start managing the channel. \n'
                                                       'Make sure I can send and edit messages and re-run /manage')
            else:
                raise TelegramError('sneaky!', 0, '{}')
        except TelegramError:
            # no chat with owner. do basic stuff and wait for /own link \ command
            bot.sendMessage(chat_id, f"Ready to manage channel; Use this link and START button to confirm:\n"
                                     f"http://t.me/{bot.getMe().get('username')}?start=own_",)
    elif command == '/unmanage':
        channel = session.query(Channel).filter(Channel.id == chat_id).first()
        if channel is None:
            bot.sendMessage(chat_id, 'Yeah, I don\'t manage that.')
            return True  # TODO: differentiate between good and bad, update bullshit counter for user
        else:
            unmanage_channel(channel)  # TODO: confirmation button\personal msg
    else:
        return True


# generics
def choose_channel(chat_id, context='choice'):
    channels = session.query(Channel).filter(Channel.pinned_id.isnot(None)).all()
    if channels.__len__() == 0:
        return bot.sendMessage(chat_id, 'I don\'t seem to manage any channels right now. '
                                        'Add me as admin and write /manage in your channel to start!')
    keyboard = []
    for channel in channels:
        keyboard.append([
            InlineKeyboardButton(
                text=channel.name,
                callback_data=f"{context}_{channel.id}"
            )
        ])
    return bot.sendMessage(
        chat_id,
        'Choose a channel to submit to or manage:',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

def manage_channel(channel):
    channel_id = channel.id
    # 1) check admin rights
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
    # 2) send message
    message_to_pin = bot.sendMessage(
        channel_id,
        f"This channel is now managed by a bot!\n"
        f"If you want to submit something to this channel, message @{bot.getMe().get('username')} personally or just go here:\n"
        f"http://t.me/{bot.getMe().get('username')}?start=submit_",
        disable_web_page_preview=True,
        disable_notification=True,
    )
    # 3) pin message
    bot.pinChatMessage(channel_id, message_to_pin['message_id'], disable_notification=True)
    # 4) save structure
    channel.pinned_id = message_to_pin['message_id']
    session.commit()  # commit this.
    return True

def unmanage_channel(channel):
    bot.unpinChatMessage(channel.id)
    bot.sendMessage(channel.id, 'This channel is no longer managed by the bot')
    bot.leaveChat(channel.id)
    session.delete(channel)
    session.commit()

def alert_demiurge(message):
    bot.sendMessage(demiurge, message)
# UTILITY

def help_message(menu='main'):
    if menu == 'admin':
        return f'Admin menu. Commands:\n' \
               f'/modlist : Displays current channel moderators\n' \
               f'/unmod : Strip someone\'s mod privileges.\n' \
               f'/mod : Shows a useful button to ask someone to be a mod!' \
               f'/banlist : Current banlist (sets up by mod request !!UNIMPLEMENTED!!: or after ' \
               f'{bullshit_threshhold} bullshit messages)\n' \
               f'/unban <username> : Unban some user by username\n' \
               f'/ban <username> : Ban some user by username\n' \
               f'/unmanage : Unmanages this channel. !!!UNIMPLEMENTED!!!: Requires additional acceptance'
    else:
        return 'Main menu commands:\n' \
               '/unmod : will prompt you to choose a channel to stop being a mod on\n' \
               '/choose : will prompt you to choose a channel and help with menus there\n' \
               '/reset will always get you back here\n' \
               'Anything else will be treated as a submission and you will be prompted to choose a channel to submit to.'

def get_command(msg):
    if 'entities' not in msg:
        return '', msg['text']
    command = ''
    the_rest = msg['text']
    for ent in msg['entities']:
        if ent['type'] == 'bot_command':
            command = msg['text'][ent['offset']:ent['length']]
            the_rest = msg['text'][int(ent['offset'])+int(ent['length']):]
    botname = command.find('@')
    if botname > -1:
        command = command[:botname]
    return command, the_rest.strip()


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
"""