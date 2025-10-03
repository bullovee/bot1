import os
from telethon import events
from telegraph import Telegraph, upload_file

# 📌 Inisialisasi Telegraph (sekali saja)
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

        # 📝 Upload Teks
        if reply.message and not reply.media:
            try:
                content = f"<pre>{reply.message}</pre>"
                result = telegraph.create_page(
                    title=title,
                    author_name="Bullove Bot",
                    html_content=content
                )
                url = f"https://telegra.ph/{result['path']}"
                await event.reply(
                    f"📝 <b>Berhasil Upload Teks</b>\n🔗 <a href='{url}'>Klik di sini</a>",
                    link_preview=True
                )
            except Exception as e:
                await event.reply(f"❌ Gagal upload teks:\n<code>{e}</code>")
            return

        # 🖼️ Upload Media
        if reply.media:
            try:
                # Buat folder downloads jika belum ada
                if not os.path.exists("./downloads"):
                    os.makedirs("./downloads")

                # Download file ke folder lokal
                file_path = await client.download_media(reply, file="./downloads/")
                if not file_path or not os.path.exists(file_path):
                    await event.reply("❌ Gagal: file tidak ditemukan setelah diunduh.")
                    return

                # Upload ke Telegraph (return list path)
                uploaded = upload_file(file_path)
                url = f"https://telegra.ph{uploaded[0]}"

                await event.reply(
                    f"📎 <b>Media berhasil diunggah</b>\n🔗 <a href='{url}'>Klik di sini</a>",
                    link_preview=True
                )

                # Bersihkan file lokal setelah selesai
                os.remove(file_path)

            except Exception as e:
                await event.reply(f"❌ Gagal upload media:\n<code>{e}</code>")

# 🆘 Daftar perintah untuk .help
HELP = {
    "Tg": [
        "• `.tg [judul opsional]` → Balas ke teks atau media untuk upload ke Telegraph.",
    ]
}
