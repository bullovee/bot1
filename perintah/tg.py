import os
import traceback
from telethon import events
from telegraph import Telegraph, upload_file

# 📌 Inisialisasi Telegraph hanya sekali
telegraph = Telegraph()
telegraph.create_account(short_name="BulloveUserbot")

def register(client):
    @client.on(events.NewMessage(pattern=r"^\.tg(?: |$)(.*)"))
    async def tg_handler(event):
        if not event.is_reply:
            await event.reply("❌ Balas ke pesan teks atau media untuk diunggah ke Telegraph.")
            return

        reply = await event.get_reply_message()
        title = event.pattern_match.group(1).strip() or "Bullove Telegraph"

        # 📝 Upload Teks
        if reply.text and not reply.media:
            try:
                html_content = reply.text.replace("\n", "<br>")
                page = telegraph.create_page(
                    title=title,
                    author_name="Bullove Bot",
                    html_content=html_content
                )
                url = f"https://telegra.ph/{page['path']}"
                await event.reply(
                    f"📝 <b>Berhasil Upload Teks</b>\n🔗 <a href='{url}'>Klik di sini</a>",
                    link_preview=True
                )
            except Exception as e:
                tb = traceback.format_exc()
                await event.reply(f"❌ Gagal upload teks:\n<code>{e}</code>\n<pre>{tb}</pre>")
            return

        # 🖼️ Upload Media (foto/video/gif/sticker)
        if reply.media:
            try:
                file_path = await client.download_media(reply)
                if not file_path or not os.path.exists(file_path):
                    await event.reply("❌ Gagal download file media.")
                    return

                uploaded = upload_file(file_path)  # ✅ return list, ambil index [0]
                url = f"https://telegra.ph{uploaded[0]}"

                await event.reply(
                    f"📎 <b>Media berhasil diunggah</b>\n🔗 <a href='{url}'>Klik di sini</a>",
                    link_preview=True
                )

                os.remove(file_path)
            except Exception as e:
                tb = traceback.format_exc()
                await event.reply(f"❌ Gagal upload media:\n<code>{e}</code>\n<pre>{tb}</pre>")

# 🆘 Integrasi ke .help
HELP = {
    "Tg": [
        "• `.tg [judul opsional]` → Balas ke teks atau media untuk upload ke Telegraph.",
    ]
}
