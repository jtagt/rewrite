from asyncio import futures

import discord
import math

COLOR = 0xFF3F3F
SUCCESS = "\u2611"
WARNING = "\u26A0"
ERROR = "\u274C"
NOTES = "\uD83C\uDFB5"

ARROW_RIGHT = "\u25B6"
ARROW_LEFT = "\u25C0"
STOP = "\u23F9"


class Paginator:
    REACTIONS = (ARROW_RIGHT, ARROW_LEFT, STOP)

    def __init__(self, **kwargs):
        self.ctx = kwargs.pop("ctx")
        self.items = kwargs.pop("items")
        self.items_per_page = kwargs.pop("items_per_page", 10)
        self.color = kwargs.pop("color", COLOR)
        self.timeout = kwargs.pop("timeout", 60.0)
        self.page = kwargs.pop("page", 0)
        self.bot = self.ctx.bot
        self.msg = None

    @property
    def embed(self):
        lower_bound = self.page*self.items_per_page
        upper_bound = lower_bound+self.items_per_page
        to_display = self.items[lower_bound:upper_bound]
        desc = ""
        for i in to_display:
            desc += f"`{to_display.index(i)+lower_bound+1}.` {i}\n"
        embed = discord.Embed(color=self.color, description=desc)
        return embed

    @property
    def pages_needed(self):
        return math.ceil(len(self.items)/self.items_per_page)

    def check(self, reaction, user):
        return reaction.message.id == self.msg.id and user.id == self.ctx.author.id

    async def send_to_channel(self):
        while True:
            try:
                if self.msg:
                    await self.msg.edit(embed=self.embed)
                    if self.pages_needed < 2:
                        await self.msg.clear_reactions()
                        break
                else:
                    self.msg = await self.ctx.send(embed=self.embed)
                    if self.pages_needed < 2:
                        break
                    await self.msg.add_reaction(ARROW_LEFT)
                    await self.msg.add_reaction(STOP)
                    await self.msg.add_reaction(ARROW_RIGHT)

                try:
                    reaction, user = await self.bot.wait_for("reaction_add", check=self.check, timeout=self.timeout)
                except futures.TimeoutError:
                    await self.msg.clear_reactions()
                    break

                if reaction.emoji == ARROW_LEFT:
                    self.page -= 1
                    self.page %= self.pages_needed
                elif reaction.emoji == ARROW_RIGHT:
                    self.page += 1
                    self.page %= self.pages_needed
                elif reaction.emoji == STOP:
                    await self.msg.clear_reactions()
                    break

                await self.msg.remove_reaction(reaction.emoji, user)

            except discord.Forbidden:
                break
