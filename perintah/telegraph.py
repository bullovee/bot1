# © 2025 - Buatan khusus untuk Bullovee Bot
# Modul: Telegraph Uploader (Perintah .tg)

HELP = {
    "tg": [
        """
📌 **Perintah:** `.tg [judul opsional]`
↪ Balas ke teks atau media untuk mengupload ke [Telegraph](https://telegra.ph)

✨ **Contoh Penggunaan:**
- Balas teks ➡️ `.tg JudulSaya`
- Balas file / gambar ➡️ `.tg`
- Balas sticker / animasi ➡️ `.tg Stickerku`

📝 **Keterangan:**
- Teks akan ditempel ke halaman Telegraph.
- Gambar / file akan diupload ke Telegraph File Hosting.
- Sticker otomatis dikonversi ke PNG.
- TGS (animated sticker) otomatis dikonversi ke GIF.
        """
    ]
}

import os
import pathlib
from PIL import Image
from telegraph import Telegraph

from userbot import ultroid_bot
from userbot.utils import ultroid_cmd, mediainfo, uf, bash, get_string

# Inisialisasi Telegraph
telegraph = Telegraph()
if not telegraph.get_access_token():
    telegraph.create_account(short_name="bullovee_bot")


@ultroid_cmd(pattern="tg( (.*)|$)")
async def tgcmd(event):
    """
    Upload media atau text ke Telegraph
    Gunakan: reply ke pesan / file → ketik .tg [judul opsional]
    """
    xx = await event.eor(get_string("com_1"))
    match = (event.pattern_match.group(1) or "").strip() or "Bullovee Telegraph"

    reply = await event.get_reply_message()
    if not reply:
        return await xx.eor("⚠️ Balas ke pesan atau file untuk diupload.")

    # === Jika text biasa ===
    if not reply.media and reply.message:
        content = reply.message
        try:
            makeit = telegraph.create_page(
                title=match,
                author_name="Bullovee Bot",
                content=[{"tag": "p", "children": [content]}],
            )
            return await xx.eor(
                f"✅ Pasted ke Telegraph: [Klik Disini]({makeit['url']})",
                link_preview=False,
            )
        except Exception as e:
            return await xx.eor(f"❌ Terjadi error saat upload teks: {e}")

    # === Jika media ===
    getit = await reply.download_media()
    dar = mediainfo(reply.media)

    try:
        # Sticker → convert ke PNG
        if dar == "sticker":
            file = f"{getit}.png"
            Image.open(getit).save(file)
            os.remove(getit)
            getit = file

        # Animated sticker (TGS) → convert ke GIF
        elif dar.endswith("animated"):
            file = f"{getit}.gif"
            await bash(f"lottie_convert.py '{getit}' {file}")
            os.remove(getit)
            getit = file

        # Jika gambar/file biasa
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
        makeit = telegraph.create_page(
            title=match,
            author_name="Bullovee Bot",
            content=[{"tag": "pre", "children": [content]}],
        )
        await xx.eor(
            f"✅ Past
