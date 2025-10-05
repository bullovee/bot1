import os
from telethon import events
from openai import OpenAI

# 🔑 Ambil API Key dari Railway
ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ Ini otomatis tergabung ke HELP global (__init__.py)
HELP = {
    "utility": [
        ".trl <teks> → Translate otomatis ke Bahasa Inggris 🌐",
        ".trid (reply pesan) → Deteksi & translate ke Bahasa Indonesia 🇮🇩",
    ]
}

def init(client):
    print("✅ Modul TRANSLATE dimuat...")

    # === .trl → translate ke Bahasa Inggris ===
    @client.on(events.NewMessage(pattern=r"^\.trl (.+)"))
    async def handler_translate_en(event):
        text_to_translate = event.pattern_match.group(1)

        try:
            response = ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Translate the text to English. Respond ONLY with the translation."},
                    {"role": "user", "content": text_to_translate}
                ]
            )

            translated_text = response.choices[0].message.content.strip()
            await event.edit(translated_text)

        except Exception as e:
            await event.edit(f"❌ Gagal translate: {e}")

    # === .trid → reply pesan, deteksi & translate ke Bahasa Indonesia ===
    @client.on(events.NewMessage(pattern=r"^\.trid$"))
    async def handler_translate_id(event):
        if not event.is_reply:
            await event.reply("⚠️ Balas pesan yang ingin diterjemahkan dengan `.trid`")
            return

        replied = await event.get_reply_message()
        original_text = replied.message

        try:
            # 🧠 Langkah 1: Deteksi bahasa
            detect_resp = ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Detect the language of the following text. Respond with ONLY the language name in English."},
                    {"role": "user", "content": original_text}
                ]
            )
            detected_lang = detect_resp.choices[0].message.content.strip()

            # 🌐 Langkah 2: Translate ke Bahasa Indonesia
            translate_resp = ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Translate the text to Indonesian. Respond ONLY with the translation."},
                    {"role": "user", "content": original_text}
                ]
            )
            translated_text = translate_resp.choices[0].message.content.strip()

            # 👤 Ambil nama pengirim
            sender = await replied.get_sender()
            name = sender.first_name or sender.username or "Pengguna"

            hasil = (
                f"👤 he/she ({name}):\n"
                f"\"{translated_text}\"\n\n"
                f"🌐 The translation from **{detected_lang}** to **Indonesian**."
            )

            await event.reply(hasil)

        except Exception as e:
            await event.reply(f"❌ Gagal translate: {e}")
