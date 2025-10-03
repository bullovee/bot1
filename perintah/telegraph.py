# © 2025 - Buatan khusus untuk Bullovee Bot
# Modul: Telegraph Uploader
# Help Menu
HELP = {
    "telegraph": """
📌 **Perintah:** `.telegraph [judul opsional]`
↪ Balas ke teks atau media untuk mengupload ke [Telegraph](https://telegra.ph)

✨ **Contoh Penggunaan:**
- Balas teks ➡️ `.telegraph JudulSaya`
- Balas file / gambar ➡️ `.telegraph`
- Balas sticker / animasi ➡️ `.telegraph Stickerku`

📝 **Keterangan:**
- Teks akan ditempel ke halaman Telegraph.
- Gambar / file akan diupload ke Telegraph File Hosting.
- Sticker otomatis dikonversi ke PNG.
- TGS (animated sticker) otomatis dikonversi ke GIF.
"""
}

import os
import pathlib
from PIL import Image
from telegraph import Telegraph
from telethon.tl.types import DocumentAttributeFilename

from userbot import ultroid_bot
from userbot.utils import ultroid_cmd, mediainfo, uf, bash, get_string

# Inisialisasi Telegraph (kalau belum pernah login)
telegraph = Telegraph()
if not telegraph.get_access_token():
    telegraph.create_account(short_name="bullovee_bot")


@ultroid_cmd(pattern="telegraph( (.*)|$)")
async def telegraphcmd(event):
    """
    Upload media atau text ke Telegraph
    Gunakan: reply ke pesan / file → ketik .telegraph [judul opsional]
    """
    xx = await event.eor(get_string("com_1"))
    match = event.pattern_match.group(1).strip() or "Bullovee Telegraph"

    reply = await event.get_reply_message()
    if not reply:
        return await xx.eor("`Balas ke pesan atau file untuk diupload.`")

    # Jika text biasa
    if not reply.media and reply.message:
        content = reply.message
        makeit = telegraph.create_page(
            title=match,
            content=[content],
        )
        return await xx.eor(
            f"Pasted ke Telegraph: [Klik Disini]({makeit['url']})", link_preview=False
        )

    # Jika media
    getit = await reply.download_media()
    dar = mediainfo(reply.media)

    try:
        if dar == "sticker":
            # Convert sticker webp ke png
            file = f"{getit}.png"
            Image.open(getit).save(file)
            os.remove(getit)
            getit = file
        elif dar.endswith("animated"):
            # Convert TGS ke GIF
            file = f"{getit}.gif"
            await bash(f"lottie_convert.py '{getit}' {file}")
            os.remove(getit)
            getit = file

        if "document" not in dar:
            try:
                nn = uf(getit)
                amsg = f"✅ Uploaded ke [Telegraph]({nn})"
            except Exception as e:
                amsg = f"❌ Gagal Upload: {e}"
            os.remove(getit)
            return await xx.eor(amsg)

        # Jika file teks / dokumen
        content = pathlib.Path(getit).read_text()
        os.remove(getit)
        makeit = telegraph.create_page(title=match, content=[content])
        await xx.eor(
            f"✅ Pasted ke Telegraph: [Klik Disini]({makeit['url']})",
            link_preview=False,
        )

    except Exception as e:
        await xx.eor(f"❌ Terjadi error: {e}")
