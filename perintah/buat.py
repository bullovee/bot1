import asyncio
import random
import traceback
import locale
import json
import os
from datetime import datetime, timedelta, timezone
from telethon import events
from telethon.tl.functions.channels import CreateChannelRequest
from telethon.tl.functions.messages import CreateChatRequest, ExportChatInviteRequest
from telethon.errors import FloodWaitError

from .random_messages import RANDOM_MESSAGES

# Set locale ke Indonesia (best-effort)
try:
    locale.setlocale(locale.LC_TIME, "id_ID.UTF-8")
except locale.Error:
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
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}

WIB = timezone(timedelta(hours=7))

OWNER_ID = None
buat_sessions = {}

# Config backup channel & local rekap file
BACKUP_CHANNEL_ID = -1002933104000
REKAP_FILE = "rekap.json"

def log_error(context: str, e: Exception):
    print(f"❌ ERROR di {context}: {e}")
    traceback.print_exc()

def progress_bar(current, total, length=20):
    filled = int(length * current // total)
    bar = "█" * filled + "▒" * (length - filled)
    return f"[{bar}] {current}/{total}"

# ------------------ Auto-restore rekap.json (download from channel if exists) ------------------
async def auto_restore_rekap(client):
    try:
        if os.path.exists(REKAP_FILE):
            print("📂 rekap.json lokal sudah ada — tidak perlu restore.")
            return

        async for msg in client.iter_messages(BACKUP_CHANNEL_ID, limit=20):
            if msg.file and getattr(msg.file, "name", "").lower() == REKAP_FILE:
                print("☁️ Menemukan rekap.json di channel, mulai restore...")
                await client.download_media(msg, file=REKAP_FILE)
                print("✅ rekap.json berhasil di-restore dari channel.")
                return

        # not found -> create empty
        print("⚠️ rekap.json tidak ditemukan di channel — membuat file kosong lokal...")
        with open(REKAP_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        print("✅ rekap.json kosong berhasil dibuat.")
    except Exception as e:
        print(f"❌ Gagal auto-restore rekap.json: {e}")
        if not os.path.exists(REKAP_FILE):
            with open(REKAP_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)

# ------------------ Upload/Merge rekap.json to channel ------------------
async def upload_rekap_to_channel(client):
    try:
        try:
            with open(REKAP_FILE, "r", encoding="utf-8") as f:
                local_data = json.load(f)
        except Exception:
            local_data = {}

        owner_key = str(OWNER_ID)
        remote_data = {}

        async for msg in client.iter_messages(BACKUP_CHANNEL_ID, limit=20):
            if msg.file and getattr(msg.file, "name", "").lower() == REKAP_FILE:
                try:
                    tmp = REKAP_FILE + ".remote"
                    await client.download_media(msg, file=tmp)
                    with open(tmp, "r", encoding="utf-8") as rf:
                        remote_data = json.load(rf)
                    os.remove(tmp)
                except Exception:
                    remote_data = {}
                break

        if not isinstance(local_data, dict):
            local_data = {}
        if not isinstance(remote_data, dict):
            remote_data = {}

        if owner_key in local_data:
            remote_data[owner_key] = local_data[owner_key]

        with open(REKAP_FILE, "w", encoding="utf-8") as f:
            json.dump(remote_data, f, indent=2, ensure_ascii=False)

        async for msg in client.iter_messages(BACKUP_CHANNEL_ID, limit=50):
            if msg.file and getattr(msg.file, "name", "").lower() == REKAP_FILE:
                await msg.delete()

        await client.send_file(BACKUP_CHANNEL_ID, REKAP_FILE, caption="📊 rekap.json (merged)")
        print("☁️ rekap.json berhasil diupload ke channel backup.")
    except Exception as e:
        log_error("upload_rekap_to_channel", e)

# ------------------ OWNER INIT ------------------
async def init_owner(client):
    global OWNER_ID
    me = await client.get_me()
    OWNER_ID = me.id
    print(f"ℹ️ [BUAT] OWNER_ID diset ke: {OWNER_ID} ({me.username or me.first_name})")

# ------------------ Command registration ------------------
def init(client):
    print("✅ Modul BUAT dimuat...")

    @client.on(events.NewMessage(pattern=r"^\.buat (b|g|c)(?: (\d+))? (.+)"))
    async def handler_buat(event):
        try:
            if event.sender_id != OWNER_ID:
                print(f"🚫 Bukan OWNER: {event.sender_id}")
                return

            jenis = event.pattern_match.group(1)
            jumlah = int(event.pattern_match.group(2)) if event.pattern_match.group(2) else 1
            nama = event.pattern_match.group(3)
            print(f"📥 Perintah .buat → jenis={jenis}, jumlah={jumlah}, nama={nama}")

            tanya = await event.respond("❓ Kirim pesan otomatis ke grup/channel? (Y/N)")
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
            jawaban = event.raw_text.strip().upper()

            if "auto_msg" not in session:
                if jawaban == "Y":
                    session["auto_msg"] = True
                    tanya2 = await event.reply("📩 Berapa jumlah pesan otomatis yang ingin dikirim? (1–10)")
                    session["tanya_msg2"] = tanya2
                elif jawaban == "N":
                    session["auto_msg"] = False
                    await mulai_buat(client, event, session, 0)
                    buat_sessions.pop(event.sender_id, None)
                await event.delete()
                return

            if session.get("auto_msg") and "auto_count" not in session:
                try:
                    cnt = max(1, min(int(event.raw_text.strip()), 10))
                    session["auto_count"] = cnt
                    await mulai_buat(client, event, session, cnt)
                    buat_sessions.pop(event.sender_id, None)
                except ValueError:
                    await event.reply("⚠️ Masukkan angka yang valid 1–10.")
                await event.delete()
        except Exception as e:
            log_error("handler_interaktif", e)

# ------------------ Main membuat grup/channel ------------------
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

            await msg.edit(f"🔄 Membuat {nama_group} ({i}/{jumlah})\n{progress_bar(i, jumlah)}")

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
    tanggal_full = f"{now.day} {BULAN_ID[now.month]} {now.year}"
    tanggal_key = now.strftime("%d/%m/%y")
    jam = now.strftime("%H:%M:%S")

    detail = (
        "```\n"
        f"🕒 Detail:\n"
        f"- Jumlah berhasil : {sukses}\n"
        f"- Jumlah gagal    : {gagal}\n\n"
        f"- Hari   : {hari}\n"
        f"- Jam    : {jam} WIB\n"
        f"- Tanggal: {tanggal_full}\n"
        "```"
    )

    await msg.edit("🎉 Grup/Channel selesai dibuat:\n\n" + "\n".join(hasil) + "\n\n" + detail, link_preview=False)

    # ------------------ Simpan ke JSON ------------------
    try:
        if not os.path.exists(REKAP_FILE):
            with open(REKAP_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)

        with open(REKAP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        owner_key = str(OWNER_ID)
        if owner_key not in data:
            data[owner_key] = {}

        if tanggal_key not in data[owner_key]:
            data[owner_key][tanggal_key] = {"grup": 0, "channel": 0}

        if jenis in ("b", "g"):
            data[owner_key][tanggal_key]["grup"] += sukses
        else:
            data[owner_key][tanggal_key]["channel"] += sukses

        with open(REKAP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # ⬆️ Upload ke channel backup setiap selesai .buat
        await upload_rekap_to_channel(client)

        # Pesan laporan total
        lines = ["**‼️ Total Grubs and channels created ‼️**"]
        total_grup = 0
        total_channel = 0
        for t, v in sorted(data[owner_key].items()):
            g = v.get("grup", 0)
            c = v.get("channel", 0)
            lines.append(f"```- {t} Total : {g} Grup / {c} Channel```")
            total_grup += g
            total_channel += c

        lines.append("")
        lines.append(f"```Total  keseluruhan : {total_grup} Grup / {total_channel} Channel```")

        await event.respond("\n".join(lines))
    except Exception as e:
        log_error("rekap_save", e)

    for tanya_msg in (session.get("tanya_msg"), session.get("tanya_msg2")):
        if tanya_msg:
            try:
                await tanya_msg.delete()
            except Exception as e:
                log_error("hapus tanya", e)

# HELP
HELP = {
    "buat": [
        ".buat (b|g|c) [jumlah] [nama] → Buat grup/channel otomatis",
        "  b = basic group, g = supergroup, c = channel",
        "  contoh: .buat g 3 GrupTes"
    ]
}
