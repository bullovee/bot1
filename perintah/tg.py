import os
import asyncio
import tempfile
from telegraph import upload_file, Telegraph
from pyrogram import Client, filters

HELP = {
    "Tg": [
        ".tg [judul opsional] → Balas ke teks atau media untuk upload ke Telegraph"
    ]
}

telegraph = Telegraph()
telegraph.create_account(short_name="bullove")

def get_telegraph_url(result):
    """Helper untuk ambil URL telegraph dari hasil upload"""
    if isinstance(result, list) and len(result) > 0:
        first = result[0]
        if isinstance(first, dict):
            return f"https://telegra.ph{first.get('src')}"
        elif isinstance(first, str):
            return f"https://telegra.ph{first}"
    return None

def register(client: Client):

    @client.on_message(filters.me & filters.command("tg", prefixes="."))
    async def telegraph_handler(_, message):
        try:
            # ambil judul opsional
            args = message.text.split(maxsplit=1)
            title = args[1] if len(args) > 1 else "Telegraph Upload"

            if message.reply_to_message:
                reply = message.reply_to_message

                # 📌 Kalau reply ke teks
                if reply.text or reply.caption:
                    text_content = reply.text or reply.caption
                    response = telegraph.create_page(
                        title,
                        html_content=f"<pre>{text_content}</pre>"
                    )
                    await message.reply(f"✅ Teks berhasil diupload:\n👉 https://telegra.ph/{response['path']}")

                # 📌 Kalau reply ke media
                elif reply.media:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        file_path = await client.download_media(reply, file_name=tmpdir)
                        result = upload_file(file_path)
                        url = get_telegraph_url(result)
                        if url:
                            await message.reply(f"✅ Media berhasil diupload:\n👉 {url}")
                        else:
                            await message.reply("❌ Gagal upload: hasil kosong.")
            else:
                await message.reply("❌ Balas ke teks atau media dengan perintah `.tg [judul opsional]`")

        except Exception as e:
            await message.reply(f"❌ Gagal upload media:\n<code>{e}</code>")
            print(f"TG ERROR: {e}")
