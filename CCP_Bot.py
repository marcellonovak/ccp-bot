import discord
from discord.ext import commands
import math
import random
import datetime

intents = discord.Intents.default()
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix='$', intents=discord.Intents.all())

# Channel IDs
general_channel_id = 704783171035856987
count_channel_id = 1049363506069245952
quote_channel_id = 805579879038058516

# Dictionary to store user strikes
user_strikes = {}

# List of wisdom
wisdom_list = []

# Command channel whitelists
allowed_channels = ['general', 'memes', 'spam', 'bot-commands', 'server-suggestions', 'sportsball']


# Login message
@bot.event
async def on_ready():
    # Wipe log file
    with open('ccp-log-file.txt', "w") as log_file:
        log_file.write("")

    # Send welcome message and log startup
    await bot.get_channel(general_channel_id).send("你好! I'm back online!")
    loginfo("Startup/INFO", "Logged in as " + bot.user.name + " (" + str(bot.user.id) + ")")

    # Load wisdom and log load success
    # Todo: Add error message if wisdom file is not found?
    with open('confucius.txt', 'r') as confucius_file:
        global wisdom_list
        wisdom_list = confucius_file.readlines()
    loginfo("Startup/INFO", f'Wisdom loaded: {len(wisdom_list)} lines')


# Log to file function
def loginfo(prefix, message) -> None:
    with open('ccp-log-file.txt', 'a') as logging_file:
        current_time = datetime.datetime.now().strftime("%y/%m/%d][%H:%M:%S")
        logging_file.write(f'[{current_time}][{prefix.ljust(26)}]: {message}\n')


# When messages are sent
@bot.event
async def on_message(message):
    # Ignore initial messages from bots
    if message.author.bot:
        return

    # If message is in the learn-to-count channel
    if message.channel.name == 'learn-to-count':

        # Look for the previous human message
        last_human_message = await findLastHumanMessage(message.channel)

        # Log all relevant info
        loginfo("Counting Message/INFO", f'Current Message Received: '
                                         f'{message.author} {message.content}')
        loginfo("Counting Message/INFO", f'Previous Message Found: '
                                         f'{last_human_message.author} {last_human_message.content}')

        # Try floating found message
        loginfo("Checking Message/INFO", f'Floating "{message.content}"...')
        try:
            float(message.content)
        # Strike is failure detected (non-number)
        except ValueError:
            await message.delete()
            await giveStrike(message, "This channel is for numbers only",
                             "Checking Message/STRIKE", f"{message.author} sent a non-number message: "
                                                        f"Struck Message: {message.content}")
            return
        # Log success if numeric
        else:
            loginfo("Checking Message/INFO", f'Floating successful')

        # Detect repetitive messaging, strike if detected
        if last_human_message.author == message.author:
            await message.delete()
            await giveStrike(message, "Only one person can count at a time",
                             "Checking Message/STRIKE", f"{message.author} counted repetitively: "
                                                        f"Struck Message: {message.content}")
            return

        # Double check if both messages are numeric (redundant?)
        if isinstance(float(last_human_message.content), float) and isinstance(float(message.content), float):

            # If [current count < last count] or [(last count + 1) < current count]
            if (float(message.content) < (float(last_human_message.content))) or \
                    (float(message.content)) > (math.floor(float(last_human_message.content)) + 1.0):
                # Delete offending message, strike for incorrect counting
                await message.delete()
                await giveStrike(message, "You can't count",
                                 "Checking Message/STRIKE", f"{message.author} counted incorrectly: "
                                                            f"Struck Message: {message.content}")
                return
            elif message.content.startswith('0'):
                # Delete messages that start with 0
                await message.delete()
                await giveStrike(message, "Don't fucking start your messages with 0 you cunt",
                                 "Checking Message/STRIKE", f"{message.author} padded their count: "
                                                            f"Struck Message: {message.content}")
                return

    # Let the bot think
    await bot.process_commands(message)


# Function to recursively find the last human message in a channel
async def findLastHumanMessage(channel) -> discord.Message:
    loginfo("Finding Human Message/INFO", f'Looking for last human message in {channel.name}...')
    loginfo("Finding Human Message/INFO", f'Last recorded message: '
                                          f'{channel.last_message.author} {channel.last_message.content}')

    async for message in channel.history(limit=None, oldest_first=False):

        # Skip bot messages and the current message
        if (message == channel.last_message) or message.author.bot:
            continue

        # Hit something that isn't a bot message
        loginfo("Finding Human Message/INFO", f'Found human message: {message.author} {message.content}')
        return message


# Function to give a user a strike
async def giveStrike(message, strike_output,
                     log_strike_prefix, log_strike_message) -> None:
    struck_user = message.author

    # Console log when a strike is given
    loginfo(log_strike_prefix, log_strike_message)

    # Add strike to user
    user_strikes.setdefault(struck_user.id, {'strikes': 0})['strikes'] += 1

    # Mention the user
    await bot.get_channel(count_channel_id).send(
        f"Strike {user_strikes[struck_user.id]['strikes']}, {strike_output} {struck_user.mention}")

    # Grant the stupid role for dumb users
    if int(user_strikes[struck_user.id]['strikes']) >= 5:
        # Log user going over strike limit
        loginfo('Moderation/INFO', f'Exiling {struck_user} for going over the strike limit')

        # Restricted Role
        role = discord.utils.get(struck_user.guild.roles, name="Faggot")

        # Add role and mention user
        await struck_user.add_roles(role)
        await bot.get_channel(count_channel_id).send(
            f'Get sent to sped class {struck_user.mention}, appeal to the discord mod for mercy.')


# Function to check perms
async def checkPerms(ctx, role_needed, command_tried):
    checked_role = discord.utils.get(ctx.guild.roles, name=role_needed)  # Get the role object to check
    command_author = ctx.author  # Get who called the command

    # If perms not valid:
    if checked_role is False:
        # If user does not have perms, give an error in chat
        await ctx.send(f'{command_author.mention}, you do not have permission to use {command_tried}')
        # Log the attempt, and the command tried
        loginfo('Moderation/INFO', f'{command_author} tried using {command_tried} without perms')

    return checked_role in ctx.author.roles


@bot.command()  # $strikes command
async def strikes(ctx, user: discord.Member = commands.parameter(default=None,
                                                                 description=": User to check strikes of")):
    """
    Check how many strikes you have
    Usage: $strikes
    """

    # Only allow command in allowed channels
    if ctx.channel.name not in allowed_channels:
        return

    # User we're checking the strikes of
    checked_user = user or ctx.author

    # Check strikes
    if checked_user.id not in user_strikes:
        checked_user_strikes = 0
    else:
        checked_user_strikes = user_strikes[checked_user.id]['strikes']

    # Send strikes message
    await ctx.send(f"{checked_user.mention}: You have {checked_user_strikes} strikes.")


@bot.command()  # $pardon command
async def pardon(ctx, user: discord.Member = commands.parameter(default=None,
                                                                description=": User to pardon")) -> None:
    """
    Pardon a user, resetting their strikes to 0
    Usage: $pardon @(user)
    """

    # Only allow command in allowed channels (yes, even for me)
    if ctx.channel.name not in allowed_channels:
        return

    command_author = ctx.author  # Get who called the command

    if await checkPerms(ctx, 'Admin', '$pardon'):  # Check if user has perms, returns true

        if user is None:  # If command is called without mentioning a user
            await ctx.send(f'{command_author.mention}, please mention a user to pardon.')
            # Log the error
            loginfo('Moderation/ERROR', f'{command_author} tried pardoning without mentioning a user')
            return

        if user.bot:  # If command is called on a bot
            await ctx.send('Bots do not have strikes and cannot be pardoned.')
            # Log the error
            loginfo('Moderation/ERROR', f'{command_author} tried pardoning a bot')
            return

        else:  # Pardon if valid command is passed
            # Get role
            stupid_role = discord.utils.get(user.guild.roles, name="Faggot")

            # Pardon user
            await ctx.send(f'{user.mention} has been pardoned. Strikes have been reset.')
            user_strikes.setdefault(user.id, {'strikes': 0})['strikes'] = 0
            if stupid_role in user.roles:
                await user.remove_roles(stupid_role)

            # Log the pardon
            loginfo('Moderation/INFO', f'{command_author} successfully pardoned {user}')


@bot.command()  # whack command
async def whack(ctx, user: discord.Member = commands.parameter(default=None,
                                                               description=": User to whack")) -> None:
    """
    Whack a user, settings their strikes to 999
    Usage: $whack @(user)
    """

    # Only allow command in allowed channels (yes, even for me)
    if ctx.channel.name not in allowed_channels:
        return

    command_author = ctx.author  # Get who called the command

    if await checkPerms(ctx, 'Admin', '$whack'):  # Check if user has perms, returns true

        if user is None:  # If command is called without mentioning a user
            await ctx.send(f'{command_author.mention}, please mention a user to whack.')
            # Log the error
            loginfo('Moderation/ERROR', f'{command_author} tried whacking without mentioning a user')
            return

        if user.bot:  # If command is called on a bot
            await ctx.send('Bots do not have strikes, cannot be whacked.')
            # Log the error
            loginfo('Moderation/ERROR', f'{command_author} tried whacking a bot')
            return

        else:  # Whack if valid command is passed
            # Get role
            stupid_role = discord.utils.get(user.guild.roles, name="Faggot")

            # Whack user
            await ctx.send(f'{user.mention} has been whacked. Strikes have been set to 999.')
            user_strikes.setdefault(user.id, {'strikes': 0})['strikes'] = 999
            if stupid_role not in user.roles:
                await user.add_roles(stupid_role)
            await ctx.send(f'Get sent to sped class {user.mention}, appeal to the discord mod for mercy.')

            # Log the whack
            loginfo('Moderation/INFO', f'{command_author} successfully whacked {user}')


@bot.command()  # $quote command
async def quote(ctx: commands.Context, text=commands.parameter(default=None,
                                                               description=": Replied message to quote")) -> None:
    """
    Automatically quote a user's message
    Usage: $quote (when replying to a message)
    """

    # Only allow command in allowed channels
    if ctx.channel.name not in allowed_channels:
        return

    # The snitch!
    command_author = ctx.author

    if text is None:
        try:
            quoted_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        except AttributeError:
            await ctx.reply("You need to reply to a message to use this command!")
            # Log the error
            loginfo('Quote/ERROR', f'{command_author} tried quoting without replying to a message')

        # If quoted message is in fact a message
        else:
            timestamp = quoted_message.created_at.strftime("%m/%d/%Y %H:%M:%S")  # Get the time down to the second
            quote_author = quoted_message.author  # Get the author of the quote
            content = quoted_message.content  # Get what the quote actually is

            # Send the full quote in format:
            # "Quote Content"
            # [Author] @ 00:00:00:00
            # Quoted by [Snitch]
            await bot.get_channel(quote_channel_id).send(
                f'"{content}"\n'
                f'[{quote_author.mention}] said this at [{timestamp}]\n'
                f'Quoted by [{command_author.mention}]')

            # Log the successful quote
            loginfo('Quote/INFO', f'{command_author} successfully quoted {quote_author}')


@bot.command()  # $wisdom command
async def wisdom(ctx) -> None:
    """
    Prints out a wise saying
    Usage: $wisdom
    """

    # Only allow command in allowed channels
    if ctx.channel.name not in allowed_channels:
        return

    selected_wisdom = random.choice(wisdom_list)
    seeker = ctx.author
    await ctx.send(f"{seeker.mention} Confucius say: {selected_wisdom}")
    
# Run the thingy
with open('bot-token.txt', 'r') as bot_token_file:
    bot_token = bot_token_file.readline().strip()
    bot.run(bot_token)

'''
Issues
- why don't emojis work (for quotes)
- delete wrong $quote messages
- delete captain fucking hook

Changelog
- Added flooring to the order check
- Added automatic role adding when a strike limit is reached
- math.floor the messages for checking
- auto-grant the stupid role to illiterates
3/26:
- changed the bot message checking to be recursive
- if a previous bot message is found, delete it
- return last human message function created
- prettied up the quote function
- added $wisdom
3/27:
- added $pardon command
- added $whack command
3/29:
- Created a logging function, working on logging to a file
3/30:
- Load bot token from a file
???:
- Created an FTP server on debian with vsftpd
- Transferred the files over with filezilla
- Started the python process headless
- Since the token is loaded from a file, can post the bot code from github easy
- Able to update the bot using github
4/10:
- Created a new strike for padded messages
- Added some better comments
4/12:
- Made perm-checking a function
- Added help functionality, and argument descriptions

todo
- add random roast messages for strikes
- unfunny strikes to restrict quote access
- add image quoting
- figure out where to host the text files (SQL?)
- Maybe define the channel IDs in a file too?
- Make messages uneditable somehow?
- Make a taiwan to china converter
- Make a $wipe command, admin only
- Make categories for commands
'''
