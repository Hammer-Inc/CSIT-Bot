import json
import os
import time
import traceback
from functools import wraps

import requests
from discord import Message, Member


def ignore_bot_calls(fn):
    async def wrapper(message, client, *args, **kwargs):
        if message.author.bot:
            return
        return await fn(message, client, *args, **kwargs)

    return wrapper


def prevent_self_calls(fn):
    @wraps(fn)
    async def wrapper(message: Message, *args, **kwargs):
        if message.author.id == message.guild.me:
            return
        return await fn(message, *args, **kwargs)

    return wrapper


def log_access_admin(command):
    def decorator(fn):
        async def wrapper(message, client, *args, **kwargs):
            if not message.author.guild_permissions.administrator:
                await access_denied(command, message, client)
                return
            access_granted(command, message)
            return await fn(message, client, *args, **kwargs)

        return wrapper

    return decorator


def log_access(command):
    def decorator(fn):
        async def wrapper(message, *args, **kwargs):
            access_granted(command, message)
            return await fn(message, *args, **kwargs)

        return wrapper

    return decorator


async def access_denied(command, message, client):
    print("[DENIED] {} called by {} ('{}')".format(command, message.author, message.content))
    await client.send_message(message.channel,
                              "{} is not in the sudoers file (this incident will be reported)".format(
                                  message.author.mention))


def access_granted(command, message):
    print("{} called by {} ('{}')".format(command, message.author, message.content))


async def log_state(server):
    """
    Logs the current nickname state of the server and uploads it to the default channel.
    :param server: The discord server object
    :return: A state mapping or None if it was not safe to create a new state
    """
    if os.path.isfile(TEMP_PATH.format(server.id)):
        with open(TEMP_PATH.format(server.id), "r") as state_in:
            state = json.load(state_in)
    else:
        state = {}
    for member in server.members:
        if member.id not in state:
            if member.top_role < server.me.top_role:
                state[member.id] = member.nick
    if not state:
        return None, None
    with open(TEMP_PATH.format(server.id), "w+") as output:
        json.dump(state, output)
    return state, TEMP_PATH.format(server.id)


def archive(file_path):
    now = time.strftime("%y%m%d-%H%M%S")
    archive_path = "{p}_{time}.archive".format(p=file_path, time=now)
    os.rename(file_path, archive_path)


async def reset_state_from_local(server, client):
    """
    Consumes the state file and uses it to reset all server nicknames
    :param client:
    :param server: The discord server object
    :return: Whether the operation was a success
    """
    if not os.path.exists(TEMP_PATH.format(server.id)):
        return False
    state = {}
    with open(TEMP_PATH.format(server.id), "r") as state_in:
        state = json.load(state_in)

    await commit_state(state, server, client)
    archive(TEMP_PATH.format(server.id))
    return True


async def reset_state_from_remote(server, url, client):
    """
    Consumes a remote json attachment and uses it to reset all server nicknames
    :param url:
    :param client:
    :param server: The discord server object
    :return: Whether the operation was a success
    """
    request = requests.get(url)
    try:
        state = json.loads(request.content)
    except Exception:
        return False
    await commit_state(state, server, client)
    if os.path.exists(TEMP_PATH.format(server.id)):
        archive(TEMP_PATH.format(server.id))
    return True


async def commit_state(state, server, client):
    for user_id in state:
        try:
            member = server.get_member(user_id)  # type: Member
            if member is None:
                member = await server.fetch_member(user_id)

            print("SET: {}({}) > {}".format(member.nick or str(member), user_id, state[user_id]))
            if member.top_role <= server.me.top_role:
                if member.nick == state[user_id]:
                    continue
                await member.edit(reason="Mass nickname change command called", nick=state[user_id])
        except Exception:
            traceback.print_exc()


TEMP_PATH = "./state_{}.temp.json"
