import aioslack
import coloredlogs
import logging

token = open('token.txt', 'r').readline().strip()
client = aioslack.Client(token)

@client.on('*')
async def handle_all(event):
    logging.info('{}'.format(event))


def type_to_channel(channel_name):    
    async def exec():
        channel = await client.find_channel(channel_name)
        if channel:
            logging.info("Typing to channel {}...".format(channel['name']))
            return { "type" : "typing", "channel": channel["id"] }
    return exec

if __name__ == '__main__':
    client.send_forever(type_to_channel("general"))
    client.send_forever(type_to_channel("programming"))
    client.send_forever({"type" : "ping"})
    client.run()    
