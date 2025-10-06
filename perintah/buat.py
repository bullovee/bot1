import asyncio
import random
import time
import traceback
import locale
import os
import json
from datetime import datetime, timedelta, timezone
from telethon import events
from telethon.tl.functions.channels import CreateChannelRequest
from telethon.tl.functions.messagesimport asyncio
import random
import time
import traceback
import locale
import os
import json
from datetime import datetime, timedelta, timezone
from telethon import events
from telethon.tl.functions.channels import CreateChannelRequest
from telethon.tl.functions.messages import CreateChatRequest, ExportChatInviteRequest
from telethon.errors import FloodWaitError
from telethon.tl.types import DocumentAttributeFilename

from .random_messages import RANDOM_MESSAGES  # pastikan file ini ada

# === Konfigurasi rekap & channel backup ===
BACKUP_CHANNEL_ID = -1002933104000  # ID channel pribadi kamu
REKAP_FILE = "rekap.json"

# Set locale ke Indonesia (kalau tersedia di sistem)
try:
    locale.setlocale(locale.LC_TIME, "id_ID.UTF-8")
except locale.Error:
    # Fallback manual kalau locale tidak tersedia (Windows sering tidak ada)
    pass

# Manual mapping nama hari & bulan Indonesia
HARI_ID = {
    "Monday": "Senin",
    "Tuesday": "Selasa",
    "Wednesday": "Rabu",
    "Thursday": "Kamis",
    "Friday": "Jumat",
    "Saturday": "Sabtu",
    "Sunday": "Minggu",
}
BULAN_ID = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}

# Zona waktu Indonesia (WIB = UTC+7)
WIB = timezone(timedelta(hours=7))

OWNER_ID = None
buat_sessions = {}  # simpan sementara session interaktif


def log_error(context: str, e: Exception):
    """Cetak error + traceback ke console."""
    print(f"❌ ERROR di {context}: {e}")
    traceback.print_exc()


def progress_bar(current, total, length=20):
    filled = int(length * current // total)
    bar = "█" * filled + "▒" * (length - filled)
    return f"[{bar}] {current}/{total}"


# === OWNER INIT (agar OWNER_ID otomatis terisi) ===
async def init_owner(client):
    global OWNER_ID
    me = await client.get_me()
    OWNER_ID = me.id
    print(f"ℹ️ [BUAT] OWNER_ID otomatis diset ke: {OWNER_ID} ({me.username or me.first_name})")


# === REGISTER COMMANDS BUAT ===
def init(client):

    print("✅ Modul BUAT dimuat...")

    @client.on(events.NewMessage(pattern=r"^\.buat (b|g|c)(?: (\d+))? (.+)"))
    async def handler_buat(event):
        try:
            if event.sender_id != OWNER_ID:
                print(f"🚫 Bukan OWNER: {event.sender_id}")
                return

            print(f"📥 Perintah .buat diterima: {event.raw_text}")

            await event.delete()
            jenis = event.pattern_match.group(1)
            jumlah = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 1
            nama = event.pattern_match.group(3)

            print(f"➡️ Jenis={jenis}, Jumlah={jumlah}, Nama={nama}")

            tanya = await event.respond("❓ Apakah ingin mengirim pesan otomatis ke grup/channel? (Y/N)")
            buat_sessions[event.sender_id] = {
                "jenis": jenis,
                "jumlah": jumlah,
                "nama": nama,
                "tanya_msg": tanya,
                "tanya_msg2": None
            }

        except Exception as e:
            log_error("handler_buat", e)

    @client.on(events.NewMessage())
    async def handler_interaktif(event):
        try:
            if event.sender_id != OWNER_ID or event.sender_id not in buat_sessions:
                return

            session = buat_sessions[event.sender_id]

            # jawaban Y/N
            if "auto_msg" not in session:
                if event.raw_text.strip().upper() == "Y":
                    print("📝 Jawaban interaktif: Y")
                    session["auto_msg"] = True
                    tanya2 = await event.reply("📩 Berapa jumlah pesan otomatis yang ingin dikirim? (contoh: 5)")
                    session["tanya_msg2"] = tanya2
                    await event.delete()
                    return

                elif event.raw_text.strip().upper() == "N":
                    print("📝 Jawaban interaktif: N")
                    session["auto_msg"] = False
                    await mulai_buat(client, event, session, 0)
                    del buat_sessions[event.sender_id]
                    await event.delete()
                    return

            # jumlah pesan otomatis
            if session.get("auto_msg") and "auto_count" not in session:
                try:
                    count = int(event.raw_text.strip())
                    print(f"🔢 Jumlah pesan otomatis: {count}")
                    count = max(1, min(count, 10))
                    session["auto_count"] = count
                    await mulai_buat(client, event, session, count)
                    del buat_sessions[event.sender_id]
                except ValueError:
                    await event.reply("⚠️ Masukkan angka yang valid (1-10).")
                await event.delete()

        except Exception as e:
            log_error("handler_interaktif", e)


# === Proses utama buat grup/channel ===
async def mulai_buat(client, event, session, auto_count):
    jenis, jumlah, nama = session["jenis"], session["jumlah"], session["nama"]
    print(f"🚀 Mulai proses buat {jumlah} item jenis {jenis} dengan nama '{nama}'")
    msg = await event.respond("⏳ Menyiapkan pembuatan group/channel...")

    hasil = []
    sukses = 0
    gagal = 0

    try:
        for i in range(1, jumlah + 1):
            nama_group = f"{nama} {i}" if jumlah > 1 else nama
            print(f"➡️ Membuat: {nama_group} ({i}/{jumlah})")

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

                if auto_count > 0:
                    for n in range(auto_count):
                        pesan = random.choice(RANDOM_MESSAGES)
                        print(f"📨 Kirim pesan otomatis ke {nama_group} #{n+1}")
                        try:
                            await client.send_message(chat_id, pesan)
                            await asyncio.sleep(1)
                        except FloodWaitError as fw:
                            print(f"⏸️ Kena FloodWait {fw.seconds} detik")
                            await asyncio.sleep(fw.seconds)
                            await client.send_message(chat_id, pesan)

            except Exception as e:
                log_error(f"pembuatan {nama_group}", e)
                hasil.append(f"❌ {nama_group} (error: {e})")
                gagal += 1

            bar = progress_bar(i, jumlah)
            await msg.edit(f"🔄 Membuat {nama_group} ({i}/{jumlah})\n{bar}")

    except FloodWaitError as e:
        gagal = jumlah - sukses
        hasil.append(f"⚠️ Kena limit Telegram! Tunggu {e.seconds//3600} jam {e.seconds%3600//60} menit.")
        log_error("FloodWait Global", e)
    except Exception as e:
        gagal = jumlah - sukses
        hasil.append(f"❌ Error global: {str(e)}")
        log_error("mulai_buat", e)

    # 🕒 Waktu lokal Indonesia (WIB)
    now = datetime.now(WIB)
    hari = HARI_ID[now.strftime("%A")]
    tanggal = f"{now.day} {BULAN_ID[now.month]} {now.year}"
    jam = now.strftime("%H:%M:%S")

    detail = (
        "```\n"
        f"🕒 Detail:\n"
        f"- Jumlah berhasil : {sukses}\n"
        f"- Jumlah gagal    : {gagal}\n\n"
        f"- Hari   : {hari}\n"
        f"- Jam    : {jam} WIB\n"
        f"- Tanggal: {tanggal}\n"
        "```"
    )

    await msg.edit(
        "🎉 Grup/Channel selesai dibuat:\n\n" + "\n".join(hasil) + "\n\n" + detail,
        link_preview=False
    )


# === Auto restore atau create rekap.json saat bot start ===
async def load_rekap_from_channel(client):
    try:
        async for msg in client.iter_messages(BACKUP_CHANNEL_ID, limit=10):
            if msg.file and msg.file.name == REKAP_FILE:
                print(f"📥 Menemukan {REKAP_FILE} di channel, mulai restore...")
                await client.download_media(msg, file=REKAP_FILE)
                print(f"✅ Berhasil restore {REKAP_FILE} dari channel.")
                return

        # Kalau tidak ditemukan file di channel, buat default baru
        if not os.path.exists(REKAP_FILE):
            with open(REKAP_FILE, "w") as f:
                json.dump({}, f)
            print(f"📝 {REKAP_FILE} tidak ditemukan di channel — file baru dibuat lokal.")

    except Exception as e:
        print(f"❌ Gagal load rekap dari channel: {e}")
        if not os.path.exists(REKAP_FILE):
            with open(REKAP_FILE, "w") as f:
                json.dump({}, f)


# === HELP MENU BUAT ===
HELP = {
    "buat": [
        ".buat (b|g|c) [jumlah] [nama] → Buat grup/channel otomatis",
        "  b = basic group, g = supergroup, c = channel",
        "  contoh: .buat g 3 GrupTes"
    ]
}
 import CreateChatRequest, ExportChatInviteRequest
from telethon.errors import FloodWaitError

from .random_messages import RANDOM_MESSAGES  # pastikan file ini ada

# 📌 ID channel pribadi untuk backup rekap.json
PRIVATE_CHANNEL_ID = -1002933104000
REKAP_FILE = "rekap.json"

# === FUNGSI REKAP JSON ===
def read_rekap():
    if os.path.exists(REKAP_FILE):
        with open(REKAP_FILE, "r") as f:
            return json.load(f)
    return {}

def write_rekap(data):
    with open(REKAP_FILE, "w") as f:
        json.dump(data, f, indent=4)

# === LOKALISASI WAKTU ===
try:
    locale.setlocale(locale.LC_TIME, "id_ID.UTF-8")
except locale.Error:
    pass

HARI_ID = {
    "Monday": "Senin",
    "Tuesday": "Selasa",
    "Wednesday": "Rabu",
    "Thursday": "Kamis",
    "Friday": "Jumat",
    "Saturday": "Sabtu",
    "Sunday": "Minggu",
}
BULAN_ID = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}

WIB = timezone(timedelta(hours=7))

OWNER_ID = None
buat_sessions = {}  # simpan sementara session interaktif


def log_error(context: str, e: Exception):
    print(f"❌ ERROR di {context}: {e}")
    traceback.print_exc()


def progress_bar(current, total, length=20):
    filled = int(length * current // total)
    bar = "█" * filled + "▒" * (length - filled)
    return f"[{bar}] {current}/{total}"


# === OWNER INIT (agar OWNER_ID otomatis terisi) ===
async def init_owner(client):
    global OWNER_ID
    me = await client.get_me()
    OWNER_ID = me.id
    print(f"ℹ️ [BUAT] OWNER_ID otomatis diset ke: {OWNER_ID} ({me.username or me.first_name})")


# === REGISTER COMMANDS BUAT ===
def init(client):

    print("✅ Modul BUAT dimuat...")

    @client.on(events.NewMessage(pattern=r"^\.buat (b|g|c)(?: (\d+))? (.+)"))
    async def handler_buat(event):
        try:
            if event.sender_id != OWNER_ID:
                print(f"🚫 Bukan OWNER: {event.sender_id}")
                return

            print(f"📥 Perintah .buat diterima: {event.raw_text}")

            await event.delete()
            jenis = event.pattern_match.group(1)
            jumlah = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 1
            nama = event.pattern_match.group(3)

            print(f"➡️ Jenis={jenis}, Jumlah={jumlah}, Nama={nama}")

            tanya = await event.respond("❓ Apakah ingin mengirim pesan otomatis ke grup/channel? (Y/N)")
            buat_sessions[event.sender_id] = {
                "jenis": jenis,
                "jumlah": jumlah,
                "nama": nama,
                "tanya_msg": tanya,
                "tanya_msg2": None
            }

        except Exception as e:
            log_error("handler_buat", e)

    @client.on(events.NewMessage())
    async def handler_interaktif(event):
        try:
            if event.sender_id != OWNER_ID or event.sender_id not in buat_sessions:
                return

            session = buat_sessions[event.sender_id]

            if "auto_msg" not in session:
                if event.raw_text.strip().upper() == "Y":
                    print("📝 Jawaban interaktif: Y")
                    session["auto_msg"] = True
                    tanya2 = await event.reply("📩 Berapa jumlah pesan otomatis yang ingin dikirim? (contoh: 5)")
                    session["tanya_msg2"] = tanya2
                    await event.delete()
                    return

                elif event.raw_text.strip().upper() == "N":
                    print("📝 Jawaban interaktif: N")
                    session["auto_msg"] = False
                    await mulai_buat(client, event, session, 0)
                    del buat_sessions[event.sender_id]
                    await event.delete()
                    return

            if session.get("auto_msg") and "auto_count" not in session:
                try:
                    count = int(event.raw_text.strip())
                    print(f"🔢 Jumlah pesan otomatis: {count}")
                    count = max(1, min(count, 10))
                    session["auto_count"] = count
                    await mulai_buat(client, event, session, count)
                    del buat_sessions[event.sender_id]
                except ValueError:
                    await event.reply("⚠️ Masukkan angka yang valid (1-10).")
                await event.delete()

        except Exception as e:
            log_error("handler_interaktif", e)


# === Proses utama buat grup/channel ===
async def mulai_buat(client, event, session, auto_count):
    jenis, jumlah, nama = session["jenis"], session["jumlah"], session["nama"]
    print(f"🚀 Mulai proses buat {jumlah} item jenis {jenis} dengan nama '{nama}'")
    msg = await event.respond("⏳ Menyiapkan pembuatan group/channel...")

    hasil = []
    sukses = 0
    gagal = 0

    try:
        for i in range(1, jumlah + 1):
            nama_group = f"{nama} {i}" if jumlah > 1 else nama
            print(f"➡️ Membuat: {nama_group} ({i}/{jumlah})")

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

                if auto_count > 0:
                    for n in range(auto_count):
                        pesan = random.choice(RANDOM_MESSAGES)
                        print(f"📨 Kirim pesan otomatis ke {nama_group} #{n+1}")
                        try:
                            await client.send_message(chat_id, pesan)
                            await asyncio.sleep(1)
                        except FloodWaitError as fw:
                            print(f"⏸️ Kena FloodWait {fw.seconds} detik")
                            await asyncio.sleep(fw.seconds)
                            await client.send_message(chat_id, pesan)

            except Exception as e:
                log_error(f"pembuatan {nama_group}", e)
                hasil.append(f"❌ {nama_group} (error: {e})")
                gagal += 1

            bar = progress_bar(i, jumlah)
            await msg.edit(f"🔄 Membuat {nama_group} ({i}/{jumlah})\n{bar}")

    except FloodWaitError as e:
        gagal = jumlah - sukses
        hasil.append(f"⚠️ Kena limit Telegram! Tunggu {e.seconds//3600} jam {e.seconds%3600//60} menit.")
        log_error("FloodWait Global", e)
    except Exception as e:
        gagal = jumlah - sukses
        hasil.append(f"❌ Error global: {str(e)}")
        log_error("mulai_buat", e)

    now = datetime.now(WIB)
    hari = HARI_ID[now.strftime("%A")]
    tanggal = f"{now.day} {BULAN_ID[now.month]} {now.year}"
    jam = now.strftime("%H:%M:%S")

    detail = (
        "```\n"
        f"🕒 Detail:\n"
        f"- Jumlah berhasil : {sukses}\n"
        f"- Jumlah gagal    : {gagal}\n\n"
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
            except Exception as e:
                log_error("hapus pesan interaktif", e)

    # 📝 Tambahan: Update rekap total dan kirim ke channel pribadi
    grup_baru = sukses if jenis in ["b", "g"] else 0
    channel_baru = sukses if jenis == "c" else 0
    await update_rekap(client, OWNER_ID, grup_baru, channel_baru)


# === SISTEM REKAP ===
async def update_rekap(client, owner_id, grup_baru, channel_baru):
    now = datetime.now(WIB)
    tgl_str = now.strftime("%d/%m/%y")

    data = read_rekap()
    if str(owner_id) not in data:
        data[str(owner_id)] = {}

    if tgl_str not in data[str(owner_id)]:
        data[str(owner_id)][tgl_str] = {"grup": 0, "channel": 0}

    data[str(owner_id)][tgl_str]["grup"] += grup_baru
    data[str(owner_id)][tgl_str]["channel"] += channel_baru

    write_rekap(data)

    try:
        await client.send_file(
            PRIVATE_CHANNEL_ID,
            REKAP_FILE,
            caption=f"📊 Rekap data owner {owner_id}"
        )
    except Exception as e:
        log_error("upload rekap ke channel", e)

    await kirim_pesan_total(client, owner_id, data[str(owner_id)])


async def kirim_pesan_total(client, owner_id, data_owner):
    teks = "🎉 Total Grup/Channel dibuat :\n"
    for tgl, rec in sorted(data_owner.items()):
        teks += f"⏺️Tanggal {tgl} Total --> {rec['grup']} Grup / {rec['channel']} Channel\n"

    async for msg in client.iter_messages(PRIVATE_CHANNEL_ID, from_user="me"):
        if msg.text and msg.text.startswith("🎉 Total Grup/Channel"):
            await msg.delete()
            break

    await client.send_message(PRIVATE_CHANNEL_ID, teks)


# === HELP MENU BUAT ===
HELP = {
    "buat": [
        ".buat (b|g|c) [jumlah] [nama] → Buat grup/channel otomatis",
        "  b = basic group, g = supergroup, c = channel",
        "  contoh: .buat g 3 GrupTes"
    ]
}
