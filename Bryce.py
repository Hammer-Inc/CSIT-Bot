import os

import discord

from commands import *

client = discord.Client()


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------\n\n')

    print("%-30s%-20s" % ("Connected Server", "Permission Status"))
    print("-" * 50)
    for server in client.servers:
        try:
            permissions = server.me.server_permissions
            if not (permissions.manage_nicknames and permissions.manage_roles and
                    permissions.attach_files and permissions.send_messages and permissions.read_messages):
                await client.send_message(server,
                                          "Warning: This server does not have the correct permissions set to run this bot!")
                print("%-30s%-20s" % (server, "Bad"))
            else:
                print("%-30s%-20s" % (server, "Good"))
        except discord.errors.DiscordException:
            print("%-30s%-20s" % (server, "Errored"))


MENTION_REGEX = "^<@!?{}>"


@client.event
async def on_message(message):
    await mention(message, client)


try:
    client.run(os.getenv('AUTH'), port=5012)
finally:
    print("Exiting")
    client.close()
