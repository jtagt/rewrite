#!/usr/bin/env python3
import asyncio
import base64
import logging
import multiprocessing as mp
import sys

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
    def __init__(self, shard_ids, controller, start_delay=5):
        self.shard_ids = shard_ids
        self.controller = controller
        self.user_id = int(base64.b64decode(controller.bot_settings.token.split(".")[0]))
        self.shards = []
        self.start_delay = start_delay

    async def get_lavalink(self):
        lavalink = Lavalink(self.user_id, self.controller.shard_count)  # global variable reference with user_id
        for (node, conf) in self.controller.bot_settings.lavaNodes.items():
            try:
                await lavalink.add_node(node, conf["uri"], conf["restUri"], conf["password"])
            except NodeException as e:
                logging.getLogger("shard_cluster").error(f"{node} - {e.args[0]}")
        return lavalink

    async def start(self, **kwargs):
        async def _delayed_start(shard):
            await shard.start(self.controller.bot_settings.token)
            await asyncio.sleep(self.start_delay)

        tasks = []
        lavalink = None  # await self.get_lavalink()
        for shard_id in self.shard_ids:
            bot = Bot(self.controller.bot_settings,
                      shard_id=shard_id,
                      shard_count=self.controller.shard_count,
                      lavalink=lavalink,
                      shard_cluster=self,
                      **kwargs)
            self.shards.append(bot)
            tasks.append(_delayed_start(bot))
        await asyncio.gather(*tasks)


class ShardController:
    def __init__(self, bot_settings, shard_ids, shard_count, start_delay=5, shard_p_cluster=4):
        self.bot_settings = bot_settings
        self.shard_ids = shard_ids
        self.shard_count = shard_count
        self.cluster_processes = {}
        self.clusters = {}
        self.start_delay = start_delay
        self.shard_p_cluster = shard_p_cluster
        self.commands = {
            "shutdown": self.shutdown_cluster,
            "restart": self.restart_cluster,
            "restart_all": self.restart_all
        }

    def shutdown_cluster(self, **kwargs):
        to_shutdown = kwargs.pop("cluster")
        process = self.cluster_processes[to_shutdown]
        logging.getLogger("shard_controller").info(f"Stopping cluster: {to_shutdown} with {process.pid}")
        process.terminate()

    def start_cluster(self, **kwargs):
        to_start = kwargs.pop("cluster")
        cluster = self.clusters[to_start]
        proc = mp.Process(target=start_shard_cluster, args=(cluster,),
                          kwargs=kwargs)
        self.cluster_processes[cluster] = proc
        logging.getLogger("shard_controller").info(f"Starting cluster: {to_start}")
        proc.start()
        proc.join(self.start_delay * self.shard_p_cluster)

    def restart_cluster(self, **kwargs):
        self.shutdown_cluster(**kwargs)
        self.start_cluster(**kwargs)

    def restart_all(self, **kwargs):
        for cluster in self.clusters.keys():
            self.restart_cluster(cluster=cluster, **kwargs)

    def start_shards(self, manager):
        logging.getLogger("shard_controller").info(f"Starting shards in parent process: {mp.current_process().pid}")

        shard_stats = manager.dict()
        command_queue = manager.Queue()
        clusters = [ShardCluster(self.shard_ids[i:i+self.shard_p_cluster], self, self.start_delay)
                    for i in range(0, self.shard_count, self.shard_p_cluster)]

        for cluster in clusters:
            proc = mp.Process(target=start_shard_cluster, args=(cluster,),
                              kwargs={"shard_stats": shard_stats, "command_queue": command_queue})
            self.cluster_processes[cluster.shard_ids[0]] = proc
            self.clusters[cluster.shard_ids[0]] = cluster
            proc.start()
            proc.join(self.start_delay*self.shard_p_cluster)

        while True:
            request = command_queue.get()
            logging.getLogger("shard_controller").info(f"Received command request: {request}")
            command = self.commands.get(request.get("action"))
            if not command:
                logging.getLogger("shard_controller").warning(f"Command request {request} is not a command!")
                continue

            command(shard_stats=shard_stats, command_queue=command_queue, **request)


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()


def main():
    logging.basicConfig(format="%(levelname)s -- %(name)s.%(funcName)s : %(message)s", level=logging.INFO)
    mp.set_start_method("spawn")
    mp_manager = mp.Manager()

    db = SettingsDB.get_instance()
    bot_settings = loop.run_until_complete(db.get_bot_settings())
    shards = int(sys.argv[1])
    shard_p_cluster = int(sys.argv[2])
    shard_controller = ShardController(bot_settings, (*range(shards),), shards, shard_p_cluster=shard_p_cluster)
    #start_shard_cluster(ShardCluster([37], shard_controller), shard_stats={}, command_queue=[], lockdown_coro=lockdown)
    shard_controller.start_shards(mp_manager)


if __name__ == "__main__":
    main()
