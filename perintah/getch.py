import re
from telethon import events
from telethon.tl.types import PeerChannel

def init(client):
    @client.on(events.NewMessage(pattern=r"^\.getch(?: |$)(.*)"))
    async def get_channel_info(event):
        input_value = event.pattern_match.group(1).strip()

        # 📌 Jika tidak ada input, cek apakah ini reply ke pesan
        if not input_value and event.is_reply:
            reply_msg = await event.get_reply_message()
            if reply_msg and reply_msg.text:
                text = reply_msg.text.strip()

                # 🧠 Cari pola ID channel dalam teks
                match = re.search(r"-?100\d{5,}", text)
                if match:
                    input_value = match.group(0).strip()

        if not input_value:
            await event.reply("⚠️ Berikan ID / username channel, atau reply pesan yang berisi ID.")
            return

        try:
            # 🧠 Deteksi apakah input angka (ID)
            if input_value.lstrip("-").isdigit():
                ch_id = int(input_value)
                if str(ch_id).startswith("-100"):
                    ch_id = int(str(ch_id).replace("-100", ""))

                entity = await client.get_entity(PeerChannel(ch_id))

            else:
                # Kalau input berupa username (@channel)
                entity = await client.get_entity(input_value)

            # 📝 Ambil info channel
            title = getattr(entity, "title", "❓ Tidak ada title")
            username = getattr(entity, "username", None)
            channel_id = entity.id
            link = f"https://t.me/{username}" if username else "❌ Tidak ada username publik"

            reply_msg = (
                f"📌 **Channel Info**\n"
                f"───────────────\n"
                f"🆔 **ID:** `{channel_id}`\n"
                f"🏷 **Title:** {title}\n"
                f"🔗 **Username:** @{username}" if username else f"🔗 **Username:** -"
            )
            reply_msg += f"\n🌐 **Link:** {link}"

            await event.reply(reply_msg)

        except Exception as e:
            await event.reply(f"❌ Gagal mengambil info channel:\n`{e}`")
