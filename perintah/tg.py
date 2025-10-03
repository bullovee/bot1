# perintah/tg.py
# 📌 Modul Telegraph (.tg) — FIX FINAL
from telethon import events
from telegraph import Telegraph, upload_file
from PIL import Image
import os

# Buat akun Telegraph sekali saja
telegraph = Telegraph()
telegraph.create_account(short_name="bullovee_bot")

HELP = {
    "Tg": """
📌 **Perintah:** `.tg [judul opsional]`
↪ Balas ke teks atau media untuk upload ke [Telegraph](https://telegra.ph)

✨ **Contoh:**
- Balas teks ➡️ `.tg Judul`
- Balas gambar / file ➡️ `.tg`
"""
}

def register(client):

    @client.on(events.NewMessage(pattern=r"^\.tg(?: (.+))?$"))
    async def telegraph_handler(event):
        title = event.pattern_match.group(1) or "Bullove Telegraph"
        reply = await event.get_reply_message()

        if not reply:
            return await event.reply("❌ Balas ke pesan atau media untuk upload.")

        # 📝 Kalau reply berupa teks
        if reply.message and not reply.media:
            content = f"<pre>{reply.message}</pre>"
            page = telegraph.create_page(
                title=title,
                author_name="Bullove Bot",
                html_content=content
            )
            url = f"https://telegra.ph/{page['path']}"
            return await event.reply(
                f"📝 <b>Berhasil Upload Teks</b>\n🔗 <a href='{url}'>Klik di sini</a>",
                link_preview=True
            )

        # 🖼️ Kalau reply berupa media
        file_path = await reply.download_media()
        try:
            # Jika sticker .webp → ubah ke .png
            if file_path.endswith(".webp"):
                png_path = file_path.replace(".webp", ".png")
                Image.open(file_path).save(png_path)
                os.remove(file_path)
                file_path = png_path

            result = upload_file(file_path)
            # result biasanya: [{'src': '/file/abc123.png'}]
            if isinstance(result, list):
                src = result[0]["src"]
            elif isinstance(result, dict):
                src = result.get("src")
            else:
                raise Exception(f"Respon upload tidak dikenal: {result}")

            url = f"https://telegra.ph{src
