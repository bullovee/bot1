# 📌 tg.py — Modul Telegraph untuk Telethon
# Adaptasi dari Man-Userbot agar cocok dengan struktur perintah/ di userbot kamu

import os
from datetime import datetime
from PIL import Image
from telethon import events
from telegraph import Telegraph, exceptions, upload_file

# 🗂 Folder download sementara
TEMP_DOWNLOAD_DIRECTORY = "./downloads"
os.makedirs(TEMP_DOWNLOAD_DIRECTORY, exist_ok=True)

# 📝 Inisialisasi Telegraph
telegraph = Telegraph()
telegraph.create_account(short_name="BulloveUserbot")


def register(client):
    @client.on(events.NewMessage(pattern=r"^\.tg (m|t)$"))
    async def telegraphs(event):
        """Unggah media atau teks ke Telegraph"""
        mode = event.pattern_match.group(1)
        reply = await event.get_reply_message()

        if not reply:
            await event.reply("❌ Balas ke pesan teks atau media terlebih dahulu.")
            return

        if mode == "m":  # 📎 Upload Media
            await event.reply("⏳ Sedang mengunduh media...")
            start = datetime.now()
            downloaded_file_name = await client.download_media(
                reply, TEMP_DOWNLOAD_DIRECTORY
            )
            end = datetime.now()
            ms = (end - start).seconds

            # ✅ Info unduhan selesai
            await event.reply(
                f"✅ Media diunduh ke `{downloaded_file_name}` dalam {ms} detik."
            )

            # Konversi webp ke PNG (sticker dsb)
            if downloaded_file_name.endswith(".webp"):
                resize_image(downloaded_file_name)

            # Upload ke Telegraph
            try:
                media_urls = upload_file(downloaded_file_name)
                url = f"https://telegra.ph{media_urls[0]}"
                await event.reply(f"📎 Media berhasil diunggah:\n{url}", link_preview=True)
            except exceptions.TelegraphException as exc:
                await event.reply(f"❌ Gagal upload media:\n`{exc}`")
            finally:
                os.remove(downloaded_file_name)

        elif mode == "t":  # 📝 Upload Teks
            if not reply.message:
                await event.reply("❌ Tidak ada teks untuk diunggah.")
                return

            page_title = (await client.get_entity(reply.sender_id)).first_name
            page_content = reply.message.replace("\n", "<br>")
            try:
                response = telegraph.create_page(page_title, html_content=page_content)
                url = f"https://telegra.ph/{response['path']}"
                await event.reply(f"📝 Teks berhasil diunggah:\n{url}", link_preview=True)
            except exceptions.TelegraphException as exc:
                await event.reply(f"❌ Gagal upload teks:\n`{exc}`")


def resize_image(image_path: str):
    """Konversi gambar WebP ke PNG agar bisa diupload ke Telegraph"""
    im = Image.open(image_path)
    im.save(image_path, "PNG")


# 🆘 Daftar perintah Help lokal
HELP = {
    "telegraph": [
        "• `.tg m` → Balas ke media untuk upload ke Telegraph",
        "• `.tg t` → Balas ke teks untuk upload ke Telegraph",
    ]
}
