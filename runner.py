#!/usr/bin/env python3
import asyncio
import logging
import multiprocessing as mp
import signal

import uvloop

from core.bot import Bot
from utils.DB import SettingsDB
from utils.magma.core import node


def start_shard(controller, shard_stats, shard_id):
    logging.basicConfig(format="%(levelname)s -- %(name)s.%(funcName)s : %(message)s", level=logging.INFO)
    logging.getLogger("discord").setLevel(logging.ERROR)
    logging.getLogger("shard_controller").info(f"Starting shard: {shard_id} in process: {mp.current_process().pid}")

    bot = Bot(controller.bot_settings, shard_stats, shard_id=shard_id, shard_count=controller.shard_count)
    bot.run(controller.bot_settings.token)


class ShardController:
    def __init__(self, bot_settings, shard_ids, shard_count):
        self.bot_settings = bot_settings
        self.shard_ids = shard_ids
        self.shard_count = shard_count

    def start_shards(self, manager):
        logging.getLogger("shard_controller").info(f"Starting shards in parent process: {mp.current_process().pid}")

        shard_stats = manager.dict()
        for shard in self.shard_ids:
            proc = mp.Process(target=start_shard, args=(self, shard_stats, shard))
            proc.start()
            proc.join(5)
        signal.pause()


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()
node.tries = 1
node.timeout = 2


if __name__ == "__main__":
    logging.basicConfig(format="%(levelname)s -- %(name)s.%(funcName)s : %(message)s", level=logging.INFO)
    mp.set_start_method("spawn")
    mp_manager = mp.Manager()

    db = SettingsDB.get_instance()
    bot_settings = loop.run_until_complete(db.get_bot_settings())
    shards = 1#44

    shard_controller = ShardController(bot_settings, (*range(shards),), shards)
    shard_controller.start_shards(mp_manager)
