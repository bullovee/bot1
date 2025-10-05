import re
from telethon import events
from telethon.tl.types import PeerChannel
HELP = {
    "getch": [
        ".getch <id/username> → Menampilkan informasi channel berdasarkan ID atau username.",
        ".getch (balas pesan) → Otomatis mendeteksi ID/username dari pesan yang direply dan menampilkan info channel."
    ]
}
def init(client):
    print("✅ Modul GETCH (.getch) dimuat...")

    @client.on(events.NewMessage(pattern=r"^\.getch(?: |$)(.*)"))
    async def handler_getch(event):
        arg = event.pattern_match.group(1).strip()

        # 📝 Mode 1: Langsung ketik .getch <id/username>
        if arg:
            await process_getch(client, event, arg)
            return

        # 📝 Mode 2: Reply ke pesan yang mengandung ID / username
        if event.is_reply:
            reply_msg = await event.get_reply_message()
            text = reply_msg.text or ""

            # Cari ID di teks (bisa -100 atau angka biasa)
            match = re.search(r"(-100\d{5,}|\d{5,})", text)
            if match:
                channel_id_str = match.group(1)
                if channel_id_str.startswith("-100"):
                    channel_id_str = channel_id_str.replace("-100", "")
                await process_getch(client, event, channel_id_str)
                return

            # Cari username @xxxx
            match_username = re.search(r"@([A-Za-z0-9_]+)", text)
            if match_username:
                await process_getch(client, event, f"@{match_username.group(1)}")
                return

        # ❌ Kalau semua gagal
        await event.reply("⚠️ Berikan ID / username channel, atau reply pesan yang berisi ID.")

async def process_getch(client, event, target):
    try:
        # Jika target adalah angka → convert ke PeerChannel
        if target.isdigit():
            entity = await client.get_entity(PeerChannel(int(target)))
        else:
            entity = await client.get_entity(target)

        title = getattr(entity, 'title', '(Tidak ada judul)')
        username = getattr(entity, 'username', None)
        link = f"https://t.me/{username}" if username else "(tidak ada link)"

        info_text = (
            f"📌 **Channel Info**\n"
            f"───────────────\n"
            f"🆔 ID: `{entity.id}`\n"
            f"🏷 Title: {title}\n"
            f"🔗 Username: @{username}" if username else f"🔗 Username: (None)"
        )

        # Tambah link jika ada
        if username:
            info_text += f"\n🌐 Link: {link}"

        await event.reply(info_text)

    except Exception as e:
        await event.reply(f"❌ Gagal mengambil data channel:\n`{e}`")
