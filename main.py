import asyncio
import logging
import os
import sys
import traceback

import discord
import dotenv
from discord.ext import commands

import aoi

try:
    os.chdir(os.path.dirname(sys.argv[0]))
except FileNotFoundError:
    pass

logging.addLevelName(7, "TRACE")

dotenv.load_dotenv(".env")


def get_prefix(_bot: aoi.AoiBot, message: discord.Message):
    if not message.guild:
        return commands.when_mentioned_or(",")(_bot, message)
    if message.guild.id not in _bot.db.prefixes:
        asyncio.create_task(_bot.db.guild_setting(message.guild.id))
        return commands.when_mentioned_or(",")(_bot, message)
    return commands.when_mentioned_or(_bot.db.prefixes[message.guild.id])(_bot, message)


bot = aoi.AoiBot(command_prefix=get_prefix, help_command=None, intents=discord.Intents.all(), fetch_offline_users=True)

bot.load_extensions()


@bot.check
async def permission_check(ctx: aoi.AoiContext):  # noqa: C901
    if not ctx.guild:
        return True
    can_use = True
    current_n = 0

    def update_use(can: bool, _n: int):
        nonlocal current_n
        nonlocal can_use
        can_use = can
        if not can:
            current_n = _n

    if ctx.command.name == 'help':
        return True

    if ctx.command.cog.qualified_name == "Permissions":
        return True
    perms = await bot.db.get_permissions(ctx.guild.id)
    for n, i in enumerate(perms):
        tok = i.split()
        if tok[0] == "asm":
            update_use(tok[1] == "enable", n)
        if tok[0] == "acm":
            if ctx.channel.id == int(tok[1]):
                update_use(tok[2] == "enable", n)
        if tok[0] == "cm":
            if ctx.channel.id == int(tok[1]) and \
                    ctx.command.cog.qualified_name.lower() == tok[3].lower():
                update_use(tok[2] == "enable", n)
        if tok[0] == "sc":
            if ctx.command.name.lower() == tok[1].lower():
                update_use(tok[2] == "enable", n)
        if tok[0] == "sm":
            if ctx.command.cog.qualified_name.lower() == tok[1].lower():
                update_use(tok[2] == "enable", n)
    if not can_use:
        raise aoi.PermissionFailed(f"Permission #{current_n} - {perms[current_n]} "
                                   f"is disallowing you from this command")
    return True

try:
    bot.run(os.getenv("TOKEN"))
except Exception as error:
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
    exit(1)