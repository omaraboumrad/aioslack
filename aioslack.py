import asyncio
import collections
import json

import aiohttp
import websockets


class SlackClient(object):

    def __init__(self, token):
        self.token = token
        self.loop = asyncio.get_event_loop()
        self.handlers = collections.defaultdict(list)

    def run(self):
        self.loop.run_until_complete(self.connect())

    async def connect(self):
        print('> Starting')
        print('> Handshaking')
        url = await self.rtm_start()
        print('> Connecting')
        async with websockets.connect(url) as websocket:
            print('> Initializing')
            await self.handler(websocket)

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
                    raise Exception('not success')
                else:
                    data = await resp.json()
                    if data['ok']:
                        return data['url']
                    else:
                        raise Exception('not ok')

    async def handler(self, websocket):
        while True:
            message = await websocket.recv()
            jsonified = json.loads(message)
            print(f'>>> Received {jsonified["type"]}')
            for handler in self.handlers[jsonified['type']]:
                task = self.loop.create_task(handler(jsonified))

    def register(self, event, callback):
        self.handlers[event].append(callback)

    def unregister(self, event, callback):
        self.handlers[event].remove(callback)
