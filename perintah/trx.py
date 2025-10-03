HELP = {
    "trx": [
        ".isi → format isi rekening penjual",
        ".danamasuk → konfirmasi dana sudah diterima",
        ".format → template transaksi",
        ".aturan → peraturan rekber",
        ".fee → informasi biaya rekber",
    ]
}

from telethon import events

OWNER_ID = None

async def init_owner(client):
    """
    Ambil ID akun pendeploy (userbot owner).
    """
    global OWNER_ID
    me = await client.get_me()
    OWNER_ID = me.id


def register_trx(client):
    # 📌 .isi
    @client.on(events.NewMessage(pattern=r"^\.isi$"))
    async def handler_isi(event):
        await event.delete()
        await event.respond(
            "Jika sudah sepakat #DONE\n\n"
            "Penjual Silahkan Di isi :\n\n"
            "Klik 1x text kutipan di bawah untuk COPY\n"
            "```\n"
            "——————————————————————————————————\n"
            " Nama Bank/ewallet :\n"
            " Atas Nama         :\n"
            " No Rek            :\n"
            "——————————————————————————————————\n"
            "```\n"
            "Nb:\n"
            "Biaya admin bank ditanggung oleh pencair.",
            link_preview=False,
        )

    # 📌 .danamasuk
    @client.on(events.NewMessage(pattern=r"^\.danamasuk$"))
    async def handler_danamasuk(event):
        await event.delete()
        await event.respond(
            "**:: Uang sudah masuk di saya. Silahkan kalian serah terima data ::**\n\n"
            "```\n"
            "━━━━━━━━PENTING!!━━━━━━━━\n"
            "⚠️ Harap tanyakan dulu masalah garansi.\n"
            "⚠️ Jangan ada drama, jika ada = saya minta ident via VC.\n"
            "⚠️ Jangan berikan OTP (tele/WA/email) di luar transaksi.\n"
            "⚠️ Jika pembeli tidak ada kabar 8 jam → dana cair.\n"
            "⚠️ Jika penjual hilang 5 jam → uang balik ke pembeli.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "```",
            link_preview=False,
        )

    # 📌 .format
    @client.on(events.NewMessage(pattern=r"^\.format$"))
    async def handler_format(event):
        await event.delete()
        await event.respond(
            "**FORMAT TRANSAKSI**\n\n"
            "Klik 1x text kutipan dibawah untuk COPY format:\n"
            "```\n"
            "Transaksi Apa  :\n"
            "Penjual Siapa  :\n"
            "Pembeli Siapa  :\n"
            "Harga Berapa   :\n"
            "Fee: Buyer/seller\n"
            "```\n\n"
            "Nb:\n"
            "- Tanyakan ulang masalah garansi\n"
            "- Tanyakan ulang kesepakatan DONE\n"
            "- CANCEL/BATAL → FEE tetap terpotong!",
            link_preview=False,
        )

    # 📌 .aturan
    @client.on(events.NewMessage(pattern=r"^\.aturan$"))
    async def handler_aturan(event):
        await event.delete()
        await event.respond(
            "Selamat Datang di Rekber Warung Bullove\n\n"
            "Mohon untuk dibaca dan diperhatikan\n"
            "```——————————————————————————————————```\n"
            "**PERATURAN REKBER :**\n"
            "1. Pastikan saya admin Grub Rekber.\n"
            "2. Dilarang Kick Penjual/Pembeli & ganti judul.\n"
            "3. Tidak menerima REKBER barang/jasa ilegal.\n"
            "4. Mohon untuk jujur mengisi judul TRX!\n\n"
            "**KETENTUAN TRANSAKSI :**\n"
            "❗ Pembeli hilang 8 jam → dana cair.\n"
            "❗ Penjual hilang 5 jam → uang balik ke pembeli.\n"
            "❗ Cancel tetap kena potong fee.\n"
            "❗ Transaksi akun wajib take seEMAIL.\n"
            "❗ Jangan berikan OTP (tele/WA/email) di luar transaksi.\n"
            "❗ Seller & Buyer dilarang hilang saat transaksi.\n\n"
            "®️ 𝙒𝙖𝙧𝙪𝙣𝙜 𝘽𝙪𝙡𝙡𝙤𝙫𝙚",
            link_preview=False,
        )

    # 📌 .fee
    @client.on(events.NewMessage(pattern=r"^\.fee$"))
    async def handler_fee(event):
        await event.delete()
        await event.respond(
            "**BIAYA REKBER / FEE REKBER**\n\n"
            "```\n"
            "10.000  - 100.000   » 5k\n"
            "100.001 - 450.000   » 10k\n"
            "450.001 - 600.000   » 15k\n"
            "600.001 - 800.000   » 20k\n"
            "800.001 - 1.000.000 » 30k\n"
            "1juta   - 5juta     » 50k\n"
            "```\n\n"
            "[CH Warung Bullove](https://t.me/warungbullove_info/850) "
            "[GC Warung Bullove](http://t.me/jb_warungbullove) "
            "[Testimo Rekber](https://t.me/WARUNGBULLOVE_INFO/850)\n\n"
            "**Rekber** @warungbullove",
            link_preview=False,
        )


def init(client):
    """
    Fungsi yang dipanggil otomatis dari bot.py
    """
    register_trx(client)
