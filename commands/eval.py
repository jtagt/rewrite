import inspect
import io
import traceback
from contextlib import redirect_stdout

from discord.ext import commands

from utils.DB import SettingsDB
from utils.misc import get_syntax_error, is_owner


class Eval:
    def __init__(self, bot):
        self.bot = bot
        self.last_result = None
        self.context = {
            "bot": self.bot,
            "db": SettingsDB.get_instance(),
            "bs": self.bot.bot_settings,
            "mpm": self.bot.mpm
        }
    
    @commands.command(aliases=["e"])
    @is_owner()
    async def eval(self, ctx, *, code: str):
        stdout = io.StringIO()
        result = ""

        self.context.update({
            "ctx": ctx,
            "ch": ctx.channel,
            "author": ctx.author,
            "msg": ctx.message,
            "_": self.last_result
        })

        if ctx.guild:
            self.context.update({
                "self": ctx.guild.me,
                "guild": ctx.guild
            })

        try:
            with redirect_stdout(stdout):
                for executor in (eval, exec):
                    try:
                        result = executor(code, self.context)
                        if inspect.isawaitable(result):
                            result = await result
                        break
                    except SyntaxError as e:
                        result = get_syntax_error(e)
        except:
            result = stdout.getvalue() + traceback.format_exc()
        finally:
            if not result:
                result = stdout.getvalue()
            
            self.last_result = result
        
        await ctx.send(f"```py\n{str(result)[:1990]}\n```")


def setup(bot):
    bot.add_cog(Eval(bot))
