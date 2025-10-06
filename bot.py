import os
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from perintah import init as load_perintah
from perintah.addbot import load_token

# 🧠 Tambahan untuk rekap
from perintah.buat import load_rekap_from_channel  # ✅ hanya tambahan ini

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("SESSION")

logging.info("🔍 Cek token dari .addbot ...")
BOT_TOKEN = load_token()

if BOT_TOKEN:
    logging.info("🤖 Bullove BOT starting...")
    client = TelegramClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
else:
    logging.info("🤖 Bullove Userbot starting...")
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)


# 🧠 OWNER_ID global
OWNER_ID = None


# 🔐 FILTER GLOBAL — hanya OWNER yang boleh pakai command (. /)
@client.on(events.NewMessage(incoming=True))
async def global_owner_filter(event):
    global OWNER_ID
    # Abaikan pesan dari bot sendiri (outgoing)
    if event.out:
        return

    # Kalau OWNER_ID belum diset, abaikan filter (biar proses init jalan)
    if OWNER_ID is None:
        return

    # Jika bukan owner dan teks diawali . atau /
    if event.sender_id != OWNER_ID and event.raw_text.startswith(('.', '/')):
        raise events.StopPropagation


async def main():
    from tools import get_owner_id, check_mode

    try:
        logging.info("🔍 Mendapatkan owner id ...")
        owner_id, owner_name = await get_owner_id(client)
        # Set OWNER_ID global
        global OWNER_ID
        OWNER_ID = owner_id
        logging.info(f"ℹ️ OWNER_ID otomatis diset ke: {owner_id} ({owner_name})")
    except Exception as e:
        logging.error(f"❌ Gagal mendapatkan owner id: {e}", exc_info=True)

    try:
        mode = check_mode(client)
        logging.info(f"🔧 Mode berjalan: {mode}")
    except Exception as e:
        logging.error(f"❌ Gagal cek mode: {e}", exc_info=True)

    # 📝 Tambahan: Load rekap.json dari channel pribadi saat startup
    try:
        await load_rekap_from_channel(client)   # ✅ hanya tambahan ini
        logging.info("📥 rekap.json berhasil dimuat dari channel pribadi (jika ada)")
    except Exception as e:
        logging.warning(f"⚠️ Gagal load rekap.json dari channel pribadi: {e}")

    # Load semua perintah via __init__.py
    logging.info("📂 Mulai load perintah...")
    await load_perintah(client)   # ✅ harus pakai await

    logging.info("🚀 Semua modul berhasil dimuat, menunggu event ...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
