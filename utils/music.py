from collections import deque

import itertools
from enum import Enum

import discord
import math
from discord.ext import commands

from utils.exceptions import CustomCheckFailure
from utils.magma.core import format_time
from .visual import WARNING, Paginator
from .DB.db import SettingsDB


class UserData(Enum):
    STOPPED = 0
    SKIPPED = 1
    SKIPPED_TO = 2
    UNCHANGED = 3
    REPLACED_AUTOPLAY = 4

    @property
    def may_start_next(self):
        return self.value > 0


class Enqueued:
    def __init__(self, track, requester):
        self.track = track
        self.requester = requester

    def __str__(self):
        return f"{self.track.title} `{format_time(self.track.duration)}`"


class QueuePaginator(Paginator):
    def __init__(self, **kwargs):
        music_player = kwargs.pop("music_player")
        self.items = music_player.queue
        super().__init__(items=self.items, **kwargs)

    @property
    def pages_needed(self):
        return math.ceil(len(self.items)/self.items_per_page) if self.items else 1

    @property
    def embed(self):
        if not self.items:
            return discord.Embed(color=self.color, description="**There are no songs in the queue**")

        lower_bound = self.page*self.items_per_page
        upper_bound = lower_bound+self.items_per_page
        desc = f"**Up next:**\n`1.` {self.items[0]}\n\n"
        to_display = deque(itertools.islice(self.items, lower_bound, upper_bound))

        index_to_add = 1
        if lower_bound == 0:
            index_to_add = 2
            to_display.popleft()

        for i in to_display:
            desc += f"`{to_display.index(i)+lower_bound+index_to_add}.` {i}\n"

        embed = discord.Embed(color=self.color, description=desc)\
            .set_footer(text=f"Page: {self.page%self.pages_needed+1}/{self.pages_needed} | "
                             f"Total duration: {format_time(sum(i.track.duration for i in self.items))}")
        return embed


def music_check(**kwargs):
    in_channel = kwargs.pop("in_channel", False)
    playing = kwargs.pop("playing", False)
    is_dj = kwargs.pop("is_dj", False)
    is_strict_dj = kwargs.pop("is_strict_dj", False)
    is_donor = kwargs.pop("is_donor", "")

    async def predicate(ctx):
        if ctx.author.id in ctx.bot.bot_settings.owners:
            return True

        if not ctx.guild:
            raise CustomCheckFailure(f"{WARNING} This command is guild only")

        if is_donor:
            bot_settings = await SettingsDB.get_instance().get_bot_settings()
            if is_donor == "contributors" and ctx.guild.id not in bot_settings.contributors.values():
                raise CustomCheckFailure(f"{WARNING} This command is for patrons who have donated for the "
                                         f"**contributor** and above tier only. If you want to become a patron, "
                                         f"then type .donate in chat")
            if is_donor == "patrons" and ctx.guild.id not in bot_settings.patrons.values():
                raise CustomCheckFailure(f"{WARNING} This command is for patrons who have donated for the "
                                         f"**baller** and above tier only. If you want to become a patron, "
                                         f"then type .donate in chat")

        settings = await SettingsDB.get_instance().get_guild_settings(ctx.guild.id)
        vc = ctx.guild.get_channel(settings.voiceId)
        tc = ctx.guild.get_channel(settings.textId)
        dj = discord.utils.get(ctx.guild.roles, id=settings.djroleId)

        link = ctx.bot.mpm.lavalink.get_link(ctx.guild, ctx.bot)
        player = link.player

        if in_channel:
            if not ctx.author.voice or not ctx.author.voice.channel:
                raise CustomCheckFailure(f"{WARNING} You must be in a voice channel to use this command!")
            elif vc and ctx.author.voice.channel != vc:
                raise CustomCheckFailure(f"{WARNING} You must be listening in `{vc.name}` to use this command!")

        if tc and ctx.channel != tc:
            raise CustomCheckFailure(f"{WARNING} You must be typing in `{tc.name}` to use this command!")

        if playing and not (player.event_adapter and player.is_playing):
            raise CustomCheckFailure(f"{WARNING} The bot must be playing to use this command!")

        voice = ctx.guild.me.voice
        connected_channel = voice.channel if voice else None

        if is_dj and not (dj in ctx.author.roles or ctx.author.guild_permissions.mute_members):
            if is_strict_dj or connected_channel and len(connected_channel.members) > 2:
                raise CustomCheckFailure(f"{WARNING} You must have the DJ role or the mute "
                                         f"members permission to use this command!")
        return True

    return commands.check(predicate)
