from aioslack import SlackClient


async def handle_presence(event):
    print(event)


if __name__ == '__main__':
    token = 'use your slack token here'
    client = SlackClient(token)
    client.register('presence_change', handle_presence)
    client.run()
