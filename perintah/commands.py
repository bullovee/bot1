import sys
import os
import time
import asyncio
import random
from datetime import datetime
from telethon import events
from telethon.tl.functions.channels import CreateChannelRequest
from telethon.tl.functions.messages import CreateChatRequest, ExportChatInviteRequest
from telethon.errors import FloodWaitError

# ✅ Import pesan random dari file terpisah
from .random_messages import RANDOM_MESSAGES
HELP = {
    "utility": [
        ".ping → cek respon bot",
        ".id → cek ID grup/channel",
        ".restart → restart bot",
    ]
}

OWNER_ID = None
buat_sessions = {}  # simpan sementara session untuk interaktif


# === OWNER INIT ===
async def init_owner(client):
    global OWNER_ID
    me = await client.get_me()
    OWNER_ID = me.id
    print(f"ℹ️ OWNER_ID otomatis diset ke: {OWNER_ID} ({me.username or me.first_name})")
    try:
        await client.send_message(OWNER_ID, "✅ Bot berhasil dijalankan dan siap dipakai.")
    except Exception:
        pass


# === HELPERS ===
def progress_bar(current, total, length=20):
    filled = int(length * current // total)
    bar = "█" * filled + "▒" * (length - filled)
    return f"[{bar}] {current}/{total}"


# === COMMANDS ===
def register_commands(client):

    # 📌 .ping
    @client.on(events.NewMessage(pattern=r"^\.ping$"))
    async def handler_ping(event):
        start = time.perf_counter()
        await event.edit("🏓 Pong...")
        end = time.perf_counter()
        ping_ms = int((end - start) * 1000)
        await event.edit(f"🏓 Pong!\n⏱ {ping_ms} ms")

    # 📌 .id (✅ fixed)
    @client.on(events.NewMessage(pattern=r"^\.id$"))
    async def handler_id(event):
        chat = await event.get_chat()
        chat_id = chat.id
        if not str(chat_id).startswith("-100") and (event.is_group or event.is_channel):
            chat_id = f"-100{abs(chat_id)}"

        # ✅ Pastikan cuma edit kalau pesannya dikirim oleh bot/userbot sendiri
        if event.out:
            await event.edit(f"🆔 Chat ID: {chat_id}")
        else:
            await event.reply(f"🆔 Chat ID: {chat_id}")


# Panggil fungsi ini di bot.py setelah client dibuat
def init(client):
    register_commands(client)
