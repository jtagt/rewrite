from collections import deque
from random import shuffle
import discord
import itertools

from utils.DB import SettingsDB
from utils.magma.core import TrackPauseEvent, TrackResumeEvent, TrackStartEvent, TrackEndEvent, \
    AbstractPlayerEventAdapter, TrackExceptionEvent, TrackStuckEvent, format_time
from utils.music import UserData, Enqueued
from utils.visual import NOTES, COLOR, WARNING


class MusicQueue:
    def __init__(self, items=None):
        self.items = items if items else deque()

    def __len__(self):
        return self.items.__len__()

    def __getitem__(self, item):
        return self.items[item]

    @property
    def empty(self):
        return not self.items

    def index(self, item):
        return self.items.index(item)

    def popleft(self):
        return self.items.popleft()

    def put(self, item):
        self.items.append(item)
        return self.index(item)

    def fair_put(self, item):
        # look at this one liner
        position = len(set(map(lambda i: i.requester, self.items)))
        last_index = 0
        queue_len = self.__len__()
        for index in range(queue_len-1, 0, -1):
            if self.items[index].requester == item.requester:
                last_index = index
                break

        position += last_index
        if position > queue_len:
            position = queue_len
        self.items.insert(position, item)
        return position

    def remove(self, to_remove):
        removed = self.items[to_remove]
        self.items.remove(removed)
        return removed

    def shorten(self, start):
        self.items = deque(itertools.islice(self.items, start, self.__len__()))

    def clear(self):
        self.items.clear()

    def move(self, to_move, pos):
        moved = self.items[to_move]
        self.items.remove(moved)
        self.items.insert(pos, moved)
        return moved

    def shuffle(self):
        shuffle(self.items)


class MusicPlayer(AbstractPlayerEventAdapter):
    def __init__(self, ctx, link):
        self.ctx = ctx
        self.link = link
        self.player = link.player
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.skips = set()
        self.queue = MusicQueue()
        self.repeat_queue = deque()
        self.paused = False
        self.autoplaying = False
        self.current = None
        self.previous = None
        self.previous_np_msg = None

        link.player.event_adapter = self

    def embed_current(self):
        track = self.current.track
        title = track.title
        url = track.uri
        requester = self.current.requester.name
        progress = f"{format_time(self.player.position)}/{format_time(track.duration)}"

        embed = discord.Embed(description=f"[{title}]({url})", color=COLOR) \
            .set_author(name="Now playing", icon_url=self.current.requester.avatar_url) \
            .add_field(name="Requested by", value=requester, inline=True) \
            .add_field(name="Progress", value=progress, inline=True)
        if "youtube" in url:
            embed.set_thumbnail(url=f"https://img.youtube.com/vi/{track.identifier}/hqdefault.jpg")
        return embed

    def shuffle(self):
        self.queue.shuffle()

    def remove(self, to_remove):
        return self.queue.remove(to_remove)

    def move(self, to_move, pos):
        return self.queue.move(to_move, pos)

    async def get_music_chan(self):
        settings = await SettingsDB.get_instance().get_guild_settings(self.guild.id)
        text_id = settings.textId
        return self.guild.get_channel(text_id)

    async def tms(self):
        settings = await SettingsDB.get_instance().get_guild_settings(self.guild.id)
        return settings.tms

    async def add_track(self, audio_track, requester):
        return await self.add_enqueued(Enqueued(audio_track, requester))

    async def add_enqueued(self, enqueued):
        enqueued.track.user_data = UserData.UNCHANGED
        if not self.current:
            self.current = enqueued
            await self.player.play(enqueued.track)
            return -1
        if self.autoplaying:
            self.current.track.user_data = UserData.REPLACED_AUTOPLAY
            self.autoplaying = False
            self.queue.clear()
            self.queue.put(enqueued)
            await self.player.stop()
            return -1
        return self.queue.fair_put(enqueued)

    def clear_queue(self):
        self.queue.clear()
        self.repeat_queue.clear()

    def clear_everything(self):
        self.current = None
        self.paused = False
        self.autoplaying = False
        self.clear_queue()

    async def stop(self):
        self.clear_everything()
        if self.player.current:
            self.player.current.user_data = UserData.STOPPED
            await self.player.stop()

    async def skip(self):
        self.player.current.user_data = UserData.SKIPPED
        await self.player.stop()

    async def skip_to(self, pos):
        self.player.current.user_data = UserData.SKIPPED_TO
        self.queue.shorten(pos)
        await self.player.stop()

    async def load_autoplay(self, identifier):
        if identifier == "DEFAULT":
            bot_settings = self.bot.bot_settings
            playlist = bot_settings.autoplayPlaylist
        else:
            playlist = identifier

        tracks = await self.link.get_tracks(playlist)
        shuffle(tracks)
        for track in tracks:
            await self.add_track(track, self.guild.me)
        self.autoplaying = True

    async def track_pause(self, event: TrackPauseEvent):
        self.paused = True

    async def track_resume(self, event: TrackResumeEvent):
        self.paused = False

    async def track_start(self, event: TrackStartEvent):
        self.skips.clear()
        self.repeat_queue.append(self.current)
        topic = f"{NOTES} **Now playing** {self.current}"
        music_channel = await self.get_music_chan()
        tms = await self.tms()
        try:
            if tms:
                if self.previous_np_msg:
                    await self.previous_np_msg.delete()

                if music_channel:
                        self.previous_np_msg = await music_channel.send(topic)
                        await music_channel.edit(topic=topic)
                else:
                    self.previous_np_msg = await self.ctx.send(topic)
        except:
            pass

    async def track_end(self, event: TrackEndEvent):
        music_channel = await self.get_music_chan()

        if event.track and not event.track.user_data.may_start_next:
            return

        self.previous = self.current
        if self.queue.empty:
            settings = await SettingsDB.get_instance().get_guild_settings(self.guild.id)

            if settings.repeat:
                self.queue = MusicQueue(self.repeat_queue)
                self.repeat_queue = deque()
            elif settings.autoplay != "NONE" and not self.autoplaying:
                await self.load_autoplay(settings.autoplay)
                tms = await self.tms()
                if tms:
                    to_send = f"{NOTES} **Added** the autoplay playlist to the queue"
                    if music_channel:
                        await music_channel.send(to_send)
                    else:
                        await self.ctx.send(to_send)

        if not self.queue.empty:
            self.current = self.queue.popleft()
            await self.player.play(self.current.track)
            return

        await self.stop()
        if self.guild.id not in self.bot.bot_settings.patrons.values():
            await self.link.disconnect()

        if music_channel:
            try:
                await music_channel.edit(topic="Not playing anything right now...")
            except discord.Forbidden:
                pass

    async def track_exception(self, event: TrackExceptionEvent):
        music_channel = await self.get_music_chan()
        msg = f"{WARNING} An exception has occurred for the track: **{event.track.title}**: `{event.exception}`"

        if music_channel:
            await music_channel.send(msg)
        else:
            await self.ctx.send(msg)

    async def track_stuck(self, event: TrackStuckEvent):
        pass

    async def destroy(self):
        self.clear_everything()
        if self.guild.id in self.bot.mpm.music_players:
            self.bot.mpm.music_players.pop(self.guild.id)
