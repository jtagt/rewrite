import discord
from discord.ext import commands

from core.bot import BotInstance


class Info:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong!")

    @commands.command()
    async def help(self, ctx):
        embed = discord.Embed(title="Himebot - The only music bot you'll ever need",
                              description="For extra support, join [Hime's support server](https://discord.gg/BCAF7rH)",
                              colour=BotInstance.COLOR)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.add_field(name="Commands",
                        value="Hime's complete commands list could be"
                              " found over at [Hime's website](https://himebot.xyz/features_and_commands.html)")
        embed.add_field(name="Getting Started",
                        value="To get started using the Hime, join a voice channel and then use the play command: `.pl"
                              "ay [song name]`the bot will then join the channel and play the requested song!")
        embed.set_footer(text=f"Created by init0#8366, flamekong#0009 & repyh#2900 using discord.py")
        await ctx.send(embed=embed)

    @commands.command(aliases=["botinfo", "stats"])
    async def info(self, ctx):
        embed = discord.Embed(title="Himebot - Statistics", colour=BotInstance.COLOR)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.add_field(name="Playing on", value=f"{1} servers", inline=True)  # placeholder
        embed.add_field(name="Server Count", value=f"{len(self.bot.guilds)}", inline=True)
        embed.add_field(name="User Count", value=f"{len(self.bot.users)}", inline=True)
        embed.add_field(name="Uptime", value="placeholder", inline=True)  # Do this later
        embed.add_field(name="Memory Used", value="placeholder", inline=True)  # psutil
        embed.add_field(name="Total Memory", value="placeholder", inline=True)  # psutil
        embed.add_field(name="Shard", value="placeholder", inline=True)
        embed.add_field(name="Users who've used bot", value="placeholder", inline=True)
        await ctx.send(embed=embed)

    @commands.command(aliases=["invite"])
    async def links(self, ctx):
        pass


def setup(bot):
    bot.add_cog(Info(bot))
