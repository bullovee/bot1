import os
from telethon import events
from openai import OpenAI

# 🔑 Ambil API Key dari Railway
ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ HELP otomatis masuk ke daftar global lewat __init__.py
HELP = {
    "utility": [
        ".trl <teks> → Translate ke Bahasa Inggris 🇬🇧",
        ".trid (reply pesan) → Translate ke Bahasa Indonesia 🇮🇩 dengan deteksi bahasa",
    ]
}

def init(client):
    print("✅ Modul TRANSLATE dimuat...")

    # === 📌 .trl → ke Bahasa Inggris ===
    @client.on(events.NewMessage(pattern=r"^\.trl (.+)"))
    async def handler_translate_en(event):
        text_to_translate = event.pattern_match.group(1)

        try:
            response = ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Translate the following text to English. Respond ONLY with the translation, no explanations."
                    },
                    {"role": "user", "content": text_to_translate}
                ]
            )

            translated_text = response.choices[0].message["content"].strip()
            await event.edit(translated_text)

        except Exception as e:
            await event.edit(f"❌ Gagal translate: {e}")

    # === 📌 .trid → ke Bahasa Indonesia (dengan deteksi bahasa) ===
    @client.on(events.NewMessage(pattern=r"^\.trid$"))
    async def handler_translate_id(event):
        reply_msg = await event.get_reply_message()
        if not reply_msg or not reply_msg.text:
            await event.reply("⚠️ Balas pesan yang ingin diterjemahkan ke Bahasa Indonesia.")
            return

        original_text = reply_msg.text

        try:
            # 🧠 Minta AI deteksi bahasa + terjemahkan
            response = ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Detect the language of the text, then translate it to Indonesian. "
                            "Return a JSON object with keys: language (detected language) and translation (Indonesian translation). "
                            "Respond ONLY with the JSON."
                        )
                    },
                    {"role": "user", "content": original_text}
                ]
            )

            import json
            content = response.choices[0].message["content"]
            result = json.loads(content)

            detected_lang = result.get("language", "Unknown")
            translated_text = result.get("translation", "")

            sender = await reply_msg.get_sender()
            sender_name = sender.first_name or "Unknown"

            output = (
                f'👤 **he/she {sender_name}**:\n'
                f'"{translated_text}"\n\n'
                f'The translation from {detected_lang} → Indonesian 🇮🇩'
            )
            await event.edit(output)

        except Exception as e:
            await event.edit(f"❌ Gagal translate: {e}")
