import asyncio
import logging
import os
from datetime import datetime

import discord
from discord.ext import commands

from audio.player_manager import MusicPlayerManager
from utils.DB import SettingsDB
from utils.exceptions import CustomCheckFailure
from utils.magma.core import NodeException, IllegalAction
from utils.visual import WARNING


class Bot(commands.Bot):

    @staticmethod
    def prefix_from(bot, msg):
        # must be an instance of this bot pls dont use anything else
        # return "_----_----__-_"
        prefixes = set()
        if msg.guild:
            prefixes.add(bot.prefix_map.get(msg.guild.id, bot.bot_settings.prefix))
        else:
            prefixes.add(bot.bot_settings.prefix)
        return commands.when_mentioned_or(*prefixes)(bot, msg)

    def __init__(self, bot_settings, **kwargs):
        self.shard_stats = kwargs.pop("shard_stats")
        self.command_queue = kwargs.pop("command_queue")
        self.shard_cluster = kwargs.get("shard_cluster")
        self.lavalink = kwargs.get("lavalink")
        super().__init__(Bot.prefix_from, **kwargs)
        self.logger = logging.getLogger("bot")
        self.start_time = datetime.now()
        self.bot_settings = bot_settings
        self.prefix_map = {}
        self.ready = False
        self.mpm = None

        self.remove_command("help")

    @property
    def stats(self):
        return {
            "guild_count": len(self.guilds),
        }

    async def load_all_nodes(self):
        self.mpm = MusicPlayerManager(self)
        for (node, conf) in self.bot_settings.lavaNodes.items():
            try:
                await self.mpm.lavalink.add_node(node, conf["uri"], conf["restUri"], conf["password"])
            except NodeException as e:
                self.logger.error(f"{node} - {e.args[0]}")

    async def load_everything(self):
        if self.lavalink:
            self.mpm = MusicPlayerManager(self, self.lavalink)
        else:
            await self.load_all_nodes()

        await self.load_all_prefixes()
        self.load_all_commands()

    async def load_music_player_manager(self):
        self.mpm = MusicPlayerManager(self, self.lavalink)
        for (node, conf) in self.bot_settings.lavaNodes.items():
            try:
                await self.mpm.lavalink.add_node(node, conf["uri"], conf["restUri"], conf["password"])
            except NodeException as e:
                self.logger.error(f"{node} - {e.args[0]}")

    async def load_all_prefixes(self):
        prefix_servers = SettingsDB.get_instance().guild_settings_col.find(
            {
                "$and": [
                    {"prefix": {"$exists": True}},
                    {"prefix": {"$ne": "NONE"}}
                ]
            }
        )

        async for i in prefix_servers:
            self.prefix_map[i["_id"]] = i["prefix"]

    def load_all_commands(self):
        commands_dir = "commands"
        ext = ".py"
        for file_name in os.listdir(commands_dir):
            if file_name.endswith(ext):
                command_name = file_name[:-len(ext)]
                self.load_extension(f"{commands_dir}.{command_name}")

    async def on_ready(self):
        if self.ready:
            return

        await self.load_everything()
        await self.change_presence(activity=discord.Game(name=self.bot_settings.game))

        self.logger.info(f"Shard: {self.shard_id}/{self.shard_count} has been loaded!")
        self.ready = True

        while True:
            # The first shard number is the identifier
            self.shard_stats[self.shard_id] = self.stats
            await asyncio.sleep(60)

    async def on_message(self, msg):
        if not msg.author.bot:
            await self.process_commands(msg)

    async def on_command_error(self, ctx, exception):
        exc_class = exception.__class__
        if exc_class == commands.CommandInvokeError:
            exception = exception.original
            exc_class = exception.__class__
        if exc_class in (commands.CommandNotFound, commands.NotOwner, discord.Forbidden, discord.Forbidden):
            return

        exc_table = {
            commands.MissingRequiredArgument: f"{WARNING} The required arguments are missing for this command!",
            commands.NoPrivateMessage: f"{WARNING} This command cannot be used in PM's!",
            commands.BadArgument: f"{WARNING} A bad argument was passed, please check if your arguments are correct!",
            IllegalAction: f"{WARNING} A node error has occurred: `{getattr(exception, 'msg', None) or getattr(exception, 'args')}`",
            CustomCheckFailure: getattr(exception, "msg", None) or getattr(exception, 'args')
        }

        if exc_class in exc_table.keys():
            await ctx.send(exc_table[exc_class])
        else:
            if ctx.guild:
                self.logger.error(f"Exception in guild: {ctx.guild.name} | {ctx.guild.id}, shard: {self.shard_id}")
            await super().on_command_error(ctx, exception)

    async def on_guild_remove(self, guild):
        await SettingsDB.get_instance().remove_guild_settings(guild.id)
        self.prefix_map.pop(guild.id, None)
        if guild.id in self.mpm.music_players:
            self.mpm.music_players.pop(guild.id)
        if guild.id in self.mpm.lavalink.links:
            await self.mpm.lavalink.links[guild.id].destroy()

    async def on_guild_join(self, guild):
        channel = guild.system_channel or \
                  next(chan for chan in guild.text_channels if chan.permissions_for(guild.me).send_messages)

        await channel.send(f":tada: Thanks for inviting me to the server! You can get a quick start guide by typing "
                           f"`.help`.\nIf you need any support, you are welcome to join our server by clicking on the "
                           f"link in `.invite`")

