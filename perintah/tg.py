# tg.py — Catbox uploader + DB JSON per owner di channel
# Fitur:
# - .tg m (judul): upload anon ke Catbox → balasan "📎 Berhasil upload : Judul" (auto-delete)
# - .tg all: tampil daftar dari file JSON milik owner → auto-delete (tanpa "by ...")
# - .tg dell: prompt bernomor, balas angka utk hapus; bot EDIT pesan yang sama (anti spam)
# - .tg help: ringkasan bantuan
# - Channel DB: 1 file JSON per owner: tg_uploads_<OWNER_ID>.json (meta.owner_id dsb.)
# - Hapus pesan perintah user otomatis (default ON, atur TG_DELETE_COMMAND=0 utk off)
# - Survive restart: bot cari file JSON milik owner dan lanjut update
# - Idempotent handler (anti dobel)

import os
import io
import html
import json
import asyncio
import mimetypes
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from PIL import Image, UnidentifiedImageError
from telethon import events
from telethon.tl.types import DocumentAttributeFilename

# ──────────────────────────────────────────────────────────────────────────────
# Konfigurasi
# ──────────────────────────────────────────────────────────────────────────────
TEMP_DOWNLOAD_DIRECTORY = "./downloads"
DATA_DIR = "./data"
STATE_FILE = os.path.join(DATA_DIR, "tg_db_state.json")  # mapping owner_id -> msg_id
os.makedirs(TEMP_DOWNLOAD_DIRECTORY, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

CATBOX_API = "https://catbox.moe/user/api.php"
DB_CHANNEL_ID = int(os.getenv("TG_DB_CHANNEL", "-1002933104000"))
TZ = ZoneInfo("Asia/Jakarta")

ALL_MAX_ITEMS = 50
AUTO_DELETE_SEC = int(os.getenv("TG_AUTODEL_SEC", "15"))
# default: ON (hapus pesan perintah user). set "0" utk mematikan
DELETE_COMMAND = os.getenv("TG_DELETE_COMMAND", "1") != "0"

_REGISTERED = False
_HANDLERS = []

# sesi .tg dell: key = prompt_msg_id -> {owner_id, initiator_id, display:[{url,ts_iso,ts_display,judul}]}
_DELL_SESSIONS = {}

# ──────────────────────────────────────────────────────────────────────────────
# Utils
# ──────────────────────────────────────────────────────────────────────────────
def _size_mb(path: str) -> float:
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except OSError:
        return 0.0

def _guess_mime(path: str) -> str:
    mt, _ = mimetypes.guess_type(path)
    return mt or "application/octet-stream"

def _now_jkt() -> datetime:
    return datetime.now(tz=TZ)

def _fmt_display(dt: datetime) -> str:
    return dt.strftime("%d/%m/%y - %H:%M:%S")

def _load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def _save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

async def _autodel(msg, delay: int = AUTO_DELETE_SEC):
    try:
        await asyncio.sleep(delay)
        await msg.delete()
    except Exception:
        pass

async def _del_cmd(event):
    if not DELETE_COMMAND:
        return
    # agresif: coba hapus command user
    try:
        await event.delete()
        return
    except Exception:
        pass
    try:
        await event.client.delete_messages(event.chat_id, [event.message.id], revoke=True)
        return
    except Exception:
        pass
    try:
        await asyncio.sleep(0.3)
        await event.client.delete_messages(event.chat_id, [event.message.id], revoke=True)
    except Exception:
        pass

def convert_webp_to_png(image_path: str) -> str:
    try:
        im = Image.open(image_path)
        if im.mode in ("P", "LA"):
            im = im.convert("RGBA")
        elif im.mode not in ("RGB", "RGBA", "L"):
            im = im.convert("RGBA")
        png_path = image_path.rsplit(".", 1)[0] + ".png"
        im.save(png_path, "PNG", optimize=True)
        try:
            os.remove(image_path)
        except OSError:
            pass
        return png_path
    except (UnidentifiedImageError, OSError):
        return image_path

def _catbox_upload(path: str) -> str:
    if _size_mb(path) <= 0:
        raise RuntimeError("File kosong (0 byte)")
    data = {"reqtype": "fileupload"}
    filename = os.path.basename(path)
    mime = _guess_mime(path)
    with open(path, "rb") as fh:
        files = {"fileToUpload": (filename, fh, mime)}
        try:
            resp = requests.post(
                CATBOX_API, data=data, files=files,
                headers={"User-Agent": "Mozilla/5.0"}, timeout=60
            )
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error: {e}") from e
    text = resp.text.strip()
    if resp.ok and text.startswith("http"):
        return text
    snippet = text[:300].replace("\n", " ")
    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.reason} | body: {snippet!r}")
    if snippet.upper().startswith("ERROR"):
        raise RuntimeError(snippet)
    raise RuntimeError(f"Unexpected response: {snippet!r}")

# ──────────────────────────────────────────────────────────────────────────────
# JSON channel helpers (per owner)
# ──────────────────────────────────────────────────────────────────────────────
def _json_name_for(owner_id: int) -> str:
    return f"tg_uploads_{owner_id}.json"

def _is_json_doc_message(msg, expected_name: str) -> bool:
    if not getattr(msg, "document", None):
        return False
    fname = None
    for attr in getattr(msg.document, "attributes", []) or []:
        if isinstance(attr, DocumentAttributeFilename):
            fname = attr.file_name
            break
    if not fname:
        fname = getattr(getattr(msg, "file", None), "name", None)
    if fname and fname == expected_name:
        return True
    return getattr(msg.document, "mime_type", "") == "application/json"

async def _locate_json_message(client, owner_id: int):
    state = _load_state()
    msg_map = state.get("json_msg_id_map", {})
    msg_id = msg_map.get(str(owner_id))
    want_name = _json_name_for(owner_id)

    if msg_id:
        try:
            msg = await client.get_messages(DB_CHANNEL_ID, ids=msg_id)
            if msg and _is_json_doc_message(msg, want_name):
                return msg
        except Exception:
            pass

    me = await client.get_me()
    try:
        msgs = await client.get_messages(DB_CHANNEL_ID, limit=50, from_user=me)
    except Exception:
        msgs = []

    for m in msgs:
        if _is_json_doc_message(m, want_name):
            msg_map[str(owner_id)] = m.id
            state["json_msg_id_map"] = msg_map
            _save_state(state)
            return m

    return None

async def _download_json_from_msg(client, msg, dest_path: str) -> dict:
    try:
        await client.download_media(msg, file=dest_path)
        with open(dest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return {"meta": {}, "items": data}
        if isinstance(data, dict):
            return {"meta": data.get("meta", {}), "items": data.get("items") or []}
        return {"meta": {}, "items": []}
    except Exception:
        return {"meta": {}, "items": []}

async def _load_json_from_channel(client, owner_id: int) -> tuple[dict, int | None]:
    msg = await _locate_json_message(client, owner_id)
    if not msg:
        return {"meta": {}, "items": []}, None
    tmp_path = os.path.join(DATA_DIR, f"_remote_{_json_name_for(owner_id)}")
    data = await _download_json_from_msg(client, msg, tmp_path)
    return data, msg.id

async def _upload_json_to_channel(client, owner_id: int, data: dict, prev_msg_id: int | None, owner_name: str, owner_username: str | None) -> int:
    now = _now_jkt()
    data = data or {}
    items = data.get("items") or []
    data["meta"] = {
        "db_owner_id": owner_id,
        "db_owner_name": owner_name,
        "db_owner_username": owner_username or "",
        "version": 2,
        "updated_iso": now.isoformat(),
        "updated_display": _fmt_display(now),
    }
    b = io.BytesIO(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
    b.name = _json_name_for(owner_id)
    caption = f"{b.name} ({len(items)} entri)"

    new_msg = await client.send_file(
        DB_CHANNEL_ID, file=b, caption=caption, force_document=True,
        parse_mode="html", link_preview=False
    )

    if prev_msg_id and prev_msg_id != new_msg.id:
        try:
            await client.delete_messages(DB_CHANNEL_ID, prev_msg_id)
        except Exception:
            pass

    state = _load_state()
    msg_map = state.get("json_msg_id_map", {})
    msg_map[str(owner_id)] = new_msg.id
    state["json_msg_id_map"] = msg_map
    _save_state(state)
    return new_msg.id

# ──────────────────────────────────────────────────────────────────────────────
# Handlers (idempotent)
# ──────────────────────────────────────────────────────────────────────────────
def _setup_handlers(client):
    global _REGISTERED, _HANDLERS, _DELL_SESSIONS
    if _REGISTERED:
        return

    async def tg_media(event):
        """`.tg m (Judul)` (balas ke media) → upload ke Catbox & update JSON di channel."""
        me = await event.client.get_me()
        owner_id = int(me.id)
        owner_name = (me.first_name or me.last_name or "User").strip()
        owner_username = (me.username or "").strip()

        m = event.pattern_match
        raw_title = (m.group(1) if m and m.group(1) else "").strip()
        title = raw_title[1:-1].strip() if raw_title.startswith("(") and raw_title.endswith(")") else raw_title

        reply = await event.get_reply_message()
        if not reply:
            msg = await event.reply("❌ Balas ke media dulu, lalu gunakan `.tg m (Judul)`.")
            asyncio.create_task(_autodel(msg))
            asyncio.create_task(_del_cmd(event))
            return

        notice = await event.reply("⏳ Mengunduh media…")
        path = await event.client.download_media(reply, TEMP_DOWNLOAD_DIRECTORY)
        if not path or not os.path.exists(path):
            await notice.edit("❌ Gagal mengunduh media.")
            asyncio.create_task(_autodel(notice))
            asyncio.create_task(_del_cmd(event))
            return

        try:
            if path.lower().endswith(".webp"):
                path = convert_webp_to_png(path)
            size = _size_mb(path)
            await notice.edit(f"⬆️ Mengunggah ke Catbox… ({size:.2f} MB)")

            url = await asyncio.to_thread(_catbox_upload, path)

            now = _now_jkt()
            ts_text = _fmt_display(now)
            link_text = title if title else ts_text
            await notice.edit(
                "📎 Berhasil upload : "
                f"<a href='{html.escape(url)}'>{html.escape(link_text)}</a>",
                parse_mode="html",
                link_preview=True,
            )
            asyncio.create_task(_autodel(notice))

            data, prev_id = await _load_json_from_channel(event.client, owner_id)
            items = data.get("items") or []
            items.append({
                "url": url,
                "judul": title or "",
                "owner_id": owner_id,
                "owner_name": owner_name,
                "owner_username": owner_username or "",
                "ts_iso": now.isoformat(),
                "ts_display": ts_text,
            })
            data["items"] = items
            await _upload_json_to_channel(event.client, owner_id, data, prev_id, owner_name, owner_username)

        except Exception as e:
            await notice.edit(f"❌ Gagal upload media:\n`{type(e).__name__}: {e}`")
            asyncio.create_task(_autodel(notice))
        finally:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
        asyncio.create_task(_del_cmd(event))

    async def tg_all(event):
        """`.tg all` → tampil list dari JSON owner di channel (auto-delete)."""
        me = await event.client.get_me()
        owner_id = int(me.id)

        data, _prev = await _load_json_from_channel(event.client, owner_id)
        items = data.get("items") or []
        if not items:
            msg = await event.reply("ℹ️ Belum ada data di channel untuk owner ini (file JSON belum dibuat).")
            asyncio.create_task(_autodel(msg))
            asyncio.create_task(_del_cmd(event))
            return

        tail = items[-ALL_MAX_ITEMS:]
        lines = ["📎Beberapa file yang berhasil diupload:"]
        for i, row in enumerate(tail, start=1):
            url = row.get("url", "")
            ts = row.get("ts_display") or row.get("ts_iso", "")
            judul = row.get("judul") or ""
            judul_disp = judul if judul else "tanpa judul"
            lines.append(f"{i}. ({ts} ({url})) - ({judul_disp})")

        msg = await event.reply("\n".join(lines), parse_mode=None, link_preview=False)
        asyncio.create_task(_autodel(msg))
        asyncio.create_task(_del_cmd(event))

    async def tg_dell(event):
        """
        `.tg dell` → tampil list bernomor; balas angka untuk hapus.
        Bot akan EDIT pesan prompt yang sama (nggak menumpuk).
        """
        me = await event.client.get_me()
        owner_id = int(me.id)
        initiator_id = int(event.sender_id or owner_id)

        data, _prev = await _load_json_from_channel(event.client, owner_id)
        items = data.get("items") or []
        if not items:
            msg = await event.reply("ℹ️ Belum ada data untuk dihapus.")
            asyncio.create_task(_autodel(msg))
            asyncio.create_task(_del_cmd(event))
            return

        tail = items[-ALL_MAX_ITEMS:]
        display = [
            {"url": r.get("url",""), "ts_iso": r.get("ts_iso",""), "ts_display": r.get("ts_display",""), "judul": r.get("judul","") or ""}
            for r in tail
        ]

        header = "📎Ketik Nomor untuk menghapus file :"
        lines = [header]
        for i, r in enumerate(display, start=1):
            url = r["url"]; ts = r["ts_display"] or r["ts_iso"]; judul = r["judul"] or "tanpa judul"
            lines.append(f"{i}. ({ts} ({url})) - ({judul})")

        prompt = await event.reply("\n".join(lines), parse_mode=None, link_preview=False)

        _DELL_SESSIONS[prompt.id] = {
            "owner_id": owner_id,
            "initiator_id": initiator_id,
            "display": display,
        }
        asyncio.create_task(_del_cmd(event))

    async def tg_dell_pick(event):
        """Balasan angka utk hapus; harus reply ke prompt `.tg dell` milik bot."""
        if not event.is_reply or not event.reply_to_msg_id:
            return
        sess = _DELL_SESSIONS.get(event.reply_to_msg_id)
        if not sess:
            return
        if int(event.sender_id or 0) != int(sess["initiator_id"]):
            return

        asyncio.create_task(_del_cmd(event))  # hapus angka user

        text = (event.raw_text or "").strip()
        if not text.isdigit():
            return
        pick = int(text)
        display = sess.get("display") or []
        if pick < 1 or pick > len(display):
            try:
                prompt = await event.get_reply_message()
                await event.client.edit_message(
                    prompt.chat_id, prompt.id,
                    "❌ Nomor tidak valid.\n" + prompt.message,
                    parse_mode=None, link_preview=False
                )
            except Exception:
                pass
            return

        chosen = display[pick - 1]
        owner_id = sess["owner_id"]

        data, prev_id = await _load_json_from_channel(event.client, owner_id)
        items = data.get("items") or []

        idx_to_del = -1
        for i, r in enumerate(items):
            if r.get("url") == chosen["url"] and (r.get("ts_iso") == chosen["ts_iso"] or r.get("ts_display") == chosen["ts_display"]):
                idx_to_del = i
                break

        if idx_to_del == -1:
            # refresh daftar
            tail = items[-ALL_MAX_ITEMS:]
            new_display = [
                {"url": r.get("url",""), "ts_iso": r.get("ts_iso",""), "ts_display": r.get("ts_display",""), "judul": r.get("judul","") or ""}
                for r in tail
            ]
            sess["display"] = new_display
            lines = ["⚠️ Item tidak ditemukan (daftar diperbarui).", "📎Ketik Nomor untuk menghapus file :"]
            for i, r in enumerate(new_display, start=1):
                url = r["url"]; ts = r["ts_display"] or r["ts_iso"]; judul = r["judul"] or "tanpa judul"
                lines.append(f"{i}. ({ts} ({url})) - ({judul})")
            try:
                prompt = await event.get_reply_message()
                await event.client.edit_message(prompt.chat_id, prompt.id, "\n".join(lines), parse_mode=None, link_preview=False)
            except Exception:
                pass
            return

        # hapus & unggah ulang JSON
        del items[idx_to_del]
        data["items"] = items
        me = await event.client.get_me()
        await _upload_json_to_channel(event.client, owner_id, data, prev_id, me.first_name or "User", me.username or "")

        # edit prompt dengan daftar terbaru
        tail = items[-ALL_MAX_ITEMS:]
        new_display = [
            {"url": r.get("url",""), "ts_iso": r.get("ts_iso",""), "ts_display": r.get("ts_display",""), "judul": r.get("judul","") or ""}
            for r in tail
        ]
        sess["display"] = new_display
        lines = [f"✅ Terhapus item #{pick}", "📎Ketik Nomor untuk menghapus file :"]
        for i, r in enumerate(new_display, start=1):
            url = r["url"]; ts = r["ts_display"] or r["ts_iso"]; judul = r["judul"] or "tanpa judul"
            lines.append(f"{i}. ({ts} ({url})) - ({judul})")
        try:
            prompt = await event.get_reply_message()
            await event.client.edit_message(prompt.chat_id, prompt.id, "\n".join(lines), parse_mode=None, link_preview=False)
        except Exception:
            pass

    async def tg_help(event):
        """`.tg help` → bantuan singkat."""
        lines = [
            "🆘 Help: tg",
            "• `.tg m (judul)` — Balas ke media untuk upload ke Catbox (balasan auto-delete).",
            "• `.tg all` — Tampilkan daftar dari file JSON milik owner (auto-delete).",
            "• `.tg dell` — Tampilkan daftar bernomor, balas angka untuk hapus (pesan akan di-edit).",
            "",
            f"Env: TG_DB_CHANNEL={DB_CHANNEL_ID}, TG_AUTODEL_SEC={AUTO_DELETE_SEC}, TG_DELETE_COMMAND={'ON' if DELETE_COMMAND else 'OFF'}",
        ]
        msg = await event.reply("\n".join(lines), link_preview=False)
        asyncio.create_task(_autodel(msg))
        asyncio.create_task(_del_cmd(event))

    # ── registrasi handler ─────────────────────────────────────────────────────
    ev_media = events.NewMessage(pattern=r"^\.tg\s+m(?:\s+(.*))?$")
    ev_all   = events.NewMessage(pattern=r"^\.tg\s+all$")
    ev_dell  = events.NewMessage(pattern=r"^\.tg\s+dell$")
    ev_dpick = events.NewMessage(pattern=r"^\d{1,4}$")       # balasan angka
    ev_help  = events.NewMessage(pattern=r"^\.tg\s+help$")

    client.add_event_handler(tg_media, ev_media)
    client.add_event_handler(tg_all,   ev_all)
    client.add_event_handler(tg_dell,  ev_dell)
    client.add_event_handler(tg_dell_pick, ev_dpick)
    client.add_event_handler(tg_help,  ev_help)

    _HANDLERS[:] = [
        (tg_media, ev_media),
        (tg_all,   ev_all),
        (tg_dell,  ev_dell),
        (tg_dell_pick, ev_dpick),
        (tg_help,  ev_help),
    ]
    _REGISTERED = True

def _teardown_handlers(client):
    global _REGISTERED, _HANDLERS, _DELL_SESSIONS
    for fn, ev in _HANDLERS:
        try:
            client.remove_event_handler(fn, ev)
        except Exception:
            pass
    _HANDLERS.clear()
    _DELL_SESSIONS.clear()
    _REGISTERED = False

def init(client):
    _setup_handlers(client)

def register(client):
    _setup_handlers(client)

# Help untuk loader help.py
HELP = {
    "tg": [
        "• `.tg m (judul)` → Balas ke media untuk upload ke Catbox; balasan auto-delete; "
        "disimpan ke channel sebagai file JSON per owner (tg_uploads_<OWNER_ID>.json).",
        "• `.tg all` → Tampilkan daftar dari file JSON milik owner; auto-delete.",
        "• `.tg dell` → Hapus item via nomor; balas angka ke prompt (pesan di-edit, tidak numpuk).",
        "• `.tg help` → Tampilkan bantuan singkat.",
        "Env: TG_DB_CHANNEL (default -1002933104000), TG_AUTODEL_SEC (default 15), TG_DELETE_COMMAND=1.",
    ]
}
