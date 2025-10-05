import os
from telethon import events
from openai import OpenAI

# Inisialisasi client OpenAI dengan API key dari Railway
ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ Ini akan otomatis tergabung ke HELP global lewat __init__.py
HELP = {
    "utility": [
        ".trl <teks> → Translate otomatis ke Bahasa Inggris 🌐",
    ]
}

def init(client):
    print("✅ Modul TRANSLATE dimuat...")

    @client.on(events.NewMessage(pattern=r"^\.trl (.+)"))
    async def handler_translate(event):
        text_to_translate = event.pattern_match.group(1)

        try:
            response = ai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a translation assistant."},
                    {"role": "user", "content": f"Translate this text to English:\n{text_to_translate}"}
                ]
            )

            translated_text = response.choices[0].message.content.strip()
            await event.reply(f"🌐 **Terjemahan:**\n{translated_text}")

        except Exception as e:
            await event.reply(f"❌ Gagal translate: {e}")
