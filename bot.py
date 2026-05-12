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


def next_time(now, weekday, hour, minute):
    """
    weekday:
    None = каждый день
    0 = понедельник
    1 = вторник
    2 = среда
    3 = четверг
    4 = пятница
    5 = суббота
    6 = воскресенье
    """

    if weekday is None:
        dt = datetime.combine(now.date(), time(hour, minute), tzinfo=MSK)
        if dt <= now:
            dt += timedelta(days=1)
        return dt

    days = (weekday - now.weekday()) % 7
    dt = datetime.combine(
        now.date() + timedelta(days=days),
        time(hour, minute),
        tzinfo=MSK
    )

    if dt <= now:
        dt += timedelta(days=7)

    return dt


def get_events(now):
    events = []

    # Гильд пати — ежедневно 21:00–21:30 МСК
    events.append({
        "name": "Гильд пати",
        "start": next_time(now, None, 21, 0),
        "end_text": "21:30 МСК"
    })

    # Арена — понедельник 21:00–22:00 МСК
    events.append({
        "name": "Арена",
        "start": next_time(now, 0, 21, 0),
        "end_text": "22:00 МСК"
    })

    # Арена — вторник 21:00–22:00 МСК
    events.append({
        "name": "Арена",
        "start": next_time(now, 1, 21, 0),
        "end_text": "22:00 МСК"
    })

    # Брейкинг арми — среда 20:00–22:00 МСК
    events.append({
        "name": "Брейкинг арми",
        "start": next_time(now, 2, 20, 0),
        "end_text": "22:00 МСК"
    })

    # Брейкинг арми — пятница 20:00–22:00 МСК
    events.append({
        "name": "Брейкинг арми",
        "start": next_time(now, 4, 20, 0),
        "end_text": "22:00 МСК"
    })

    return events


async def send_and_delete(channel, text):
    msg = await channel.send(text)

    await asyncio.sleep(DELETE_AFTER)

    try:
        await msg.delete()
    except discord.NotFound:
        pass
    except discord.Forbidden:
        print("Нет прав на удаление сообщений.")


async def reminder_loop():
    await client.wait_until_ready()

    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print("Канал не найден. Проверь CHANNEL_ID.")
        return

    sent_30 = set()
    sent_start = set()

    while not client.is_closed():
        now = datetime.now(MSK)

        for event in get_events(now):
            name = event["name"]
            event_time = event["start"]
            end_text = event["end_text"]

            key = f"{name}-{event_time.isoformat()}"

            diff = (event_time - now).total_seconds()

            # Напоминание за 30 минут
            if 1700 < diff < 1800 and key not in sent_30:
                sent_30.add(key)

                await send_and_delete(
                    channel,
                    f"@everyone 🔔 Через 30 минут начнётся **{name}**!\n"
                    f"Время: **{event_time.strftime('%H:%M')}–{end_text}**"
                )

            # Напоминание в момент старта
            if 0 < diff < 60 and key not in sent_start:
                sent_start.add(key)

                await send_and_delete(
                    channel,
                    f"@everyone 🚨 **{name}** начинается прямо сейчас!\n"
                    f"Время: **{event_time.strftime('%H:%M')}–{end_text}**"
                )

        await asyncio.sleep(30)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    client.loop.create_task(reminder_loop())


client.run(TOKEN)
