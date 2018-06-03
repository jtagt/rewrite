import random
from asyncio import futures

import discord
from discord.ext import commands

from utils.DB import SettingsDB
from utils.magma.core import format_time
from utils.music import music_check, QueuePaginator
from utils.visual import ERROR, COLOR, NOTES, SUCCESS, WARNING


class Music:
    def __init__(self, bot):
        self.bot = bot
        self.mpm = bot.mpm

    @commands.command(aliases=["join"])
    @music_check(in_channel=True)
    async def connect(self, ctx):
        mp = self.mpm.get_music_player(ctx)
        voice = ctx.guild.me.voice

        if not voice or not voice.channel:
            try:
                await mp.link.connect(ctx.author.voice.channel)
            except commands.BotMissingPermissions:
                await ctx.send(f"{ERROR} I am unable to connect to **{ctx.author.voice.channel.name}**, "
                               f"check if the permissions are correct!")

    @commands.command(aliases=["pl"])
    @music_check(in_channel=True)
    async def play(self, ctx, *, query: str):
        mp = self.mpm.get_music_player(ctx)
        splitted = query.split()
        should_shuffle = False

        if splitted[0] in ("shuffle", "sh"):
            should_shuffle = True
            query = "".join(splitted[1:])

        voice = ctx.guild.me.voice
        if not voice or not voice.channel:
            try:
                await mp.link.connect(ctx.author.voice.channel)
            except commands.BotMissingPermissions:
                await ctx.send(f"{ERROR} I am unable to connect to **{ctx.author.voice.channel.name}**, "
                               f"check if the permissions are correct!")
                return

        if query == "init0":  # easter egg?
            query = "https://www.youtube.com/playlist?list=PLzME6COik-H9hSsEuvAf26uQAN228ESck"
        elif query == "autoplay":
            settings = await SettingsDB.get_instance().get_guild_settings(ctx.guild.id)
            if settings.autoplay == "NONE":
                await ctx.send(f"{WARNING} An autoplay playlist has not been set yet, "
                               f"set one with: `.settings autoplay [DEFAULT/link]`")
            else:
                await mp.load_autoplay(settings.autoplay)
                await ctx.send(f"{NOTES} **Added** the autoplay playlist to the queue")
            return
        elif ctx.guild.id in self.bot.bot_settings.patrons.values():
            settings = await SettingsDB.get_instance().get_guild_settings(ctx.guild.id)
            if settings.aliases and query in settings.aliases:
                query = settings.aliases[query]

        if query.startswith("http"):
            results = await mp.link.get_tracks(query)
        else:
            results = await mp.link.get_tracks_yt(query)

        if not results:
            await ctx.send(f"{WARNING} No results found!")
            return

        if query.startswith("http") and len(results) != 1:
            if should_shuffle:
                random.shuffle(results)
            for track in results:
                await mp.add_track(track, ctx.author)
            await ctx.send(f"{NOTES} **Added** {len(results)} entries to the queue")
        else:
            pos = await mp.add_track(results[0], ctx.author)
            if pos == -1:
                await ctx.send(f"{NOTES} **Added** `{results[0].title}` to be played now")
                return
            await ctx.send(f"{NOTES} **Added** `{results[0].title}` to position: `{pos+1}`")

    @commands.command(aliases=["scsearch"])
    @music_check(in_channel=True)
    async def search(self, ctx, *, query):
        mp = self.mpm.get_music_player(ctx)
        sc = ctx.invoked_with == "scsearch"
        if sc:
            results = await mp.link.get_tracks_sc(query)
        else:
            results = await mp.link.get_tracks_yt(query)

        if not results:
            await ctx.send(f"{WARNING} No results found!")
            return

        desc = ""
        for i in range(5):
            desc += f"{i+1}. [{results[i].title}]({results[i].uri})\n"

        e = discord.Embed(colour=COLOR, description=desc)
        e.set_footer(text=f"Results fetched from {'SoundCloud' if sc else 'YouTube'}", icon_url=ctx.author.avatar_url)
        await ctx.send(content=f"{NOTES} Type the number of the entry you wish to play", embed=e)

        try:
            msg = await self.bot.wait_for("message", check=lambda msg: msg.author.id == ctx.author.id, timeout=30.0)
            index = int(msg.content)
        except ValueError:
            await ctx.send(f"{WARNING} Please use a number as the index!")
            return
        except futures.TimeoutError:
            await ctx.send(f"{WARNING} You have not entered a selection!")
            return

        if not 0 < index < 6:
            await ctx.send(f"{WARNING} The index must be from 1-5!")
            return

        selected = results[index-1]

        voice = ctx.guild.me.voice
        if not voice or not voice.channel:
            try:
                await mp.link.connect(ctx.author.voice.channel)
            except commands.BotMissingPermissions:
                await ctx.send(f"{ERROR} I am unable to connect to **{ctx.author.voice.channel.name}**, "
                               f"check if the permissions are correct!")
                return

        pos = await mp.add_track(selected, ctx.author)
        if pos == -1:
            await ctx.send(f"{NOTES} **Added** `{selected.title}` to be played now")
            return
        await ctx.send(f"{NOTES} **Added** `{selected.title}` to position: `{pos+1}`")

    @commands.command(aliases=["np", "nowplaying"])
    @music_check(playing=True)
    async def current(self, ctx):
        mp = self.mpm.get_music_player(ctx, False)
        embed = mp.embed_current()
        await ctx.send(embed=embed)

    @commands.command(aliases=["prev"])
    @music_check(in_channel=True)
    async def previous(self, ctx):
        mp = self.mpm.get_music_player(ctx, False)
        if not mp or not mp.previous:
            await ctx.send(f"{WARNING} There hasn't been played anything yet!")
            return

        pos = await mp.add_track(mp.previous.track, ctx.author)
        if pos == -1:
            await ctx.send(f"{NOTES} **Added previous track:** `{mp.previous.track.title}` to be played now")
            return
        await ctx.send(f"{NOTES} **Added previous track:** `{mp.previous.track.title}` to position: `{pos+1}`")

    @commands.command(aliases=["q", "songlist"])
    @music_check(playing=True)
    async def queue(self, ctx, page=1):
        mp = self.mpm.get_music_player(ctx, False)
        if not mp.queue:
            await ctx.send(f"{WARNING} No songs are in the queue!")
            return
        if page < 0:
            page = 1
        paginator = QueuePaginator(ctx=ctx, music_player=mp, page=page-1)
        await paginator.send_to_channel()

    @commands.command(aliases=["sh"])
    @music_check(playing=True, is_dj=True)
    async def shuffle(self, ctx):
        mp = self.mpm.get_music_player(ctx, False)
        mp.shuffle()
        await ctx.send(f"{SUCCESS} The queue has been shuffled")

    @commands.command(aliases=["disconnect", "leave"])
    @music_check(in_channel=True, is_dj=True)
    async def stop(self, ctx):
        try:
            mp = self.mpm.get_music_player(ctx, False)
            await mp.stop()
            await mp.link.disconnect()
        except:
            pass
        await ctx.send(f"{SUCCESS} The player has been stopped and the bot has disconnected")

    @commands.command(aliases=["rq", "clearqueue"])
    @music_check(in_channel=True, playing=True, is_dj=True)
    async def reset(self, ctx):
        mp = self.mpm.get_music_player(ctx, False)
        mp.clear()
        await ctx.send(f"{SUCCESS} The queue has been cleared")

    @commands.command(aliases=["r", "delete"])
    @music_check(in_channel=True, playing=True, is_dj=True)
    async def remove(self, ctx, *positions: int):
        try:
            pos_len = len(positions)
            if pos_len == 1:
                pos = positions[0]
                pos -= 1
                mp = self.mpm.get_music_player(ctx, False)
                track = mp.remove(pos)
                await ctx.send(f"{SUCCESS} The track: `{track.track.title}` has been removed")
            else:
                positions = [*positions]
                positions.sort(reverse=True)
                for pos in positions:
                    pos -= 1
                    mp = self.mpm.get_music_player(ctx, False)
                    mp.remove(pos)
                await ctx.send(f"{SUCCESS} Removed `{pos_len}` entries")
        except IndexError:
            await ctx.send(f"{WARNING} The specified position(s) are outside the queue length!")

    @commands.command(aliases=["s", "voteskip"])
    @music_check(playing=True)
    async def skip(self, ctx):
        mp = self.mpm.get_music_player(ctx, False)
        listeners = list(filter(lambda m: not (m.bot or m.voice.deaf or m.voice.self_deaf),
                                ctx.guild.me.voice.channel.members))
        skips_needed = round(len(listeners) * 0.5)
        current_skips = len(mp.skips)
        if mp.current.requester == ctx.author or current_skips + 1 >= skips_needed:
            await mp.skip()
            await ctx.send(f"{SUCCESS} The current song has been skipped")
        else:
            mp.skips.add(ctx.author)
            await ctx.send(f"{SUCCESS} You have voted to skip this song, "
                           f"`{skips_needed-current_skips}` more skips are needed to skip")

    @commands.command(aliases=["jumpto", "jump"])
    @music_check(in_channel=True, playing=True, is_dj=True)
    async def skipto(self, ctx, pos: int):
        mp = self.mpm.get_music_player(ctx, False)
        await mp.skip_to(pos-1)
        await ctx.send(f"{SUCCESS} The current song has been skipped to position: {pos}")

    @commands.command(aliases=["fskip", "modskip"])
    @music_check(in_channel=True, playing=True, is_dj=True)
    async def forceskip(self, ctx):
        mp = self.mpm.get_music_player(ctx, False)
        await mp.skip()
        await ctx.send(f"{SUCCESS} The current song has been skipped")

    @commands.command(aliases=["mov", ".playafter"])
    @music_check(in_channel=True, playing=True, is_dj=True)
    async def move(self, ctx, *, args):
        mp = self.mpm.get_music_player(ctx, False)
        queue = mp.queue
        queue_len = len(queue)

        to_move = args
        pos = 1

        splitted = args.split()
        if splitted[-1].isdecimal() and len(splitted) > 1:
            pos = int(splitted[-1])
            to_move = " ".join(splitted[:-1])

        try:
            to_move = int(to_move)
            to_move -= 1
        except ValueError:
            for i in range(queue_len):
                if to_move.lower() in queue[i].track.title.lower():
                    to_move = i
                    break
            else:
                await ctx.send(f"{WARNING} No song found with that name!")
                return

        pos -= 1
        if not (0 <= to_move < queue_len) or not (0 <= pos <= queue_len):
            await ctx.send(f"{WARNING} The specified positions must be from `0-{queue_len}`!")
            return
        moved = mp.move(to_move, pos)
        if pos == 0:
            await ctx.send(f"{SUCCESS} The track: {moved} has been moved to be played next")
        else:
            await ctx.send(f"{SUCCESS} The track: {moved} has been moved to position {pos+1}")

    @commands.command()
    @music_check(in_channel=True, playing=True, is_dj=True)
    async def seek(self, ctx, timestamp: str):
        mp = self.mpm.get_music_player(ctx, False)
        current_pos = round(mp.player.position)
        try:
            if ":" in timestamp:
                ts_split = [0, 0] + [int(t) for t in timestamp.split(':')]
                hours = ts_split[-3]
                mins = ts_split[-2]
                secs = ts_split[-1]
                pos = (secs + 60 * (mins + 60 * hours)) * 1000
            else:
                pos = current_pos + int(timestamp)*1000
        except ValueError:
            await ctx.send(f"{WARNING} The specified duration must be a number!")
            return

        await mp.player.seek_to(pos)
        await ctx.send(f"{SUCCESS} The current song has been seeked to `{format_time(pos)}`")

    @commands.command(aliases=["p"])
    @music_check(in_channel=True, playing=True, is_dj=True)
    async def pause(self, ctx):
        mp = self.mpm.get_music_player(ctx, False)
        if mp.player.paused:
            await ctx.send(f"{WARNING} The player is already paused!")
            return

        await mp.player.set_paused(True)
        await ctx.send(f"{SUCCESS} The player has been paused")

    @commands.command(aliases=["re"])
    @music_check(in_channel=True, playing=True, is_dj=True)
    async def resume(self, ctx):
        mp = self.mpm.get_music_player(ctx, False)
        if not mp.player.paused:
            await ctx.send(f"{WARNING} The player is not paused!")
            return

        await mp.player.set_paused(False)
        await ctx.send(f"{SUCCESS} The player has been resumed")

    @commands.command(aliases=["loop"])
    @music_check(in_channel=True, playing=True, is_dj=True)
    async def repeat(self, ctx):
        settings = await SettingsDB.get_instance().get_guild_settings(ctx.guild.id)
        settings.repeat = not settings.repeat
        await SettingsDB.get_instance().set_guild_settings(settings)
        await ctx.send(f"{SUCCESS} The repeat state has been set to `{settings.repeat}`")

    @commands.command(aliases=["vol"])
    @music_check(in_channel=True, playing=True, is_dj=True, is_donor="contributors")
    async def volume(self, ctx, volume: int):
        if not 0 <= volume <= 150:
            await ctx.send(f"{WARNING} The specified volume must be from `0-150`!")
            return

        mp = self.mpm.get_music_player(ctx, False)
        await mp.player.set_volume(volume)
        settings = await SettingsDB.get_instance().get_guild_settings(ctx.guild.id)
        settings.volume = volume
        await SettingsDB.get_instance().set_guild_settings(settings)
        await ctx.send(f"{SUCCESS} The player volume has been set to `{volume}`")


def setup(bot):
    bot.add_cog(Music(bot))
