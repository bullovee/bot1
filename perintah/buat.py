import asyncio
import random
import time
from datetime import datetime
from telethon import events
from telethon.tl.functions.channels import CreateChannelRequest
from telethon.tl.functions.messages import CreateChatRequest, ExportChatInviteRequest
from telethon.errors import FloodWaitError

from .random_messages import RANDOM_MESSAGES  # pastikan file ini ada

OWNER_ID = None
buat_sessions = {}  # simpan sementara session interaktif


def progress_bar(current, total, length=20):
    filled = int(length * current // total)
    bar = "█" * filled + "▒" * (length - filled)
    return f"[{bar}] {current}/{total}"


# === REGISTER COMMANDS BUAT ===
def init_buat(client):

    # 📌 .buat
    @client.on(events.NewMessage(pattern=r"^\.buat (b|g|c)(?: (\d+))? (.+)"))
    async def handler_buat(event):
        if event.sender_id != OWNER_ID:
            return

        await event.delete()
        jenis = event.pattern_match.group(1)
        jumlah = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 1
        nama = event.pattern_match.group(3)

        # simpan session + pertanyaan pertama
        tanya = await event.respond("❓ Apakah ingin mengirim pesan otomatis ke grup/channel? (Y/N)")
        buat_sessions[event.sender_id] = {
            "jenis": jenis,
            "jumlah": jumlah,
            "nama": nama,
            "tanya_msg": tanya,
            "tanya_msg2": None
        }

    # 📌 respon interaktif setelah .buat
    @client.on(events.NewMessage())
    async def handler_interaktif(event):
        if event.sender_id != OWNER_ID or event.sender_id not in buat_sessions:
            return

        session = buat_sessions[event.sender_id]

        # jawaban Y/N
        if "auto_msg" not in session:
            if event.raw_text.strip().upper() == "Y":
                session["auto_msg"] = True
                tanya2 = await event.reply("📩 Berapa jumlah pesan otomatis yang ingin dikirim? (contoh: 5)")
                session["tanya_msg2"] = tanya2
                await event.delete()
                return

            elif event.raw_text.strip().upper() == "N":
                session["auto_msg"] = False
                await mulai_buat(client, event, session, 0)
                del buat_sessions[event.sender_id]
                await event.delete()
                return

        # jumlah pesan otomatis
        if session.get("auto_msg") and "auto_count" not in session:
            try:
                count = int(event.raw_text.strip())
                if count < 1:
                    count = 1
                elif count > 10:
                    count = 10
                session["auto_count"] = count
                await mulai_buat(client, event, session, count)
                del buat_sessions[event.sender_id]
            except ValueError:
                await event.reply("⚠️ Masukkan angka yang valid (1-10).")
            await event.delete()


# === Proses utama buat grup/channel ===
async def mulai_buat(client, event, session, auto_count):
    jenis, jumlah, nama = session["jenis"], session["jumlah"], session["nama"]
    msg = await event.respond("⏳ Menyiapkan pembuatan group/channel...")

    hasil = []
    sukses = 0
    gagal = 0

    try:
        for i in range(1, jumlah + 1):
            nama_group = f"{nama} {i}" if jumlah > 1 else nama

            try:
                if jenis == "b":
                    r = await client(CreateChatRequest(
                        users=[await client.get_me()],
                        title=nama_group,
                    ))
                    chat_id = r.chats[0].id
                else:
                    r = await client(CreateChannelRequest(
                        title=nama_group,
                        about="GRUB BY @WARUNGBULLOVE",
                        megagroup=(jenis == "g"),
                    ))
                    chat_id = r.chats[0].id

                link = (await client(ExportChatInviteRequest(chat_id))).link
                hasil.append(f"✅ [{nama_group}]({link})")
                sukses += 1

                # 🔹 pesan otomatis jika Y
                if auto_count > 0:
                    for _ in range(auto_count):
                        pesan = random.choice(RANDOM_MESSAGES)
                        try:
                            await client.send_message(chat_id, pesan)
                            await asyncio.sleep(1)
                        except FloodWaitError as fw:
                            await asyncio.sleep(fw.seconds)
                            await client.send_message(chat_id, pesan)

            except Exception as e:
                hasil.append(f"❌ {nama_group} (error: {e})")
                gagal += 1

            bar = progress_bar(i, jumlah)
            await msg.edit(f"🔄 Membuat {nama_group} ({i}/{jumlah})\n{bar}")

    except FloodWaitError as e:
        gagal = jumlah - sukses
        hasil.append(f"⚠️ Kena limit Telegram! Tunggu {e.seconds//3600} jam {e.seconds%3600//60} menit.")
    except Exception as e:
        gagal = jumlah - sukses
        hasil.append(f"❌ Error global: {str(e)}")

    # 🕒 Detail waktu Indonesia (lokal)
    now = datetime.now()
    hari = now.strftime("%A")
    jam = now.strftime("%H:%M:%S")
    tanggal = now.strftime("%d %B %Y")

    detail = (
        "```\n"
        f"🕒 Detail:\n"
        f"- jumlah berhasil di buat : {sukses}\n"
        f"- jumlah gagal di buat    : {gagal}\n\n"
        f"- Hari   : {hari}\n"
        f"- Jam    : {jam} WIB\n"
        f"- Tanggal: {tanggal}\n"
        "```"
    )

    await msg.edit(
        "🎉 Grup/Channel selesai dibuat:\n\n" + "\n".join(hasil) + "\n\n" + detail,
        link_preview=False
    )

    for tanya_msg in (session.get("tanya_msg"), session.get("tanya_msg2")):
        if tanya_msg:
            try:
                await tanya_msg.delete()
            except:
                pass
