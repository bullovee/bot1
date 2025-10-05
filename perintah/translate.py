import os
from telethon import events
from openai import OpenAI

# 🔑 Ambil API Key dari Railway / variabel lingkungan
ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ Ini otomatis tergabung import os
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

# 🌐 Mapping kode bahasa ke bendera
FLAG_MAP = {
    "EN": "🇬🇧", "ID": "🇮🇩", "JP": "🇯🇵", "KR": "🇰🇷",
    "CN": "🇨🇳", "FR": "🇫🇷", "DE": "🇩🇪", "ES": "🇪🇸",
    "RU": "🇷🇺", "AR": "🇸🇦"
}

def init(client):
    print("✅ Modul TRANSLATE (.tr) dimuat...")

    @client.on(events.NewMessage(pattern=r"^\.tr(?: |$)(.*)"))
    async def handler_tr(event):
        user_text = event.pattern_match.group(1).strip()

        # 📝 Mode 1: .tr <teks> → translate ke Inggris
        if user_text:
            try:
                response = ai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Translate the text to English. Respond ONLY with the translation, no extra words."},
                        {"role": "user", "content": user_text}
                    ]
                )
                translated_text = response.choices[0].message.content.strip()
                await event.edit(translated_text)

            except Exception as e:
                await event.edit(f"❌ Gagal translate: {e}")
            return

        # 📝 Mode 2: Balas pesan + .tr → translate ke Indonesia
        if event.is_reply:
            reply_msg = await event.get_reply_message()
            original_text = reply_msg.text
            sender = await reply_msg.get_sender()
            nama = sender.first_name or sender.username or "Unknown"

            try:
                # 🧠 Suruh model deteksi bahasa dan terjemahkan ke Indo
                prompt = f"""
Detect the language of the following text. 
Reply in this exact format:

Language: <language name> (<code like EN, ID, JP>)
Translation: <translated text to Indonesian>

Text:
{original_text}
                """

                response = ai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful translation assistant."},
                        {"role": "user", "content": prompt.strip()}
                    ]
                )

                result = response.choices[0].message.content.strip()

                # 🧩 Parsing manual (karena model balas format tetap)
                lang_name = "Unknown"
                lang_code = "??"
                translated_text = original_text

                for line in result.splitlines():
                    if line.startswith("Language:"):
                        # Contoh: Language: Korean (KR)
                        try:
                            lang_part = line.split(":", 1)[1].strip()
                            lang_name = lang_part.split("(")[0].strip()
                            lang_code = lang_part.split("(")[1].replace(")", "").strip().upper()
                        except:
                            pass
                    elif line.startswith("Translation:"):
                        translated_text = line.split(":", 1)[1].strip()

                flag = FLAG_MAP.get(lang_code, "🏳️")

                reply_text = (
                    f"👤 𝗪𝗮𝗿𝘂𝗻𝗴 𝗕𝘂𝗹𝗹𝗼𝘃𝗲 **Said** :\n"
                    f"`⎯⎯⎯⎯⎯⎯⎯⎯⎯`\n"
                    f"`{flag} {lang_code} : {original_text}`\n"
                    f"`🇮🇩 ID : {translated_text}`\n"
                    f"`⎯⎯⎯⎯⎯⎯⎯⎯⎯`\n"
                    f"_Detected language {lang_name} Translation to Indonesian._"
                )

                await event.reply(reply_text)

            except Exception as e:
                await event.reply(f"❌ Gagal translate: {e}")
            return

        # ⚠️ Tidak ada teks & tidak reply
        await event.reply("⚠️ Gunakan `.tr <teks>` atau balas pesan dengan `.tr`.")
#ke HELP global lewat __init__.py
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
                        {"role": "user", "content": f"Detect the language and translate this to Indonesian. Also include the detected language name and language code (like EN, ID, JP). Respond in JSON with keys: detected_language_name, detected_language_code, translated_text."}
                    ]
                )

                import json
                data = json.loads(response.choices[0].message.content)
                lang_name = data.get("detected_language_name", "Unknown")
                lang_code = data.get("detected_language_code", "??").upper()
                translated_text = data.get("translated_text", "")

                # 🇬🇧 Bendera otomatis (sederhana)
                FLAG_MAP = {
                    "EN": "🇬🇧", "ID": "🇮🇩", "JP": "🇯🇵", "KR": "🇰🇷",
                    "CN": "🇨🇳", "FR": "🇫🇷", "DE": "🇩🇪", "ES": "🇪🇸",
                    "RU": "🇷🇺", "AR": "🇸🇦"
                }
                flag = FLAG_MAP.get(lang_code, "🏳️")

                reply_text = (
                    f"👤 𝗪𝗮𝗿𝘂𝗻𝗴 𝗕𝘂𝗹𝗹𝗼𝘃𝗲 **Said** :\n"
                    f"`⎯⎯⎯⎯⎯⎯⎯⎯⎯`\n"
                    f"`{flag} {lang_code} : {original_text}`\n"
                    f"`🇮🇩 ID : {translated_text}`\n"
                    f"`⎯⎯⎯⎯⎯⎯⎯⎯⎯`\n"
                    f"_Detected language {lang_name} Translation to Indonesian._"
                )

                await event.reply(reply_text)

            except Exception as e:
                await event.reply(f"❌ Gagal translate: {e}")
            return

        # Jika tidak ada teks & tidak reply
        await event.reply("⚠️ Gunakan `.tr <teks>` atau balas pesan dengan `.tr`.")
