import re

import discord
from discord.ext import commands

from utils.DB import SettingsDB
from utils.exceptions import CustomCheckFailure
from utils.music import music_check
from utils.visual import COLOR, WARNING, NOTES
from utils.visual import SUCCESS


def perm_check():
    def predicate(ctx):
        if not ctx.author.guild_permissions.manage_roles:
            raise CustomCheckFailure(f"{WARNING} You must have the manage roles permissions to use this command!")
        return True

    return commands.check(predicate)


class Settings:
    def __init__(self, bot):
        self.bot = bot
        self.autoplay_pattern = re.compile("^(https?://)?((www\.)?youtube\.com|youtu\.?be)/.+$")

    @commands.group(pass_context=True, invoke_without_command=True, case_insensitive=True)
    @commands.guild_only()
    async def settings(self, ctx):
        guild = ctx.guild
        settings = await SettingsDB.get_instance().get_guild_settings(guild.id)
        dj_role = discord.utils.get(guild.roles, id=settings.djroleId)
        text_chan = guild.get_channel(settings.textId)
        voice_chan = guild.get_channel(settings.voiceId)

        dj_role = f"{dj_role.name}" if dj_role else "NONE"
        text_chan = f"{text_chan.name}" if text_chan else "NONE"
        voice_chan = f"{voice_chan.name}" if voice_chan else "NONE"

        volume = settings.volume
        autoplay = settings.autoplay
        repeat = settings.repeat
        tms = settings.tms
        prefix = settings.prefix

        e = discord.Embed(description=f"DJ role: {dj_role}\n"
                                      f"Text channel: {text_chan}\n"
                                      f"Voice channel: {voice_chan}\n"
                                      f"Volume: {volume}\n"
                                      f"Autoplay: {autoplay}\n"
                                      f"Repeat: {repeat}\n"
                                      f"Now playing messages: {tms}\n"
                                      f"Prefix: {prefix}",
                          colour=COLOR)

        await ctx.send(content=f":tools: Settings for **{guild.name}**", embed=e)

    @settings.command()
    @perm_check()
    async def dj(self, ctx, *, role):
        settings = await SettingsDB.get_instance().get_guild_settings(ctx.guild.id)
        if role.lower() == "none":
            settings.djroleId = "NONE"
            await SettingsDB.get_instance().set_guild_settings(settings)
            await ctx.send(f"{SUCCESS} The DJ role has been cleared, only people with the manage server permission "
                           f"can use DJ commands now")
        else:
            try:
                role = await commands.RoleConverter().convert(ctx, role)
            except commands.BadArgument:
                await ctx.send(f"{WARNING} That role was not found!")
                return
            settings.djroleId = role.id
            await SettingsDB.get_instance().set_guild_settings(settings)
            await ctx.send(f"{SUCCESS} DJ commands can now only be used by people who have the **{role.name}** role "
                           f"or the manage server permission")

    @settings.command()
    @perm_check()
    async def tc(self, ctx, *, channel):
        settings = await SettingsDB.get_instance().get_guild_settings(ctx.guild.id)
        if channel.lower() == "none":
            settings.textId = "NONE"
            await SettingsDB.get_instance().set_guild_settings(settings)
            await ctx.send(f"{SUCCESS} The music text channel has been cleared, people can now use music commands in "
                           f"all text channels")
        else:
            try:
                channel = await commands.TextChannelConverter().convert(ctx, channel)
            except commands.BadArgument:
                await ctx.send(f"{WARNING} That channel was not found!")
                return
            settings.textId = channel.id
            await SettingsDB.get_instance().set_guild_settings(settings)
            await ctx.send(f"{SUCCESS} Music commands can now only be used in the **{channel.name}** text channel")

    @settings.command()
    @perm_check()
    async def vc(self, ctx, *, channel):
        settings = await SettingsDB.get_instance().get_guild_settings(ctx.guild.id)
        if channel.lower() == "none":
            settings.voiceId = "NONE"
            await SettingsDB.get_instance().set_guild_settings(settings)
            await ctx.send(f"{SUCCESS} The music voice channel has been cleared, people can now play music in all "
                           f"channels")
        else:
            try:
                channel = await commands.VoiceChannelConverter().convert(ctx, channel)
            except commands.BadArgument:
                await ctx.send(f"{WARNING} That channel was not found!")
                return
            settings.voiceId = channel.id
            await SettingsDB.get_instance().set_guild_settings(settings)
            await ctx.send(f"{SUCCESS} Music can now only be played in the **{channel.name}** voice channel")

    @settings.command(aliases=["ap"])
    @perm_check()
    async def autoplay(self, ctx, *, link):
        settings = await SettingsDB.get_instance().get_guild_settings(ctx.guild.id)
        if link.lower() == "none":
            settings.autoplay = "NONE"
            await SettingsDB.get_instance().set_guild_settings(settings)
            await ctx.send(f"{SUCCESS} The autoplay playlist has been cleared, autoplay won't start anymore when the "
                           f"queue ends")
        elif link.lower() == "default":
            settings.autoplay = "DEFAULT"
            await SettingsDB.get_instance().set_guild_settings(settings)
            await ctx.send(f"{SUCCESS} The autoplay playlist has been set to the default playlist, autoplay will play "
                           f"once the queue ends")
        else:
            if not self.autoplay_pattern.match(link):
                await ctx.send(f"{WARNING} The autoplay link must be linking to a YouTube playlist!")
                return
            settings.autoplay = link
            await SettingsDB.get_instance().set_guild_settings(settings)
            await ctx.send(f"{SUCCESS} The autoplay playlist has been set to `{link}`, autoplay will play "
                           f"once the queue ends")

    @settings.command(aliases=["musicspam", "ms"])
    @perm_check()
    async def tms(self, ctx, toggle: bool):
        settings = await SettingsDB.get_instance().get_guild_settings(ctx.guild.id)
        if toggle:
            settings.tms = True
            await SettingsDB.get_instance().set_guild_settings(settings)
            await ctx.send(f"{SUCCESS} Now playing messages will now be sent when a song starts")
        else:
            settings.tms = False
            await SettingsDB.get_instance().set_guild_settings(settings)
            await ctx.send(f"{SUCCESS} Now playing messages will now not be sent when a song starts")

    @settings.command()
    @perm_check()
    async def prefix(self, ctx, prefix):
        settings = await SettingsDB.get_instance().get_guild_settings(ctx.guild.id)
        if prefix.lower() in (self.bot.bot_settings.prefix, "none"):
            settings.prefix = "NONE"
            await SettingsDB.get_instance().set_guild_settings(settings)
            self.bot.prefix_map.pop(ctx.guild.id, None)
            await ctx.send(f"{SUCCESS} The prefix has been reset to the default prefix: "
                           f"`{self.bot.bot_settings.prefix}`")
        else:
            if len(prefix) > 3:
                await ctx.send(f"{WARNING} The prefix can only be 3 characters or less")
                return
            settings.prefix = prefix
            await SettingsDB.get_instance().set_guild_settings(settings)
            self.bot.prefix_map[ctx.guild.id] = prefix
            await ctx.send(f"{SUCCESS} The prefix has been changed to: `{prefix}`\ncommands should now be invoked as: "
                           f"`{prefix}play, {prefix}stop, {prefix}resume`")

    @commands.group(pass_context=True, invoke_without_command=True, case_insensitive=True)
    @music_check(is_dj=True, is_strict_dj=True, is_donor="patrons")
    async def aliases(self, ctx):
        settings = await SettingsDB.get_instance().get_guild_settings(ctx.guild.id)
        aliases = settings.aliases if settings.aliases else {}
        if not aliases:
            await ctx.send(f"{WARNING} No aliases having been set! Add an alias with: `.aliases add [alias] [link]`")
            return

        embed = discord.Embed(color=COLOR)
        embed.set_footer(text="The name of the aliases are displayed above their links/values")
        for i in aliases:
            embed.add_field(name=i, value=aliases[i], inline=False)
        await ctx.send(content=f"{NOTES} Music aliases for **{ctx.guild.name}**", embed=embed)

    @aliases.command()
    @music_check(is_dj=True, is_strict_dj=True, is_donor="patrons")
    async def add(self, ctx, alias, *, link):
        settings = await SettingsDB.get_instance().get_guild_settings(ctx.guild.id)
        if not settings.aliases:
            settings.aliases = {}
        settings.aliases[alias] = link
        await SettingsDB.get_instance().set_guild_settings(settings)
        await ctx.send(f"{SUCCESS} The alias `{alias}` is now pointing to `{link}`. Use `.pl {alias}` to play it")

    @aliases.command(aliases=["delete"])
    @music_check(is_dj=True, is_strict_dj=True, is_donor="patrons")
    async def remove(self, ctx, alias):
        settings = await SettingsDB.get_instance().get_guild_settings(ctx.guild.id)
        if alias not in settings.aliases:
            await ctx.send(f"{WARNING} The alias `{alias}` is not found!")
            return
        del settings.aliases[alias]
        await SettingsDB.get_instance().set_guild_settings(settings)
        await ctx.send(f"{SUCCESS} The alias `{alias}` has been removed")


def setup(bot):
    bot.add_cog(Settings(bot))
