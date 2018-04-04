# Channel Manager Bot
# Introduction
This is a poorly constructed bot, which enables submissions in telegram channels.
Right now it's running on a pythonanywhere web setup [here](http://t.me/chmgr_bot).

This bot is developed under AGPU license. For more details, consult [LICENSE](LICENSE) file.

# Changelog
## v1.1
Bot reworked with a flat structure in mind. The only state the bot keeps is the currently selected channel, which can be changed in most prompts or be reset with `/cancel`.

Consult reworked [commands](#commands-list) section for more details.
## v1.0
Bot released with current documentation.

# Feature Creep
## Planned Features
- [ ] Shadowban
- [ ] Anonymous submitting
- [ ] Full message copying not just for anonymity but to show buttons under submission.
- [ ] Verbosity switch for admin
- [x] ~~Flat structure~~ done in v1.1

## Requested Features
Nothing! Be the first one to [request something](https://github.com/WillDrug/channel_manager_bot/issues)!

# Functionality
This bot includes the following features:
## Turning On
For the bot to work you need to:
 1) Message the bot once. This will make the rest of the process less complicated.
 2) Add it to the channel you created as an admin with _edit_ and _post_ privileges
 3) Run `/manage` command.
 4) Only _channel creator_ will be messaged and can admin the channel.

 The bot will try to send you something. If it succeedes, it will post and pin a message to the channel, telling people that it's now moderated and how to submit.

## Submitting
Posting into a channel can be done in several ways:
1) Follow a link from pinned channel message and then send something.
2) Send something to the bot and then choose a channel to post to.
3) Bot remembers the last channel you posted to, so if a channel is selected it will prompt you to submit right away.

_*IMPORTANT*_: Stickers and bot commands are not something you can submit. Because.

## Moderating
If a channel doesn't have mods the post will go to the creator for approval.

If the creator is unavailble bot will *freak out and just leave the channel alltogether*.

1) To let someone moderate you need to write `@chmgr_bot` in any private chat and choose a channel from a drop-down menu.
2) Alternatevily, you may run `/mod` command. If you have any channel you're admining -- you'll be given a button, which will prompt you to choose a chat on press.

Funny enough, this is just a very complicated way to use method 1.

**Telegram caches inline results!** Cache time can't be set too low or bot's potato server might explode. `/mod` command has a perk that it generates a unique GUID so telegram is fooled.

Any mod can stop being a mod with `/unmod` command. Admin can also unmod anyone with the same command.
Both options include mutual notifications.

## Ban lists
Any moderator can ban someone. Their options are always `approve`, `decline`, `ban`.

However, moderators cannot ban other moderators or the channel creator. This was included because the poor bot doesn't want to be sweeped into all the drama. If you have issues -- `/unmod`.

Admin also has `/banlist` command and `/unban` command, which are used to see currently banned usernames and unbanning someone. Both commands will prompt for a channel if none is selected. Details in the [commands list](#commands-list)


## Bullshit counter
The bot implements the **Bullshit Counter** (patent pending) functionality.

When a user submits a certain number of useless requests, which are not commands nor submissions he is ignored for 24 hours all-together.

Each useful request halves the meter

## Commands List
All commands prompt channel if none selected or if fucntion is not permitted for current channel.
* `/help`: Display help
* `/modlist`: ADMIN: Displays list of mods
* `/unmod`: USER: Unmod yourself from a channel; ADMIN: choose a person to unmod
* `/banlist`: ADMIN: Displays a list of banned users
* `/unban`: ADMIN: Prompts to unban a user
* `/cancel`: Resets current prompt and channel
* `/poke`: USER: Reminds mods about your submission or re-sends to another; ADMIN: Pokes all mods
* `/mod`: Useful button to invite mods
* `/unmanage`: ADMIN: Bot leaves channel. All is deleted.
* `/manage`: FROM CHANNEL: Start managing a channel

<right><sub>you can [buy me a coffee](https://www.paypal.me/willdrug) if you like this</sub></right>