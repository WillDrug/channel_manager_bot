# Channel Manager Bot
# Introduction
This is a poorly constructed bot, which enables submissions in telegram channels.
Right now it's running on a pythonanywhere web setup [here](http://t.me/@tofix).

This bot is developed under AGPU license. For more details, consult `LICENSE`

# Changelog
## v1.0
Bot released with current documentation.

# Feature Creep
## Planned Features
1) Shadowban
2) Anonymous submitting
3) Full message copying not just for anonymity but to show buttons under submission.
4) Verbosity switch for admin
5) Flat structure, getting rid of menus altogether

## Requested Features

# Functionality
This bot includes
## Enabling
For the bot to work you need to:
 1) add it to your channel as an admin with edit and post privileges
 2) Then run `/manage` command.
 3) _Channel creator_ and only him will be messaged.

 The bot will try to send you something.
 If it succeedes it will send you into an admin menu and then send and pin a message into the channel, telling people
 where to post.
## Submitting
Posting into a channel can be done in several ways:
1) Follow a link from pinned channel message and then send something
2) Run `/choose` command and then send something
3) Just send something and then you'll be prompted to choose a channel.

_*IMPORTANT*_: Stickers and bot commands are not something you can submit. Because.

## Moderating
If a channel doesn't have mods the post will go to the creator for approval.

If the creator is unavailble bot will freak out and just leave the channel alltogether.

1) To let someone moderate you need to write `@tofix` in any private chat and choose a channel from a drop-down menu.
2) Alternatevily, you may run `/mod` command from `/admin` menu.
You'll be given a button, which will prompt you to choose a chat on press.
Funny enough, this is just a very complicated way to use method 1.

**Telegram caches inline results!** `/mod` command has a perk that it generates a unique GUID so telegram is fooled.

Any mod can stop being a mod with `/unmod` command. Admin can also unmod anyone from `/admin` menu.
Both options include mutual notifications.

## Ban lists
Any moderator can ban someone. Their options are always `approve`, `decline`, `ban`.

Channel creator can use `/ban <username>` command to ban someone pre-emptively. However, that only works for people who wrote to the bot at least once.

Admin also has `/banlist` command and `/unban <username>` command from the `/admin` menu.

## Bullshit counter
The bot implements the BULLSHIT COUNTER functionality.

When a user submits a certain number of useless requests, which are not commands nor submissions he is ignored for 24 hours all-together.

Each useful request halves the meter

## Commands List
/start - Works with deep links and switches you to a proper menu

/reset - Goes to root menu from anywhere

/list - List channels you're modding

/choose - Prompts you to choose a channel. Persists

/unmod - Stop yourself from being a mod. Works from root and channel menus

/admin - Go to admin menu. Works from root and channel menus.

/help - Help with current menu

/modlist - !ADMIN ONLY! - Lists moderators

/unmod  - !ADMIN ONLY! - Strip someone's mod privileges

/mod - !ADMIN ONLY! - Shows a useful button to ask someone to be a mod!

/banlist - !ADMIN ONLY! - Current banlist

/unban <username> - !ADMIN ONLY! - Unban some user by username
 
/ban <username> - !ADMIN ONLY! - Ban some user by username (only if user has spoken to a bot at least once)
 
/unmanage - !ADMIN ONLY! - Unmanages your channel. WORKS INSTANTLY! CAREFUL!
