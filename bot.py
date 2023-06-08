import sqlite3
import discord
from discord.ext import commands, tasks
import logging
from colorlog import ColoredFormatter

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

log = logging.getLogger('my-discord-bot')
stream = logging.StreamHandler()

stream.setFormatter(ColoredFormatter("%(reset)s%(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(message)s"))
log.addHandler(stream)

log.setLevel("INFO")

client = commands.Bot(intents=intents, command_prefix="!")

# Checking if database exists, if not, create it
con = sqlite3.connect('./data/database.db')
cur = con.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guilds'")
if cur.fetchone() is None:
    cur.execute(
        """
        CREATE TABLE guilds (
            guild_id INTEGER,
            l_enabled BOOLEAN DEFAULT TRUE,
            w_enabled BOOLEAN DEFAULT TRUE,
            w_s INTEGER DEFAULT 0,
            l_s INTEGER DEFAULT 0,
            
            PRIMARY KEY (guild_id)
        )
        """
    )

w_guilds = []
l_guilds = []

l_counter = {}
w_counter = {}


# Bot begins here

@client.event
async def on_ready():
    log.info(f"Logged in as {client.user.name}#{client.user.discriminator} ({client.user.id})")
    log.info(f"Connected to {len(client.guilds)} guilds")
    log.info(f"Connected to {len(client.users)} users")

    db_sync.start()


@client.event
async def on_guild_join(guild):
    cur.execute("INSERT INTO guilds (guild_id) VALUES (?)", (guild.id,))
    con.commit()

    log.info(f"Joined guild {guild.name} ({guild.id})")


@client.event
async def on_guild_remove(guild):
    cur.execute("DELETE FROM guilds WHERE guild_id = ?", (guild.id,))
    con.commit()

    log.info(f"Left guild {guild.name} ({guild.id})")


@client.command()
async def sync(ctx):
    if ctx.user.id != 123:
        return
    await client.tree.sync()


@client.event
async def on_message(message):
    if message.author.bot:
        return

    if message.guild.id not in w_guilds or message.guild.id not in l_guilds:
        return

    if " L " in f" {message.content.upper()} ":
        l_counter[message.guild.id] += 1
        action = "L"
    elif " W " in f" {message.content.upper()} ":
        w_counter[message.guild.id] += 1
        action = "W"
    else:
        return

    count = l_counter[message.guild.id] if " L " in f" {message.content.upper()} " else w_counter[message.guild.id]

    match str(count)[-1]:
        case 1:
            suffix = "st"
        case 2:
            suffix = "nd"
        case 3:
            suffix = "rd"
        case _:
            suffix = "th"

    try:
        await message.reply(f"This is the {count}{suffix} {action}")
    except discord.errors.Forbidden:
        log.warning(f"Missing permissions to send message in {message.guild.name} ({message.guild.id})")
    except discord.errors.HTTPException:    # Rate limited
        log.warning(f"Rate limited in {message.guild.name} ({message.guild.id})")
    log.debug(f"Sent {count}{suffix} {action} in {message.guild.name} ({message.guild.id})")

    await client.process_commands(message)


@tasks.loop(seconds=60)
async def db_sync():
    global w_guilds, l_guilds
    l_guilds = [i[0] for i in cur.execute("SELECT guild_id FROM guilds WHERE l_enabled = TRUE").fetchall()]
    w_guilds = [i[0] for i in cur.execute("SELECT guild_id FROM guilds WHERE w_enabled = TRUE").fetchall()]

    log.debug(f"Synced guilds: {w_guilds}, {l_guilds}")

    global l_counter, w_counter

    # Don't worry, when the bot starts, the dict will be empty so no changes will be made
    # put values of l_counter and w_counter into database
    for guild in l_counter:
        cur.execute("UPDATE guilds SET l_s = ? WHERE guild_id = ?", (l_counter[guild], guild))
    for guild in w_counter:
        cur.execute("UPDATE guilds SET w_s = ? WHERE guild_id = ?", (w_counter[guild], guild))

    con.commit()

    l_counter = {i[0]: i[1] for i in cur.execute("SELECT guild_id, l_s FROM guilds").fetchall()}
    w_counter = {i[0]: i[1] for i in cur.execute("SELECT guild_id, w_s FROM guilds").fetchall()}


client.run("MTExNDkyNjc3NTQ1NDE0NjU2MQ.GMgKlq.28gqGF9J-FCNgi8uI-tQBP2JyfomlOXxDPatZ0")
