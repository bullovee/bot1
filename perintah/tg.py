import os
from telethon import events
from telegraph import Telegraph, upload_file

# Inisialisasi Telegraph sekali saja
telegraph = Telegraph()
telegraph.create_account(short_name="userbot")

def register(client):
    @client.on(events.NewMessage(pattern=r"^\.tg(?: |$)(.*)"))
    async def tg_handler(event):
        if not event.is_reply:
            await event.reply("❌ Balas ke pesan teks atau media untuk diunggah ke Telegraph.")
            return

        reply = await event.get_reply_message()
        title = event.pattern_match.group(1).strip() or "Bullove Telegraph"

        # 📝 Upload teks
        if reply.message and not reply.media:
            try:
                content = f"<pre>{reply.message}</pre>"
                result = telegraph.create_page(
                    title=title,
                    author_name="Bullove Bot",
                    html_content=content
                )
                url = f"https://telegra.ph/{result['path']}"
                await event.reply(f"📝 <b>Berhasil Upload Teks</b>\n🔗 <a href='{url}'>Klik di sini</a>", link_preview=True)
            except Exception as e:
                await event.reply(f"❌ Gagal upload teks:\n<code>{e}</code>")
            return

        # 🖼️ Upload media
        if reply.media:
            try:
                file_path = await client.download_media(reply, file="./")
                uploaded = upload_file(file_path)  # ← ini return list, bukan dict
                url = f"https://telegra.ph{uploaded[0]}"
                await event.reply(f"📎 <b>Media berhasil diunggah</b>\n🔗 <a href='{url}'>Klik di sini</a>", link_preview=True)
                os.remove(file_path)
            except Exception as e:
                await event.reply(f"❌ Gagal upload media:\n<code>{e}</code>")

# 🆘 HELP untuk perintah ini
HELP = {
    "Tg": [
        "• `.tg [judul opsional]` → Balas ke teks atau media untuk upload ke Telegraph."
    ]
}
