import asyncio
import collections
import itertools
import json
import logging

import aiohttp
import coloredlogs
import websockets

logging.basicConfig(level=logging.INFO)
coloredlogs.install()

class Client(object):

    def __init__(self, token):
        self.token = token
        self.loop = asyncio.get_event_loop()
        self.handlers = collections.defaultdict(list)

    def run(self):
        self.loop.run_until_complete(self.connect())

    async def connect(self):
        logging.info('handshaking')
        url = await self.rtm_start()
        logging.info('connecting')
        async with websockets.connect(url) as websocket:
            logging.info('initializing')
            await self.consumer(websocket)

    async def rtm_start(self):
        headers = {'user-agent': 'slackclient/12 Python/3.6.0 Darwin/15.5.0'}
        data = {'token': self.token}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                    'https://slack.com/api/rtm.start',
                    headers=headers,
                    data=data) as resp:
                status = resp.status

                if status != 200:
                    logging.error(
                        f'rtm request was not successful [Code: {status}]')
                    raise Exception('not success')
                else:
                    data = await resp.json()
                    if data['ok']:
                        return data['url']
                    else:
                        raise Exception('not ok')

    async def consumer(self, websocket):
        while True:
            message = await websocket.recv()
            jsonified = json.loads(message)
            logging.info(f'received {jsonified["type"]}')
            for handler in itertools.chain(
                    self.handlers[jsonified['type']],
                    self.handlers['*']):
                task = asyncio.ensure_future(handler(jsonified))

    def on(self, event, **options):
        def _decorator(callback):
            self.handlers[event].append(callback)
            return callback
        return _decorator

    def unregister(self, event_type, callback):
        self.handlers[event].remove(callback)
