import os
from telethon import events
from telegraph import Telegraph, upload_file

# Inisialisasi Telegraph
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

        # 📝 Upload teks polos
        if reply.message and not reply.media:
            try:
                content = reply.message
                result = telegraph.create_page(
                    title=title,
                    author_name="Bullove Bot",
                    html_content=content
                )
                url = f"https://telegra.ph/{result['path']}"
                await event.reply(f"📝 Berhasil upload teks\n🔗 {url}", link_preview=True)
            except Exception as e:
                await event.reply(f"❌ Gagal upload teks:\n<code>{e}</code>")
            return

        # 🖼️ Upload media
        if reply.media:
            try:
                file_path = await client.download_media(reply, file="./")
                uploaded = upload_file(file_path)  # return list path
                src = uploaded[0]
                url = f"https://telegra.ph{src}"
                await event.reply(f"📎 Media berhasil diunggah\n🔗 {url}", link_preview=True)
                os.remove(file_path)
            except Exception as e:
                await event.reply(f"❌ Gagal upload media:\n<code>{e}</code>")

# 🆘 Help untuk .tg
HELP = {
    "Tg": [
        "• `.tg [judul opsional]` → Balas ke teks atau media untuk upload ke Telegraph.",
    ]
}
