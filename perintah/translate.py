import os
from telethon import events
from openai import OpenAI

# 🔑 Ambil API Key dari Railway (variable: OPENAI_API_KEY)
ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ Otomatis masuk ke HELP global
HELP = {
    "utility": [
        ".tr <teks> → Translate otomatis ke Inggris 🌐",
        ".tr (reply pesan) → Deteksi & translate otomatis ke Bahasa Indonesia 🇮🇩",
    ]
}

def init(client):
    print("✅ Modul TRANSLATE (.tr) dimuat...")

    @client.on(events.NewMessage(pattern=r"^\.tr(?:\s+(.+))?$"))
    async def handler_tr(event):
        text_to_translate = event.pattern_match.group(1)

        # 📌 MODE 1: Terjemahkan teks ke Inggris
        if text_to_translate:
            try:
                response = ai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Translate the text to English. Respond ONLY with the translation."},
                        {"role": "user", "content": text_to_translate}
                    ]
                )
                translated_text = response.choices[0].message["content"].strip()
                await event.edit(translated_text)
            except Exception as e:
                await event.edit(f"❌ Gagal translate: {e}")

        # 📌 MODE 2: Reply pesan → translate ke Bahasa Indonesia
        else:
            if not event.is_reply:
                await event.reply("⚠️ Balas pesan yang ingin diterjemahkan ke Bahasa Indonesia.")
                return

            reply_msg = await event.get_reply_message()
            original_text = reply_msg.text
            sender = await reply_msg.get_sender()
            nama = sender.first_name or sender.username or "Unknown"

            try:
                response = ai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Detect the language and translate the following text to Indonesian. Include the detected language name."},
                        {"role": "user", "content": original_text}
                    ]
                )
                translated_text = response.choices[0].message["content"].strip()

                await event.reply(
                    f"👤 {nama}:\n\"{translated_text}\""
                )
            except Exception as e:
                await event.reply(f"❌ Gagal translate: {e}")
