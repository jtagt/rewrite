import asyncio
import logging
import os
from datetime import datetime

from discord.ext import commands

from audio.player_manager import MusicPlayerManager
from utils.DB import SettingsDB
from utils.exceptions import CustomCheckFailure
from utils.magma.core import NodeException, IllegalAction
from utils.visual import WARNING


class Bot(commands.AutoShardedBot):

    @staticmethod
    def prefix_from(bot, msg):
        prefixes = set()
        if msg.guild:
            prefixes.add(bot.prefix_map.get(msg.guild.id, bot.bot_settings.prefix))
        else:
            prefixes.add(bot.bot_settings.prefix)
        return commands.when_mentioned_or(*prefixes)(bot, msg)
      
    def __init__(self, bot_settings, **kwargs):
        super().__init__(Bot.prefix_from, **kwargs)
        self.logger = logging.getLogger("bot")
        self.start_time = datetime.now()
        self.bot_settings = bot_settings
        self.prefix_map = {}
        self.mpm = None
        self.ready = False

    async def on_ready(self):
        if self.ready:
            return

        logging.getLogger("magma").setLevel(logging.DEBUG)
        logging.getLogger('websockets').setLevel(logging.INFO)
        logging.getLogger("discord").setLevel(logging.WARNING)

        self.logger.info("!! Logged in !!")
        self.remove_command("help")

        self.mpm = MusicPlayerManager(self)

        for (node, conf) in self.bot_settings.lavaNodes.items():
            try:
                await self.mpm.lavalink.add_node(node, conf["uri"], conf["restUri"], conf["password"])
            except NodeException as e:
                self.logger.error(f"{node} - {e.args[0]}")

        prefix_servers = SettingsDB.get_instance().guild_settings_col.find(
            {
                "$and": [
                        {"prefix": {"$exists": True}},
                        {"prefix": {"$ne": "NONE"}}
                        ]
            }
        )

        async for server in prefix_servers:
            self.prefix_map[server["_id"]] = server["prefix"]

        commands_dir = "commands"
        ext = ".py"
        for filename in os.listdir(commands_dir):
            if filename.endswith(ext):
                command_name = filename[:-len(ext)]
                self.load_extension(f"{commands_dir}.{command_name}")

        self.ready = True

    async def on_shard_ready(self, shard_id):
        self.logger.info(f"Shard: {shard_id}/{self.shard_count} is ready")

    async def on_message(self, msg):
        if not msg.author.bot:
            await self.process_commands(msg)

    async def on_command_error(self, ctx, exception):
        exc_class = exception.__class__
        if exc_class in (commands.CommandNotFound, commands.NotOwner):
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
            await super().on_command_error(ctx, exception)
