import os
from telethon import events
from openai import OpenAI

# 🔑 Ambil API Key dari Railway / variabel lingkungan
ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ Ini otomatis tergabung ke HELP global lewat __init__.py
HELP = {
    "utility": [
        ".tr <teks> → Translate otomatis ke Bahasa Inggris 🌐",
        ".tr (balas pesan) → Translate otomatis ke Bahasa Indonesia 🇮🇩",
    ]
}

def init(client):
    print("✅ Modul TRANSLATE (.tr) dimuat...")

    @client.on(events.NewMessage(pattern=r"^\.tr(?: |$)(.*)"))
    async def handler_tr(event):
        user_text = event.pattern_match.group(1).strip()

        # 📝 Mode 1: Jika ada teks setelah .tr → translate ke Inggris
        if user_text:
            try:
                response = ai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Translate the text to English. Respond ONLY with the translation, no explanations."},
                        {"role": "user", "content": user_text}
                    ]
                )

                translated_text = response.choices[0].message.content.strip()
                await event.edit(translated_text)

            except Exception as e:
                await event.edit(f"❌ Gagal translate: {e}")
            return

        # 📝 Mode 2: Jika tidak ada teks tapi reply → translate ke Indonesia
        if event.is_reply:
            reply_msg = await event.get_reply_message()
            original_text = reply_msg.text
            sender = await reply_msg.get_sender()
            nama = sender.first_name or sender.username or "Unknown"

            try:
                response = ai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a translation assistant."},
                        {"role": "user", "content": f"Detect the language and translate this to Indonesian. Also include the detected language name:\n{original_text}"}
                    ]
                )

                translated_text = response.choices[0].message.content.strip()
                await event.reply(f"👤 he/she {nama}:\n\"{translated_text}\"")

            except Exception as e:
                await event.reply(f"❌ Gagal translate: {e}")
            return

        # Jika tidak ada teks & tidak reply
        await event.reply("⚠️ Gunakan `.tr <teks>` atau balas pesan dengan `.tr`.")
