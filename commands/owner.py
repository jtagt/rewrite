import asyncio

import aiohttp
from discord.ext import commands

from utils.visual import ERROR
from utils.visual import SUCCESS
from utils.misc import is_owner


class Owner:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @is_owner()
    async def load(self, ctx, *, cog: str):
        """Command which Loads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')

    @commands.command()
    @is_owner()
    async def unload(self, ctx, *, cog: str):
        """Command which Unloads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.unload_extension(cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')

    @commands.command()
    @is_owner()
    async def reload(self, ctx, *, cog: str):
        """Command which Unloads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.unload_extension(cog)
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')

    @commands.command(aliases=["x"])
    @is_owner()
    async def subproc(self, ctx, *, command: str):
        try:
            proc = await asyncio.create_subprocess_exec("/usr/bin/zsh", "-c", command, stdout=asyncio.subprocess.PIPE,
                                                        stderr=asyncio.subprocess.STDOUT)
            data = await proc.stdout.read()
            await proc.wait()
            decoded = data.decode()
            output = decoded.rstrip()
            if len(output) == 0:
                output = f"{SUCCESS} The command has been executed successfully"
            else:
                output = f"```{output[:1994]}```"
            await ctx.send(output)
        except asyncio.TimeoutError:
            await ctx.send(f"{ERROR} The command has timed out!")

    @commands.command()
    @is_owner()
    async def exception(self, ctx):
        raise Exception(ctx)


def setup(bot):
    bot.add_cog(Owner(bot))
