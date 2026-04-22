import os
import asyncio
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

import discord

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
DELETE_AFTER = int(os.getenv("DELETE_AFTER_SECONDS", "1800"))

MSK = ZoneInfo("Europe/Moscow")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

def get_events(now):
    events = []

    # Гильд пати ежедневно 21:00
    events.append(("Гильд пати", next_time(now, None, 21, 0)))

    # Арена Пн (0) Вт (1)
    events.append(("Арена", next_time(now, 0, 21, 0)))
    events.append(("Арена", next_time(now, 1, 21, 0)))

    # Брейкинг армия Ср (2) Пт (4)
    events.append(("Брейкинг арми", next_time(now, 2, 20, 0)))
    events.append(("Брейкинг арми", next_time(now, 4, 20, 0)))

    return events

def next_time(now, weekday, hour, minute):
    if weekday is None:
        dt = datetime.combine(now.date(), time(hour, minute), tzinfo=MSK)
        if dt <= now:
            dt += timedelta(days=1)
        return dt

    days = (weekday - now.weekday()) % 7
    dt = datetime.combine(now.date() + timedelta(days=days), time(hour, minute), tzinfo=MSK)
    if dt <= now:
        dt += timedelta(days=7)
    return dt

async def send_and_delete(channel, text):
    msg = await channel.send(text)
    await asyncio.sleep(DELETE_AFTER)
    await msg.delete()

async def loop():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    sent_30 = set()
    sent_start = set()

    while not client.is_closed():
        now = datetime.now(MSK)

        for name, event_time in get_events(now):
            key = f"{name}-{event_time}"

            diff = (event_time - now).total_seconds()

            # за 30 минут
            if 1700 < diff < 1800 and key not in sent_30:
                sent_30.add(key)
                await send_and_delete(channel, f"@everyone 🔔 Через 30 минут начнётся {name}!")

            # старт
            if 0 < diff < 60 and key not in sent_start:
                sent_start.add(key)
                await send_and_delete(channel, f"@everyone 🚨 {name} начинается прямо сейчас!")

        await asyncio.sleep(30)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    client.loop.create_task(loop())

client.run(TOKEN)
