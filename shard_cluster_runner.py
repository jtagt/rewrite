#!/usr/bin/env python3
import asyncio
import base64
import logging
import multiprocessing as mp
import signal

import uvloop

from core.bot import Bot
from utils.DB import SettingsDB
from utils.magma.core import Lavalink, NodeException


def start_shard_cluster(cluster, **kwargs):
    logging.basicConfig(format="%(levelname)s -- %(name)s.%(funcName)s : %(message)s", level=logging.INFO)
    logging.getLogger("discord").setLevel(logging.ERROR)

    logging.getLogger("shard_controller")\
        .info(f"Starting shards: {cluster.shard_ids} in process: {mp.current_process().pid}")

    asyncio.get_event_loop().run_until_complete(cluster.start(**kwargs))


class ShardCluster:
    def __init__(self, shard_ids, controller):
        self.shard_ids = shard_ids
        self.controller = controller
        self.user_id = int(base64.b64decode(controller.bot_settings.token.split(".")[0]))
        self.shards = []

    async def get_lavalink(self):
        lavalink = Lavalink(self.user_id, self.controller.shard_count)  # global variable reference with user_id
        for (node, conf) in self.controller.bot_settings.lavaNodes.items():
            try:
                await lavalink.add_node(node, conf["uri"], conf["restUri"], conf["password"])
            except NodeException as e:
                logging.getLogger("shard_cluster").error(f"{node} - {e.args[0]}")
        return lavalink

    async def start(self, **kwargs):
        tasks = []
        lavalink = await self.get_lavalink()
        for shard_id in self.shard_ids:
            bot = Bot(self.controller.bot_settings, shard_id=shard_id, shard_count=self.controller.shard_count, lavalink=lavalink, **kwargs)
            self.shards.append(bot)
            tasks.append(bot.start(self.controller.bot_settings.token))
        await asyncio.gather(*tasks)


class ShardController:
    def __init__(self, bot_settings, shard_ids, shard_count):
        self.bot_settings = bot_settings
        self.shard_ids = shard_ids
        self.shard_count = shard_count

    def start_shards(self, manager, shards_p_cluster=3):
        logging.getLogger("shard_controller").info(f"Starting shards in parent process: {mp.current_process().pid}")

        shard_stats = manager.dict()
        command_queues = manager.dict()

        clusters = [ShardCluster(self.shard_ids[i:i+shards_p_cluster], self) for i in range(0, self.shard_count, shards_p_cluster)]
        for cluster in clusters:
            proc = mp.Process(target=start_shard_cluster, args=(cluster,),
                              kwargs={"shard_stats": shard_stats, "command_queues": command_queues})
            proc.start()
            proc.join(5)
        signal.pause()


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()


def main():
    logging.basicConfig(format="%(levelname)s -- %(name)s.%(funcName)s : %(message)s", level=logging.INFO)
    mp.set_start_method("spawn")
    mp_manager = mp.Manager()

    db = SettingsDB.get_instance()
    bot_settings = loop.run_until_complete(db.get_bot_settings())
    shards = 1
    shard_controller = ShardController(bot_settings, (*range(shards),), shards)

    # start_shard_cluster(ShardCluster([0], shard_controller), shard_stats={}, command_queues={})
    shard_controller.start_shards(mp_manager)


if __name__ == "__main__":
    main()
