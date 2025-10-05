import sys
import os
import json
from telethon import events

HELP = {
    "utility": [
        ".restart → restart bot",
    ]
}

OWNER_ID = None
RESTART_FILE = "restart_data.json"


# ✅ Dijalankan saat modul dimuat
async def init_owner(client):
    global OWNER_ID
    me = await client.get_me()
    OWNER_ID = me.id

    # Cek apakah bot baru selesai restart
    if os.path.exists(RESTART_FILE):
        try:
            with open(RESTART_FILE, "r") as f:
                data = json.load(f)
            chat_id = data.get("chat_id")
            message_id = data.get("message_id")

            # Edit pesan lama menjadi sukses
            if chat_id and message_id:
                await client.edit_message(chat_id, message_id, "✅ Bot berhasil direstart!")
            os.remove(RESTART_FILE)
        except Exception as e:
            print(f"⚠️ Gagal update pesan restart: {e}")


def register(client):
    @client.on(events.NewMessage(pattern=r"^\.restart$"))
    async def handler_restart(event):
        if event.sender_id != OWNER_ID:
            return

        # Kirim pesan loading restart
        msg = await event.edit("♻️ Bot sedang restart...")

        # Simpan data ke file supaya bisa diedit setelah hidup lagi
        with open(RESTART_FILE, "w") as f:
            json.dump({"chat_id": event.chat_id, "message_id": msg.id}, f)

        # Restart proses
        args = [sys.executable] + sys.argv
        os.execv(sys.executable, args)
