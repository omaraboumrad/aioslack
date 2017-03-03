import asyncio
import types
import collections
import itertools
import json
import logging

import aiohttp
import coloredlogs
import websockets
import time
import uuid

from functools import singledispatch

logging.basicConfig(level=logging.INFO)
coloredlogs.install()


class Client(object):
    PRODUCER_DELAY = 0.5
    BASE_URL = "https://slack.com/api"

    def __init__(self, token):
        self.token = token
        self.loop = asyncio.get_event_loop()
        self.handlers = collections.defaultdict(list)
        self.requests = []
        self.producers = itertools.cycle(self.requests)
        self.channels = []
        self.users = []

    def run(self):
        self.loop.run_until_complete(self.start_ws_connection())

    def on(self, event, **options):
        def _decorator(callback):
            self.handlers[event].append(callback)
            return callback
        return _decorator

    def unregister(self, event_type, callback):
        self.handlers[event_type].remove(callback)

    def send_forever(self, request):
        self.requests.append(request)

    async def find_channel(self, channel_name):
        if self.channels:
            for channel in self.channels:
                if channel['name'] == channel_name:
                    return channel
        else:
            self.channels = await self.get(
                "channels.list",
                callback=lambda response: response['channels'])
            return self.find_channel(channel_name)

    async def find_user(self, user_name):
        if self.users:
            for user in self.users:
                if user['name'] == user_name:
                    return user
        else:
            self.users = await self.get(
                "users.list",
                callback=lambda response: response['users'])
            return self.find_user(user_name)

    async def get(self, path, extraParams={}, extraHeaders={}, callback=None):
        async def get_request(session, headers, params):
            async with session.get(
                    '{}/{}'.format(Client.BASE_URL, path),
                    headers=headers,
                    params=params) as resp:
                return await self.handle_http_response(resp, path, callback)
        return await self.make_http_request(
            get_request, extraParams, extraHeaders)

    async def post(self, path, extraData={}, extraHeaders={}, callback=None):
        async def post_request(session, headers, data):
            async with session.post(
                    '{}/{}'.format(Client.BASE_URL, path),
                    headers=headers,
                    data=data) as resp:
                return await self.handle_http_response(resp, path, callback)
        return await self.make_http_request(
            post_request, extraData, extraHeaders)

    async def start_ws_connection(self):
        def retrieve(data):
            return (data["url"], data["channels"], data["users"])

        logging.info('handshaking')
        url, channels, users = await self.post("rtm.start", callback=retrieve)
        self.channels = channels
        self.users = users
        logging.info('connecting')
        async with websockets.connect(url) as websocket:
            logging.info('initializing')
            await self.ws_server_loop(websocket)

    async def make_http_request(self, request, extraData={}, extraHeaders={}):
        headers = {
            'user-agent': 'slackclient/12 Python/3.6.0 Darwin/15.5.0',
            **extraHeaders}
        data = {'token': self.token, **extraData}

        async with aiohttp.ClientSession() as session:
            return await request(session, headers, data)

    async def handle_http_response(self, resp, req_name, callback=None):
        status = resp.status
        if status != 200:
            logging.error('{} request was not successful [Code: {}]'.format(
                req_name, status))
            raise Exception('not success')
        else:
            data = await resp.json()
            if data['ok']:
                if callback:
                    return callback(data)
                return data
            else:
                raise Exception('not ok')

    async def ws_server_loop(self, websocket):
        while True:
            listener_task = asyncio.ensure_future(websocket.recv())
            producer_task = asyncio.ensure_future(self.producer())
            done, pending = await asyncio.wait(
                [listener_task, producer_task],
                return_when=asyncio.FIRST_COMPLETED)
            if listener_task in done:
                message = listener_task.result()
                await self.consumer(message)

            if producer_task in done:
                message = producer_task.result()
                if message:
                    await websocket.send(message)

    async def consumer(self, message):
        jsonified = json.loads(message)
        logging.info('received {}'.format(jsonified["type"]))
        for handler in itertools.chain(
                self.handlers[jsonified['type']],
                self.handlers['*']):
            asyncio.ensure_future(handler(jsonified))

    async def producer(self):
        if self.requests:
            time.sleep(Client.PRODUCER_DELAY)
            data = await Client.retrieve_data(self.producers.__next__())
            if data:
                return json.dumps({"id": uuid.uuid4().int, **data})

    @singledispatch
    async def retrieve_data(producer):
        logging.warn("Unknown producer type. Skipping...")

    @retrieve_data.register(dict)
    async def _(producer):
        return producer

    @retrieve_data.register(types.FunctionType)
    async def _(producer):
        return await producer()
