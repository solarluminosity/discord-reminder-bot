import os
import asyncio
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

import discord

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# Через сколько удалять сообщения бота
# 1800 секунд = 30 минут
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

        # ВАЖНО:
        # Даём небольшое окно после старта, чтобы бот успел отправить сообщение
        # если цикл сработал не ровно в 21:00:00, а, например, в 21:00:15.
        if dt < now - timedelta(minutes=2):
            dt += timedelta(days=1)

        return dt

    days = (weekday - now.weekday()) % 7

    dt = datetime.combine(
        now.date() + timedelta(days=days),
        time(hour, minute),
        tzinfo=MSK
    )

    # Тоже оставляем окно после старта
    if dt < now - timedelta(minutes=2):
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


async def delete_later(msg):
    await asyncio.sleep(DELETE_AFTER)

    try:
        await msg.delete()
    except discord.NotFound:
        pass
    except discord.Forbidden:
        print("Нет прав на удаление сообщений.")
    except discord.HTTPException as e:
        print(f"Ошибка при удалении сообщения: {e}")


async def send_and_schedule_delete(channel, text):
    msg = await channel.send(
        text,
        allowed_mentions=discord.AllowedMentions(everyone=True)
    )

    # ВАЖНО:
    # Удаление запускается отдельной задачей.
    # Теперь бот НЕ засыпает на 30 минут и продолжает проверять ивенты.
    asyncio.create_task(delete_later(msg))


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

            key = f"{name}-{event_time.isoformat()}"

            diff = (event_time - now).total_seconds()

            # Напоминание за 30 минут
            # Окно сделано шире, чтобы бот не пропускал уведомление из-за задержки цикла.
            if 1740 <= diff <= 1800 and key not in sent_30:
                sent_30.add(key)

                await send_and_schedule_delete(
                    channel,
                    f"@everyone 🔔 Через 30 минут начнётся **{name}**!"
                )

            # Напоминание в момент старта
            # Теперь работает даже если бот проверил не ровно в 21:00:00,
            # а чуть позже, например в 21:00:15 или 21:00:40.
            if -60 <= diff <= 30 and key not in sent_start:
                sent_start.add(key)

                await send_and_schedule_delete(
                    channel,
                    f"@everyone 🚨 **{name}** начинается прямо сейчас!"
                )

        await asyncio.sleep(15)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    if not hasattr(client, "reminder_task"):
        client.reminder_task = asyncio.create_task(reminder_loop())


client.run(TOKEN)
