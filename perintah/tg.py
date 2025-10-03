import os
import aiohttp
from telethon import events
from telegraph import upload_file, Telegraph

# Inisialisasi Telegraph
telegraph = Telegraph()
telegraph.create_account(short_name="userbot")

def register(client):
    @client.on(events.NewMessage(pattern=r"^\.tg(?: |$)(.*)"))
    async def tg_handler(event):
        if not event.is_reply:
            await event.reply("❌ Balas ke pesan teks atau media untuk diunggah ke Telegraph.")
            return

        reply_msg = await event.get_reply_message()
        title = event.pattern_match.group(1).strip() or "Bullove Telegraph"

        # 📝 Upload teks
        if reply_msg.message and not reply_msg.media:
            try:
                html_content = f"<pre>{reply_msg.message}</pre>"
                response = telegraph.create_page(title, html_content=html_content)
                url = f"https://telegra.ph/{response['path']}"
                await event.reply(f"📝 <b>Berhasil Upload Teks</b>\n🔗 <a href='{url}'>Klik di sini</a>", link_preview=True)
            except Exception as e:
                await event.reply(f"❌ Gagal upload teks:\n<code>{e}</code>")
            return

        # 🖼️ Upload media
        if reply_msg.media:
            try:
                file_path = await client.download_media(reply_msg, file="./")
                uploaded = upload_file(file_path)
                url = f"https://telegra.ph{uploaded[0]}"
                await event.reply(f"📎 <b>Media berhasil diunggah</b>\n🔗 <a href='{url}'>Klik di sini</a>", link_preview=True)
                os.remove(file_path)
            except Exception as e:
                await event.reply(f"❌ Gagal upload media:\n<code>{e}</code>")
            return

# 🆘 HELP agar muncul di .help
HELP = {
    "Tg": [
        "• `.tg [judul opsional]` → Balas ke teks atau media untuk upload ke Telegraph."
    ]
}
