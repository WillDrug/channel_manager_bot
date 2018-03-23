import os
from telepot import Bot, glance, flavor
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, InlineQuery, InlineQueryResultArticle, ChosenInlineResult, InputTextMessageContent
from telepot.exception import TelegramError
from model import Channel, UserContext, Invite, Mod, Banned, Message, session
from config import config

demiurge = 123  # TODO: add maintainer chat id

token = os.environ.get('SECRET')

bot = Bot(token)
bot.deleteWebhook()

# {'message_id': 1027, 'from': {'id': 391834810, 'is_bot': False, 'first_name': 'Sergey', 'last_name': 'Bobkov',
# 'username': 'WillDrug', 'language_code': 'en-US'}, 'chat': {'id': 391834810, 'first_name': 'Sergey',
# 'last_name': 'Bobkov', 'username': 'WillDrug', 'type
# ': 'private'}, 'date': 1521465604, 'text': 'test'}
def handle(msg):
    print(msg)
    flavour = flavor(msg)
    if flavour == 'chat':
        #short: (content_type, msg['chat']['type'], msg['chat']['id'])
        content_type, chat_type, chat_id = glance(msg)
        if chat_type == 'private':
            # TODO: reset command
            context = session.query(UserContext).filter(UserContext.id == chat_id).first()
            if context is None:
                bot.sendMessage(chat_id,
                                'Hello! I am Channel Manager Bot!\n'
                                'Please pardon the lag, my server is made of potatoes and is free.')
                context = UserContext(id=chat_id, username=msg['from']['username'], menu='main_menu')
                session.add(context)
                session.commit()
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
        choice, data = query_data.split('$')
        context = session.query(UserContext).filter(UserContext.id == from_id).first()
        if context is None:
            # WHAT?!
            return True
        if choice in ['choice', 'submit']:
            ch = session.query(Channel).filter(Channel.id == data).first()
            if ch is None:
                return bot.sendMessage(from_id, 'That\' not something I manage... Weird')
            context.channel = ch
            context.menu = 'channel_menu'
            session.commit()
            if choice == 'submit':
                return True  # TODO: submission checks
            else:  # TODO send commands only if applicable
                return bot.sendMessage(from_id, f'Okay, chosen$\nSend me something as a submission'
                                                f'Use /unmod if you\'re a mode or /admin if you\'re an admin')
    if flavour == 'inline_query':
        query_id, from_id, query_string = telepot.glance(msg, flavor='inline_query')
        channels = session.query(Channel).filter(Channel.owner == from_id).all()
        articles = []
        for channel in channels:
            invite = session.query(Invite).filter(Invite.channel == channel) # TODO: DO
            articles.append(
                InlineQueryResultArticle(
                    id=channel.id,
                    title=channel.name,
                    input_message_content=InputTextMessageContent(
                        message_text=f'You are invited to be a mod in {channel.name}\n'
                                     f'If you agree, follow the link below and press start\n'
                                     f'http://t.me/{bot.getMe().get("username")}/?start=mod$',
                        disable_web_page_preview=True
                    )
                )
            )

        pass
    if flavour == 'chosen_inline_result':
        pass
    if flavour == 'shipping_query':
        pass
    if flavour == 'pre_checkout_query':
        pass

def route(msg, context):
    if 'text' in msg:  # TODO: graceful handling
        if get_command(msg['text']) == '/start':
            context.menu = 'main_menu'
            session.commit()
    menus = {
        'main_menu': main_private_menu,
        'channel_menu': channel_private_menu,
    }
    if context.menu in menus:
        return menus[context.menu](msg, context)
    else:
        return True

def channel_private_menu(msg, context):
    # presuming context.channel is set up
    content_type, chat_type, chat_id = glance(msg)
    ch = session.query(Channel).filter(Channel.id == context.channel).first()
    if content_type == 'text':
        command = get_command(msg['text'])
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
            return bot.sendMessage(chat_id, f'some shit here') # TODO: admin menu help
    # everything else are submissions
    # TODO: handle submissions

def main_private_menu(msg, context):
    # presuming msg is CHAT
    content_type, chat_type, chat_id = glance(msg)
    # 1) send  basic menu info
    # REDONE to not be obnoxious
    # 2) If that's main menu we have no channel$ Text is treated as a command
    if content_type == 'text':
        command = get_command(msg['text'])
        if command == '/start':  # TODO: fix shitty start
            try:
                command, option, command_hash = msg['text'].split('$')
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
                new_mod = Mod(channel=invite.channel, mod_id=chat_id)
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
                        session.commit()
                return True
            # 4) someone has no idea what are they doing at all
            else:
                return bot.sendMessage(chat_id, help_message())
        elif command == '/manage':
            return bot.sendMessage(chat_id, 'This command is used in channel only for now\n'
                                     'Run /choose to go into a channel or just send something as a submission and '
                                     'I\'ll prompt you')
        elif command == '/choose':  # Specific choose
            return choose_channel(chat_id)
    # everything else is submission (no-command text and not-text type
    elif content_type == 'sticker':
        return True  # can't submit stickers, thats bullshit
    # TODO: submission stuff
    return choose_channel(chat_id, context='submit')

# channel comms
def main_channel_menu(msg, chat_id):
    # presuming CHAT - TEXT
    command = get_command(msg['text'])
    if command == '/manage':
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
        try:
            bot.sendMessage(owner, 'Hello!')
            # chat with owner is opened, ok
            if not manage_channel(ch):
                session.delete(ch)
                session.commit()
                bot.sendMessage(msg['from']['id'], 'Couldn\'t start managing the channel. \n'
                                                   'Make sure I can send and edit messages and re-run /manage')
        except TelegramError:
            # no chat with owner. do basic stuff and wait for /own link \ command
            bot.sendMessage(chat_id, f"Ready to manage channel$ Use this link and START button to confirm:\n"
                                     f"http://t.me/{bot.getMe().get('username')}?start=$own$",)
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
                callback_data=f"{context}${channel.id}"
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
        f"http://t.me/{bot.getMe().get('username')}?start=$submit$1",
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

def help_message():
    return 'THIS IS HELP'

def get_command(text):
    if text[0] != '/':
        return ''
    botname = text.find('@')
    cmd_end = text.find(' ')
    if botname == -1 and cmd_end == -1:
        return text
    elif cmd_end > -1 and botname == -1:
        return text[:cmd_end]
    else:
        return text[:botname]

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