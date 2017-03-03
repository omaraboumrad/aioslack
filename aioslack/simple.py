import aioslack

token = open('token.txt', 'r').readline().strip()
client = aioslack.Client(token)


@client.on('message')
async def handle_message(event):
    if 'text' in event:
        print('{} said: {}'.format(
            event['user'],
            event['text']
        ))


# Captures all events.
# @client.on('*')
# async def handle_all(event):
#     pass


if __name__ == '__main__':
    client.run()
