import os
import pathlib
from telethon import events
from telegraph import Telegraph, upload_file
from PIL import Image

# 📝 HELP
HELP = {
    "tg": """
📌 **Perintah:** `.tg [judul opsional]`
↪ Balas ke teks atau media untuk upload ke [Telegraph](https://telegra.ph)
"""
}

telegraph = Telegraph()
telegraph.create_account(short_name="bullovee_bot")


def init(client):
    @client.on(events.NewMessage(pattern=r"^\.tg(?: |$)(.*)"))
    async def handler_tg(event):
        reply = await event.get_reply_message()
        title = event.pattern_match.group(1).strip() or "Bullovee Telegraph"

        if not reply:
            return await event.reply("⚠️ Balas ke pesan atau file untuk diupload.")

        # 📝 Kalau teks
        if reply.text:
            try:
                page = telegraph.create_page(
                    title=title,
                    content=[reply.text.replace("\n", "<br>")]
                )
                url = page["url"]
                await event.reply(f"✅ Pasted ke Telegraph:\n👉 {url}")
            except Exception as e:
                await event.reply(f"❌ Gagal membuat halaman Telegraph:\n`{e}`")
            return

        # 📎 Kalau media/file
        try:
            file_path = await reply.download_media()
            if file_path.endswith(".webp"):
                png_path = file_path + ".png"
                Image.open(file_path).save(png_path)
                os.remove(file_path)
                file_path = png_path

            media_url = upload_file(file_path)[0]
            os.remove(file_path)
            await event.reply(f"✅ Uploaded ke Telegraph:\n👉 https://telegra.ph{media_url}")
        except Exception as e:
            await event.reply(f"❌ Gagal upload media:\n`{e}`")
