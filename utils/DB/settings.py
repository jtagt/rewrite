from abc import ABC


class Settings(ABC):
    def __init__(self, id_):
        self._id = id_


class GuildSettings(Settings):
    def __init__(self, id, **kwargs):
        super().__init__(id)
        self.aliases = kwargs.get("aliases")
        self.prefix = kwargs.get("prefix", "NONE")
        self.autoplay = kwargs.get("autoplay", "NONE")
        self.textId = kwargs.get("textId", "NONE")
        self.voiceId = kwargs.get("voiceId", "NONE")
        self.djroleId = kwargs.get("djroleId", "NONE")
        self.volume = kwargs.get("volume", 100)
        self.repeat = kwargs.get("repeat", False)
        self.tms = kwargs.get("tms", True)


class BotSettings(Settings):
    def __init__(self, id, **kwargs):
        super().__init__(id)
        self.owners = kwargs.get("owners")
        self.prefix = kwargs.get("prefix")
        self.game = kwargs.get("game")
        self.autoplayPlaylist = kwargs.get("autoplayPlaylist")
        self.token = kwargs.get("token")
        self.geniusToken = kwargs.get("geniusToken")
        self.lavaNodes = kwargs.get("lavaNodes")
        self.contributors = kwargs.get("contributors")
        self.ballers = kwargs.get("ballers")
        self.sentryArgs = kwargs.get("sentryArgs")
        self.patrons = {**self.ballers, **self.contributors}
