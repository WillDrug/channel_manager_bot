from bot import bot, handle
from telepot.loop import MessageLoop
from telepot import flavor, glance
def rehandle(msg):
    flavour = flavor(msg)
    if flavour == 'chat':
        content_type, chat_type, chat_id = glance(msg, flavour)
        if chat_type == 'private':
            return handle({'message': msg})
        elif chat_type == 'channel':
            return handle({'channel_post': msg})
    else:
        return handle({flavour: msg})

MessageLoop(bot, rehandle).run_as_thread()

while True:
    try:
        pass
    except KeyboardInterrupt:
        break