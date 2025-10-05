import os
import io
import qrcode
from telethon import events
from openai import OpenAI

# 🔑 Ambil API Key dari Environment
ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🆘 Daftar HELP untuk modul ini
HELP = {
    "ai_tools": [
        ".ai <pertanyaan> → Jawaban dari AI 🤖",
        ".buatjpg <deskripsi> → Buat gambar dari teks 🎨",
        ".qr <link atau teks> → Buat QR code dari teks/link 📱",
        ".qr (balas pesan) → Buat QR code dari isi pesan"
    ]
}

def init(client):
    print("✅ Modul AI Tools (.ai / .buatjpg / .qr) dimuat...")

    # 🧠 ========== AI TEXT (.ai) ==========
    @client.on(events.NewMessage(pattern=r"^\.ai(?: |$)(.*)"))
    async def handler_ai(event):
        prompt = event.pattern_match.group(1).strip()
        if not prompt:
            await event.reply("⚠️ Gunakan `.ai <pertanyaan>`")
            return

        await event.edit("🧠 Sedang berpikir...")
        try:
            response = ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Kamu adalah asisten cerdas Telegram."},
                    {"role": "user", "content": prompt}
                ]
            )
            answer = response.choices[0].message.content.strip()
            await event.edit(f"🤖 **Jawaban AI:**\n{answer}")
        except Exception as e:
            await event.edit(f"❌ Gagal memproses AI: {e}")

    # 🖼️ ========== BUAT JPG (.buatjpg) ==========
    @client.on(events.NewMessage(pattern=r"^\.buatjpg(?: |$)(.*)"))
    async def handler_buatjpg(event):
        prompt = event.pattern_match.group(1).strip()
        if not prompt:
            await event.reply("⚠️ Gunakan `.buatjpg <deskripsi gambar>`")
            return

        await event.edit("🎨 Sedang membuat gambar...")
        try:
            result = ai_client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="1024x1024"
            )
            image_url = result.data[0].url
            await event.client.send_file(event.chat_id, image_url, caption=f"🖼️ {prompt}")
            await event.delete()
        except Exception as e:
            await event.edit(f"❌ Gagal membuat gambar: {e}")

    # 📱 ========== QR CODE (.qr) ==========
    @client.on(events.NewMessage(pattern=r"^\.qr(?: |$)(.*)"))
    async def handler_qr(event):
        # Jika user reply link, ambil dari pesan itu
        if event.is_reply:
            reply_msg = await event.get_reply_message()
            data = reply_msg.text.strip()
        else:
            data = event.pattern_match.group(1).strip()

        if not data:
            await event.reply("⚠️ Gunakan `.qr <link>` atau balas pesan berisi link.")
            return

        await event.edit("📱 Membuat QR Code...")
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # Simpan QR ke buffer
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)

            await event.client.send_file(event.chat_id, buf, caption=f"🔗 {data}")
            await event.delete()
        except Exception as e:
            await event.edit(f"❌ Gagal membuat QR: {e}")
