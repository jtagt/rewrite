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
        prefixes = set()
        if msg.guild:
            prefixes.add(bot.prefix_map.get(msg.guild.id, bot.bot_settings.prefix))
        else:
            prefixes.add(bot.bot_settings.prefix)
        return commands.when_mentioned_or(*prefixes)(bot, msg)

    def __init__(self, bot_settings, shard_stats, **kwargs):
        super().__init__(Bot.prefix_from, **kwargs)
        self.shard_stats = shard_stats
        self.logger = logging.getLogger("bot")
        self.start_time = datetime.now()
        self.bot_settings = bot_settings
        self.prefix_map = {}
        self.ready = False
        self.mpm = None

    @property
    def stats(self):
        return {
            "guild_count": len(self.guilds),
        }

    async def load_everything(self):
        await self.load_all_nodes()
        await self.load_all_prefixes()
        self.load_all_commands()

    async def load_all_nodes(self):
        self.mpm = MusicPlayerManager(self)
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
        if exc_class in (commands.CommandNotFound, commands.NotOwner, discord.Forbidden):
            return

        exc_table = {
            commands.MissingRequiredArgument: f"{WARNING} The required arguments are missing for this command!",
            commands.NoPrivateMessage: f"{WARNING} This command cannot be used in PM's!",
            commands.BadArgument: f"{WARNING} A bad argument was passed, please check if your arguments are correct!",
            IllegalAction: f"{WARNING} A node error has occurred: `{getattr(exception, 'msg', None)}`",
            CustomCheckFailure: getattr(exception, "msg", None) or "None"
        }

        if exc_class in exc_table.keys():
            await ctx.send(exc_table[exc_class])
        else:
            if ctx.guild:
                self.logger.error(f"Exception in guild: {ctx.guild.name} | {ctx.guild.id}, shard: {self.shard_id}")
            await super().on_command_error(ctx, exception)

    def run(self, *args, **kwargs):
        self.remove_command("help")
        super().run(*args, **kwargs)
