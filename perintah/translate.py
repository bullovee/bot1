import os
from telethon import events
from openai import OpenAI

ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

HELP = {
    "utility": [
        ".trl <teks> → Translate otomatis ke Bahasa Inggris 🌐",
        ".trid (reply pesan) → Translate otomatis ke Bahasa Indonesia 🇮🇩",
    ]
}

def init(client):
    print("✅ Modul TRANSLATE dimuat...")

    # 🌐 .trl → translate ke Inggris
    @client.on(events.NewMessage(pattern=r"^\.trl (.+)"))
    async def handler_trl(event):
        text_to_translate = event.pattern_match.group(1)

        try:
            response = ai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a translation assistant."},
                    {"role": "user", "content": f"Translate this text to English ONLY:\n{text_to_translate}"}
                ]
            )

            translated_text = response.choices[0].message.content.strip()
            await event.edit(translated_text)

        except Exception as e:
            await event.reply(f"❌ Gagal translate: {e}")

    # 🇮🇩 .trid → reply pesan asing → translate ke Indonesia
    @client.on(events.NewMessage(pattern=r"^\.trid$"))
    async def handler_trid(event):
        if not event.is_reply:
            await event.reply("⚠️ Balas pesan yang ingin diterjemahkan ke Bahasa Indonesia.")
            return

        reply_msg = await event.get_reply_message()
        original_text = reply_msg.text
        sender = await reply_msg.get_sender()
        nama = sender.first_name or sender.username or "Unknown"

        try:
            response = ai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a translation assistant."},
                    {"role": "user", "content": f"Detect the language and translate this to Indonesian. Also include the detected language name:\n{original_text}"}
                ]
            )

            translated_text = response.choices[0].message.content.strip()
            await event.reply(f"👤 he/she {nama}:\n\"{translated_text}\"")

        except Exception as e:
            await event.reply(f"❌ Gagal translate: {e}")
