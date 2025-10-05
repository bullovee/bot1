import os
from telethon import events
from openai import OpenAI

# 🔑 Ambil API Key dari Railway / Environment
ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ Otomatis masuk ke HELP global (__init__.py)
HELP = {
    "utility": [
        ".tr [teks atau reply] → Auto detect bahasa & translate 🇮🇩↔🇬🇧",
    ]
}

def init(client):
    print("✅ Modul TRANSLATE (.tr) dimuat...")

    @client.on(events.NewMessage(pattern=r"^\.tr(?:\s+(.+))?$"))
    async def handler_translate(event):
        # 📝 Cek apakah pakai reply atau langsung tulis teks
        if event.pattern_match.group(1):
            text_to_translate = event.pattern_match.group(1)
            nama_pengirim = "Kamu"
        elif event.is_reply:
            reply_msg = await event.get_reply_message()
            text_to_translate = reply_msg.text
            sender = await reply_msg.get_sender()
            nama_pengirim = sender.first_name or sender.username or "Unknown"
        else:
            await event.reply("⚠️ Balas pesan atau tulis teks setelah `.tr` untuk diterjemahkan.")
            return

        try:
            # 🧠 Gunakan GPT-4o-mini untuk auto detect & translate
            response = ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a translation assistant. "
                            "Detect the input language automatically. "
                            "If the text is in Indonesian, translate it to English. "
                            "If it's in another language, translate it to Indonesian. "
                            "Respond ONLY with the translation result, no explanation."
                        ),
                    },
                    {"role": "user", "content": text_to_translate}
                ]
            )

            translated_text = response.choices[0].message["content"].strip()

            # ✨ Format hasil terjemahan rapi
            await event.reply(f"👤 {nama_pengirim}:\n\"{translated_text}\"")

        except Exception as e:
            await event.reply(f"❌ Gagal translate: {e}")
