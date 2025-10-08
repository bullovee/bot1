# tg.py — Catbox uploader + .tg m (judul) + DB channel: 1 file JSON per owner + .tg all
# - File channel: tg_uploads_<OWNER_ID>.json, berisi meta {db_owner_id,...} + items[]
# - .tg m (judul): balasan "📎 Berhasil upload : Judul" (link)
# - .tg all: baca dari file JSON milik owner saat ini
# - Setelah restart: bot cari file JSON yang sesuai owner dan lanjut update
# - Idempotent handler (anti-dobel)

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

_REGISTERED = False
_HANDLERS = []

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

def _mention_html(user_id: int, name: str, username: str | None) -> str:
    safe_name = html.escape(name) if name else "User"
    if username:
        text = html.escape("@" + username.lstrip("@"))
    else:
        text = safe_name
    return f"<a href='tg://user?id={user_id}'>{text}</a>"

def convert_webp_to_png(image_path: str) -> str:
    try:
        im = Image.open(image_path)
        if im.mode in ("P", "LA"):
            im = im.convert("RGBA")
        elif im.mode not in ("RGB", "RGBA", "L"):
            im = im.convert("RGBA")
        png_path = image_path.rsplit(".", 1)[0] + ".png"
        im.save(png_path, "PNG", optimize=True)
        try: os.remove(image_path)
        except OSError: pass
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
    if not resp.ok: raise RuntimeError(f"HTTP {resp.status_code}: {resp.reason} | body: {snippet!r}")
    if snippet.upper().startswith("ERROR"): raise RuntimeError(snippet)
    raise RuntimeError(f"Unexpected response: {snippet!r}")

# ──────────────────────────────────────────────────────────────────────────────
# JSON channel helpers
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
    """
    Cari dok JSON sesuai owner:
      1) coba pakai id dari state['json_msg_id_map'][owner_id]
      2) fallback: cari 50 pesan terakhir dari akun ini, yang namanya tg_uploads_<owner_id>.json
    """
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
        # dukung format lama (list)
        if isinstance(data, list):
            return {"meta": {}, "items": data}
        if isinstance(data, dict):
            items = data.get("items")
            if isinstance(items, list):
                return data
            # jika dict tapi tak ada items → treat sebagai kosong
            return {"meta": data.get("meta", {}), "items": []}
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

    # hapus yang lama bila berbeda
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
    global _REGISTERED, _HANDLERS
    if _REGISTERED:
        return

    async def tg_media(event):
        """
        Balas ke media, ketik:
          • `.tg m (Judul)` atau `.tg m Judul`
          • tanpa judul: `.tg m`
        Hasil di chat: "📎 Berhasil upload : Judul"
        Channel DB: satu dokumen JSON per owner yang selalu di-replace.
        """
        # Owner info (pemilik userbot ini)
        me = await event.client.get_me()
        owner_id = int(me.id)
        owner_name = (me.first_name or me.last_name or "User").strip()
        owner_username = (me.username or "").strip()

        # Ambil judul (opsional) dan bersihkan tanda kurung
        m = event.pattern_match
        raw_title = (m.group(1) if m and m.group(1) else "").strip()
        title = raw_title[1:-1].strip() if raw_title.startswith("(") and raw_title.endswith(")") else raw_title

        reply = await event.get_reply_message()
        if not reply:
            await event.reply("❌ Balas ke media dulu, lalu gunakan `.tg m (Judul)`.")
            return

        notice = await event.reply("⏳ Mengunduh media…")
        path = await event.client.download_media(reply, TEMP_DOWNLOAD_DIRECTORY)
        if not path or not os.path.exists(path):
            await notice.edit("❌ Gagal mengunduh media.")
            return

        try:
            if path.lower().endswith(".webp"):
                path = convert_webp_to_png(path)
            size = _size_mb(path)
            await notice.edit(f"⬆️ Mengunggah ke Catbox… ({size:.2f} MB)")

            url = await asyncio.to_thread(_catbox_upload, path)

            # Balasan ke user
            now = _now_jkt()
            ts_text = _fmt_display(now)
            link_text = title if title else ts_text
            await notice.edit(
                "📎 Berhasil upload : "
                f"<a href='{html.escape(url)}'>{html.escape(link_text)}</a>",
                parse_mode="html",
                link_preview=True,
            )

            # Load JSON milik owner dari channel, append item, lalu upload ulang
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
        finally:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass

    async def tg_all(event):
        """
        Tampilkan daftar dari file JSON milik owner saat ini di channel.
        """
        me = await event.client.get_me()
        owner_id = int(me.id)

        data, _prev = await _load_json_from_channel(event.client, owner_id)
        items = data.get("items") or []
        if not items:
            await event.reply("ℹ️ Belum ada data di channel untuk owner ini (file JSON belum dibuat).")
            return

        tail = items[-ALL_MAX_ITEMS:]
        lines = ["📎Beberapa file yang berhasil diupload:"]
        for i, row in enumerate(tail, start=1):
            url = row.get("url", "")
            ts = row.get("ts_display") or row.get("ts_iso", "")
            judul = row.get("judul") or ""
            judul_disp = judul if judul else "tanpa judul"
            oid = int(row.get("owner_id") or 0)
            oname = row.get("owner_name") or "User"
            ouser = row.get("owner_username") or ""
            lines.append(
                f"{i}. (<a href='{html.escape(url)}'>{html.escape(ts)}</a>) - "
                f"({html.escape(judul_disp)}) • by {_mention_html(oid, oname, ouser or None)}"
            )
        await event.reply("\n".join(lines), parse_mode="html", link_preview=False)

    ev_media = events.NewMessage(pattern=r"^\.tg\s+m(?:\s+(.*))?$")
    ev_all = events.NewMessage(pattern=r"^\.tg\s+all$")

    client.add_event_handler(tg_media, ev_media)
    client.add_event_handler(tg_all, ev_all)

    _HANDLERS[:] = [(tg_media, ev_media), (tg_all, ev_all)]
    _REGISTERED = True

def _teardown_handlers(client):
    global _REGISTERED, _HANDLERS
    for fn, ev in _HANDLERS:
        try:
            client.remove_event_handler(fn, ev)
        except Exception:
            pass
    _HANDLERS.clear()
    _REGISTERED = False

def init(client):
    _setup_handlers(client)

def register(client):
    _setup_handlers(client)
