import time
from datetime import datetime

import discord
from discord.ext import commands

from utils.DB import SettingsDB
from utils.misc import get_lyrics, LyricsPaginator
from utils.visual import COLOR, WARNING, SUCCESS

HIME_SERVER_ID = 230772456380432398
BALLER_ROLE_ID = 298728057898795010
CONTRIBUTOR_ROLE_ID = 298728388292509707


class Info:
    def __init__(self, bot):
        self.bot = bot  # flamekong was here xdddddddddddddd

    @commands.command()
    async def ping(self, ctx):
        t1 = time.perf_counter()
        await ctx.channel.trigger_typing()
        t2 = time.perf_counter()
        # Singles quotes to match my relationship status
        fmt = f"\U0001f3d3 **Pong!** `{str(round((t2 - t1) * 100))}ms`"
        # An embed for 7 letters, yes
        em = discord.Embed(description=fmt, color=COLOR)
        await ctx.send(embed=em)

    @commands.command()
    async def help(self, ctx):
        embed = discord.Embed(title="Himebot - The only music bot you'll ever need",
                              description="For extra support join [Hime's support server](https://discord.gg/BCAF7rH)",
                              colour=COLOR)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.add_field(name="Commands",
                        value="Hime's complete commands list could be "
                              "found over at [Hime's website](https://himebot.xyz/features_and_commands.html)")
        embed.add_field(name="Getting Started",
                        value=f"To get started using the Hime, join a voice channel and then use the play command: "
                              f"`{self.bot.bot_settings.prefix}play [song name]` the bot will then join the channel "
                              f"and play the requested song!")
        embed.set_footer(text=f"Created by init0#8366, unazed 💜#4131, flamekong#0009 & repyh#2900 using discord.py")
        await ctx.send(embed=embed)

    @commands.command(aliases=["botinfo", "stats"])
    async def info(self, ctx):
        playing_guilds = self.bot.mpm.lavalink.playing_guilds
        guild_count = sum(val["guild_count"] for val in self.bot.shard_stats.values())
        embed = discord.Embed(title="Himebot - Statistics", colour=COLOR)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.add_field(name="Playing on", value=f"{playing_guilds:,}", inline=True)  # placeholder
        embed.add_field(name="Server Count", value=f"{guild_count:,}", inline=True)
        embed.add_field(name="Uptime", value=f"{str(datetime.now()-self.bot.start_time).split('.')[0]}",
                        inline=True)  # TODO
        if ctx.guild:
            embed.add_field(name="Shard", value=f"{ctx.guild.shard_id}/{self.bot.shard_count}", inline=True)
        await ctx.send(embed=embed)

    @commands.command(aliases=["invite"])
    async def links(self, ctx):
        embed = discord.Embed(description=
                          ("[Add to your server](https://discordapp.com/oauth2/authorize"
                           "?client_id=232916519594491906&scope=bot&permissions=40)\n"
                           "[Join Hime's server](https://discord.gg/BCAF7rH)\n"
                           "[Hime's Website](https://himebot.xyz/)\n"
                           "[Hime's Patreon](https://www.patreon.com/himebot)"),
                          colour=COLOR)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    async def donate(self, ctx):
        embed = discord.Embed(description="Hime has grown incredibly since it first started. In order to keep the music "
                                          "player running with no lag and interruptions, a lot of processing power is "
                                          "required, which is very expensive. So if you enjoy the bot, "
                                          "then please donate to show your affection <3\n"
                                          "[Donate here](https://www.patreon.com/himebot)",
                              colour=COLOR)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_author(name="Why would anyone donate?")
        await ctx.send(embed=embed)

    @commands.command()
    async def partners(self, ctx):
        embed = discord.Embed(colour=COLOR)
        embed.set_author(name="Our partners", icon_url=self.bot.user.avatar_url)

        embed.add_field(name="EMIYA - Unlimited Lewd Works Server",
                    value="A place where we discuss anime related stuff, vidya, events, lewds and karaoke. "
                          "[Discord server](https://discord.gg/2Jd5Tu4) | "
                          "[Facebook page](https://www.facebook.com/xEmiyaShirou)")
        embed.add_field(name="Rap Town - Your #1 source for the best rap music!",
                    value="For the best rap music on YouTube check out Rap Town! "
                          "[YouTube channel](https://www.youtube.com/c/raptown) | "
                          "[Music Discord server](https://discord.gg/thetown)")
        e.add_field(name="Scorchy - Himebot's artist!",
                    value="Scorchy is the artist for Hime's avatar, "
                          "you could check out some of his work on his [Twitter](https://twitter.com/AyyScorchy)")
        await ctx.send(embed=embed)

    @commands.command()
    async def lyrics(self, ctx, *, song):
        lyrics_data = await get_lyrics(song, self.bot.bot_settings.geniusToken)
        error = lyrics_data.get("error")
        if error:
            await ctx.send(f"{WARNING} {error}!")
            return

        lyrics_paginator = LyricsPaginator(ctx, lyrics_data)
        await lyrics_paginator.send_to_channel()

    @commands.command()
    @commands.guild_only()
    async def redeem(self, ctx, server_id: int=None):
        if ctx.guild.id == HIME_SERVER_ID:
            roles = [*map(lambda role: role.id, ctx.author.roles)]
            bot_settings = self.bot.bot_settings

            if not server_id:
                await ctx.send(f"{WARNING} Please include your server ID! Use this command on your server to find out")
                return

            if CONTRIBUTOR_ROLE_ID in roles:
                bot_settings.contributors[ctx.author.id] = server_id
                await ctx.send(f"{SUCCESS} Your guild with the ID of: **{server_id}** "
                               f"now has access to Contributor commands!")
            elif BALLER_ROLE_ID in roles:
                bot_settings.ballers[str(ctx.author.id)] = server_id
                await ctx.send(f"{SUCCESS} Your guild with the ID of: **{server_id}** "
                               f"now has access to Baller commands!")
            else:
                await ctx.send(f"{WARNING} This command is for patrons who have donate $5 or above only!")
                return
            await SettingsDB.get_instance().set_bot_settings(bot_settings)
        else:
            await ctx.send(f"{WARNING} The server ID on this server is: **{ctx.guild.id}**, type `.redeem "
                           f"{ctx.guild.id}` on **Hime's server** to obtain your rewards")


def setup(bot):
    bot.add_cog(Info(bot))
