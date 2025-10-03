import os
import pathlib
from telegraph import Telegraph, upload_file
from PIL import Image
from pyrogram import Client, filters

# 📝 Menu help untuk .tg
HELP = {
    "tg": """
📌 **Perintah:** `.tg [judul opsional]`
↪ Balas ke teks atau media untuk upload ke [Telegraph](https://telegra.ph)

✨ **Contoh Penggunaan:**
- Balas teks ➡️ `.tg JudulSaya`
- Balas file / gambar ➡️ `.tg`
- Balas sticker / animasi ➡️ `.tg Stickerku`
"""
}

# 🧭 Inisialisasi Telegraph
telegraph = Telegraph()
telegraph.create_account(short_name="bullovee_bot")


def init(client: Client):
    @client.on_message(filters.command("tg", prefixes=".") & filters.me)
    async def tg_handler(c: Client, m):
        reply = m.reply_to_message
        title = "Bullovee Telegraph"
        if len(m.command) > 1:
            title = " ".join(m.command[1:])

        if not reply:
            return await m.reply("⚠️ Balas ke pesan atau file untuk diupload.")

        # 📝 Kalau teks
        if reply.text:
            try:
                page = telegraph.create_page(
                    title=title,
                    content=[reply.text.html.replace("\n", "<br>")]
                )
                url = page["url"]
                await m.reply(f"✅ Pasted ke Telegraph:\n👉 {url}")
            except Exception as e:
                await m.reply(f"❌ Gagal membuat halaman Telegraph:\n`{e}`")
            return

        # 📎 Kalau file/media
        try:
            file_path = await reply.download()
            # Kalau sticker (webp), convert ke png dulu
            if file_path.endswith(".webp"):
                png_path = file_path + ".png"
                Image.open(file_path).save(png_path)
                os.remove(file_path)
                file_path = png_path

            media_url = upload_file(file_path)[0]
            os.remove(file_path)
            await m.reply(f"✅ Uploaded ke Telegraph:\n👉 https://telegra.ph{media_url}")
        except Exception as e:
            await m.reply(f"❌ Gagal upload media:\n`{e}`")
