from dotenv import load_dotenv

import os
import asyncio
import discord

load_dotenv()
TOKEN = os.environ["DISCORD_BOT_TOKEN"]
DEFAULT_USER_ID = int(os.environ["DISCORD_ALERT_USER_ID"])


async def _send_dm(user_id, message):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    ready = asyncio.Event()

    @client.event
    async def on_ready():
        ready.set()

    async def _runner():
        asyncio.get_running_loop().create_task(client.start(TOKEN))
        await ready.wait()
        user = await client.fetch_user(user_id)
        await user.send(message)
        await client.close()

    await _runner()


def send_discord_alert(tx_hash, user_id=None, prefix=None):
    uid = user_id or DEFAULT_USER_ID
    msg_prefix = prefix or "🔒 취약점 감지"
    message = (
        f"{msg_prefix}\n"
        f"트랜잭션 해시: `{tx_hash}`에서 취약점이 발견되었습니다.\n"
        f"즉시 확인이 필요합니다."
    )

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_send_dm(uid, message))
    else:
        return loop.create_task(_send_dm(uid, message))
