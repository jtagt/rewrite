import asyncio

from utils.magma.core import Lavalink
from .player import MusicPlayer


class MusicPlayerManager:
    def __init__(self, bot, lavalink=None):
        self.bot = bot
        self.lavalink = lavalink or Lavalink(bot.user.id, bot.shard_count)
        self.music_players = {}
        self.timeout_tasks = {}

        self.bot.add_listener(self.on_voice_state_update)
        self.bot.add_listener(self.lavalink.on_socket_response)

    def get_music_player(self, ctx, select_if_absent=True):
        if not select_if_absent or ctx.guild.id in self.music_players:
            return self.music_players.get(ctx.guild.id)

        link = self.lavalink.get_link(ctx.guild, self.bot)
        mp = MusicPlayer(ctx, link)
        self.music_players[ctx.guild.id] = mp
        return mp

    def find_all(self, predicate):
        return dict(filter(predicate, self.music_players.items()))

    async def on_voice_state_update(self, member, before, after):
        if member.bot or member.guild.id not in self.music_players:
            return

        bot_voice = member.guild.me.voice
        if not bot_voice or not bot_voice.channel:
            return

        bot_channel = bot_voice.channel
        if bot_channel == before.channel:
            await self.voice_left(before.channel)
        elif bot_channel == after.channel:
            await self.voice_joined(after.channel)

    async def voice_left(self, channel):
        users = list(filter(lambda m: not m.bot, channel.members))
        if len(users) > 0:
            return

        task = self.bot.loop.create_task(self.timeout_task(channel))
        self.timeout_tasks[channel.id] = task
        await task

    async def voice_joined(self, channel):
        mp = self.music_players.get(channel.guild.id)
        users = list(filter(lambda m: not m.bot, channel.members))
        if mp and mp.player.paused and len(users) < 3:
            await mp.player.set_paused(False)

        if channel.id in self.timeout_tasks:
            self.timeout_tasks[channel.id].cancel()
            self.timeout_tasks.pop(channel.id)

    async def timeout_task(self, channel):
        mp = self.music_players[channel.guild.id]
        await mp.player.set_paused(True)

        if channel.guild.id not in self.bot.bot_settings.patrons.values():
            await asyncio.sleep(180)  # maybe should use a variable but who cares u know
            users = list(filter(lambda m: not m.bot, channel.members))
            if len(users) > 0:
                return

            await mp.player.set_paused(False)
            await mp.stop()
            await mp.link.disconnect()

        self.timeout_tasks.pop(channel.id, None)
