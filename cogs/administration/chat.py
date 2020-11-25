import asyncio
import datetime
import io
from typing import List, Optional, Union

import discord
from discord.ext import commands
import aoi


class Chat(commands.Cog):
    def __init__(self, bot: aoi.AoiBot):
        self.bot = bot

    @property
    def description(self) -> str:
        return "Commands to deal with chat"

    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 30, commands.BucketType.channel)
    @commands.command(brief="Saves chat in a txt file. Limit can be a message to stop at or a number of messages")
    async def savechat(self, ctx: aoi.AoiContext, channel: Optional[discord.TextChannel],
                       limit: Union[int, discord.Message]):
        time = datetime.datetime.now()
        channel = channel or ctx.channel
        await ctx.trigger_typing()
        # fetch the messages first, in blocks
        current_message: Optional[discord.Message]
        if isinstance(limit, int):
            messages: List[discord.Message] = (await channel.history(limit=min(limit, 1000)).flatten())[::-1]
        else:
            messages: List[discord.Message] = \
                (await channel.history(limit=1000, after=limit).flatten())[::-1]
        buf = io.StringIO()
        buf.write(f"Channel save of {channel.name} [{channel.id}] triggered by {ctx.author} [{ctx.author.id}] on "
                  f"{datetime.datetime.now().strftime('%x %X')}. The messages go from "
                  f"{messages[0].created_at.strftime('%x %X')} "
                  f"to {messages[-1].created_at.strftime('%x %X')}\n\n")
        seen_ids = []
        seen_dates = []
        for m in messages:
            date = m.created_at.strftime("%x")
            if date not in seen_dates:
                seen_dates.append(date)
                buf.write("="*10 + date + "="*10)
            buf.write(f"\n[{m.created_at.strftime('%X')}] ")
            if m.author.id not in seen_ids:
                seen_ids.append(m.author.id)
                buf.write(f"[{m.author} | {m.author.id}] ")
            else:
                buf.write(f"[{m.author}]")
            if m.author.bot:
                buf.write(f" [BOT]")
            content = " " + m.content
            buf.write(f":{content.splitlines(keepends=False)[0]}\n")
            buf.write("\n".join(f"      {line}" for line in content.splitlines(keepends=False)[1:]))
        buf.seek(0)
        await ctx.send(content=f"Saved {len(messages)} in {(datetime.datetime.now() - time).seconds} s",
                       file=discord.File(buf, filename="chat-save.txt"))

    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_channels=True, manage_messages=True)
    @commands.cooldown(1, 30, commands.BucketType.channel)
    @commands.command(brief="Clear message from a channel",
                      flags={"safe": (None, "Ignore pinned messages"),
                                      "from": (discord.Member, "From a certain member")})
    async def clear(self, ctx: aoi.AoiContext, n: int):
        await ctx.trigger_typing()
        # fetch the messages first, in blocks
        messages: List[discord.Message] = []
        channel: discord.TextChannel = ctx.channel
        last_message: Optional[discord.Message] = None
        current_message: Optional[discord.Message]
        reached_bulk_limit = False
        log = False
        if n > 100 or ("from" in ctx.flags and n > 50):
            log = True
            msg = await ctx.send("Fetching messages...")

        while len(messages) < n and not reached_bulk_limit:
            async for current_message in channel.history(limit=min(100, n - len(messages)), before=last_message):
                if current_message.id == ctx.message.id:
                    continue
                if log and current_message.id == msg.id:
                    continue
                last_message = current_message
                if (datetime.datetime.now() - current_message.created_at).days >= 13:
                    reached_bulk_limit = True
                    break
                if "safe" in ctx.flags and current_message.pinned:
                    continue
                if "from" not in ctx.flags or ("from" in ctx.flags and
                                               ctx.flags["from"].id == current_message.author.id):
                    messages.append(current_message)
            if log:
                await msg.edit(content=f"Fetching messages...{len(messages)}/{n}")
            if len(messages) < n and not reached_bulk_limit:
                await asyncio.sleep(1)

        to_delete = [messages[i * 100:(i + 1) * 100] for i in range((len(messages) + 100 - 1) // 100)]

        for n, row in enumerate(to_delete):
            if log:
                await msg.edit(content=f"Deleting batch {n+1}/{len(to_delete)}")
            if len(row) == 0:
                continue
            if len(row) == 1:
                await row[0].delete()
                continue
            await self.bot.http.delete_messages(ctx.channel.id, message_ids=[m.id for m in row],
                                                reason=f"Bulk | {n+1}/{len(to_delete)} | "
                                                       f"{ctx.author} ({ctx.author.id})")
            await asyncio.sleep(1)

        ignore_pins = ", while ignoring pins" if "safe" in ctx.flags else ""
        from_user = f"from {ctx.flags['from'].mention}" if "from" in ctx.flags else ""
        confirmation = f"Done! Cleared {len(messages)} {from_user}{ignore_pins}. " + \
                       ("The 14 day limit was hit." if reached_bulk_limit else "")

        if log:
            await msg.delete()

        await ctx.send_ok(confirmation)




def setup(bot: aoi.AoiBot) -> None:
    bot.add_cog(Chat(bot))
