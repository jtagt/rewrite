import aiohttp
import bs4 as bs4
import discord
from discord.ext import commands

from .exceptions import CustomCheckFailure
from .visual import Paginator


def is_owner():
    def predicate(ctx):
        if ctx.message.author.id not in ctx.bot.bot_settings.owners:
            raise CustomCheckFailure("Not for you :PP")
        return True
    return commands.check(predicate)


def split_str(string, split_at=2000):
    splitted = []
    if string:
        splitted = [string[i:i + split_at] for i in range(0, len(string), split_at)]
    return splitted


def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip('` \n')


def get_syntax_error(e):
    if e.text is None:
        return '```py\n{0.__class__.__name__}: {0}\n```'.format(e)
    return '```py\n{0.text}{1:>{0.offset}}\n{2}: {0}```'.format(e, '^', type(e).__name__)


async def get_lyrics(query, token):
    url = "https://api.genius.com/search"
    params = {"q": query, "page": 1}
    headers = {"Authorization": f"Bearer {token}"}

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, params=params) as response:
            data = await response.json()
            results = data["response"]["hits"]

        if len(results) < 1:
            return {"error": f"No results found for \"{query}\""}

        result = results[0]["result"]
        response = await session.get(result["url"])
        bs = bs4.BeautifulSoup(await response.text(), "html.parser")

    for script_tag in bs.find_all("script"):
        script_tag.extract()

    lyrics = bs.find("div", class_="lyrics").get_text()

    return {
        "title": result["title"],
        "url": result["url"],
        "path": result["path"],
        "thumbnail": result.get("thumbnail"),
        "header_image_url": result["song_art_image_thumbnail_url"],
        "primary_artist": result["primary_artist"],
        "lyrics": lyrics
    }


class LyricsPaginator(Paginator):
    def __init__(self, ctx, lyrics_data):
        super().__init__(ctx=ctx, items=split_str(lyrics_data["lyrics"]), items_per_page=1)
        self.lyrics_data = lyrics_data

    @property
    def embed(self):
        lower_bound = self.page*self.items_per_page
        upper_bound = lower_bound+self.items_per_page
        to_display = self.items[lower_bound:upper_bound]
        desc = ""
        for content in to_display:
            desc += content
        embed = discord.Embed(color=self.color,
                              description=desc, )
        embed.set_author(name=f"{self.lyrics_data['primary_artist']['name']} - {self.lyrics_data['title']}",
                         icon_url=self.lyrics_data["header_image_url"],
                         url=self.lyrics_data["url"])
        embed.set_footer(text=f"Page: {self.page+1}/{self.pages_needed}")
        return embed

