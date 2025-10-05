    # 🎨 ========== IMAGINE Handler ==========
    @client.on(events.NewMessage(pattern=r"^\.imagine(?: |$)(.*)"))
    async def handler_imagine(event):
        prompt = event.pattern_match.group(1).strip()
        if not prompt:
            await event.reply("⚠️ Gunakan `.imagine <deskripsi gambar>`.")
            return

        await event.edit("🎨 Sedang membuat gambar AI...")
        try:
            result = ai_client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="1024x1024"
            )
            image_url = result.data[0].url
            await event.client.send_file(event.chat_id, image_url, caption=f"🧠 Hasil `.imagine`\n📜 {prompt}")
            await event.delete()
        except Exception as e:
            await event.edit(f"❌ Gagal membuat gambar: {e}")

    # 💻 ========== CODE Handler ==========
    @client.on(events.NewMessage(pattern=r"^\.code(?: |$)(.*)"))
    async def handler_code(event):
        query = event.pattern_match.group(1).strip()
        if not query:
            await event.reply("⚠️ Gunakan `.code <bahasa>: <perintah>`\nContoh: `.code python: buat bot telegram sederhana`")
            return

        await event.edit("💻 AI sedang menulis kode...")
        try:
            response = ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Kamu adalah AI programmer. Buat kode singkat & jelas sesuai permintaan. Sertakan penjelasan singkat jika perlu."},
                    {"role": "user", "content": query}
                ]
            )
            code = response.choices[0].message.content.strip()
            await event.edit(f"🧠 **AI Code:**\n\n{code}")
        except Exception as e:
            await event.edit(f"❌ Gagal generate code: {e}")
