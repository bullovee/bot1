# © 2025 - Buatan khusus untuk Bullovee Bot
# Modul: Telegraph Uploader

HELP = {
    "telegraph": [
        "📌 **Perintah:** `.telegraph [judul opsional]` atau `.tg`\n"
        "↪ Balas ke teks atau media untuk mengupload ke [Telegraph](https://telegra.ph)\n\n"
        "✨ **Contoh:**\n"
        "- Balas teks ➡️ `.telegraph JudulSaya`\n"
        "- Balas file / gambar ➡️ `.telegraph`\n"
        "- Balas sticker / animasi ➡️ `.telegraph Stickerku`"
    ]
}

import os
import pathlib
from PIL import Image
from telegraph import Telegraph
from telethon import events

# Inisialisasi Telegraph
telegraph = Telegraph()
if not telegraph.get_access_token():
    telegraph.create_account(short_name="bullovee_bot")


def register(client):
    @client.on(events.NewMessage(pattern=r"^\.tg( (.*)|$)"))
    @client.on(events.NewMessage(pattern=r"^\.telegraph( (.*)|$)"))
    async def telegraphcmd(event):
        """
        Upload media atau text ke Telegraph
        Gunakan: reply ke pesan / file → ketik .telegraph [judul opsional]
        """
        match = (event.pattern_match.group(1) or "").strip() or "Bullovee Telegraph"
        reply = await event.get_reply_message()

        if not reply:
            return await event.reply("⚠️ Balas ke pesan atau file untuk diupload.")

        # Jika text biasa
        if not reply.media and reply.message:
            content = reply.message
            page = telegraph.create_page(
                title=match,
                content=[content],
            )
            return await event.reply(
                f"✅ Pasted ke Telegraph: [Klik Disini]({page['url']})", link_preview=False
            )

        # Jika media
        file_path = await reply.download_media()
        try:
            # Konversi sticker webp ke png
            if file_path.endswith(".webp"):
                png_path = f"{file_path}.png"
                Image.open(file_path).save(png_path)
                os.remove(file_path)
                file_path = png_path

            # Konversi animated sticker .tgs ke gif (jika tersedia)
            if file_path.endswith(".tgs"):
                gif_path = f"{file_path}.gif"
                os.system(f"lottie_convert.py '{file_path}' '{gif_path}'")
                os.remove(file_path)
                file_path = gif_path

            # Upload ke Telegraph
            from telegraph.upload import upload_file
            url = upload_file(file_path)[0]
            await event.reply(f"✅ Uploaded ke [Telegraph](https://telegra.ph{url})")

        except Exception as e:
            await event.reply(f"❌ Terjadi error: {e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
