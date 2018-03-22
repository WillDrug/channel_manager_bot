import os
from telepot import Bot, glance, flavor
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
    if 'text' in msg:  # TODO: graceful handling
        if get_command(msg['text']) == '/start':
            menu = 'main_menu'
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
                command, option, command_hash = msg['text'].split(';')
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
                channels = session.query(Channel).filter(Channel.owner == chat_id).filter(Channel.pinned_id is None).all()
                for channel in channels:
                    if not manage_channel(channel):
                        bot.sendMessage(chat_id, f'Couldn\'t manage {channel.name}\n'
                                                 f'Make sure I\'m there and have privileges to pin and post')
                        session.delete(channel)
                        session.commit()
            # 4) someone has no idea what are they doing at all
            else:
                return bot.sendMessage(chat_id, help_message(),
                                reply_markup=[])  # TODO: reply buttons
        elif command == '/manage':
            bot.sendMessage(chat_id, 'This command is used in channel only')
            pass

        # 3) everything else is used as submission material -> then we ask for a channel
    else:
        return bot.sendMessage(chat_id, help_message())

# UTILITY
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
        f"This channel is now managed by me!\n"
        f"If you want to submit something to this channel, message me personally or just go here:\n"
        f"http://t.me/{bot.getMe().get('username')}?start=submit;",
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
    mods = session.query(Mod).filter(Mod.channel == channel.id).all()
    for mod in mods:
        session.delete(mod)
    session.query(Banned)
    session.query(Invite)
    session.query(Message)
    session.commit()

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