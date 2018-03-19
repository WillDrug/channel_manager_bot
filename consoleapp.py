from bot import bot, handle
from telepot.loop import MessageLoop

MessageLoop(bot, handle).run_as_thread()
while True:
    try:
        pass
    except KeyboardInterrupt:
        break