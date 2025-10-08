# pesan_random.py — Kirim pesan acak dari perintah/random_messages.py
# Perintah:
#   .send N           → kirim N pesan random ke chat ini (pesan perintah otomatis DIHAPUS)
#   .send all N       → kirim N pesan random ke SEMUA grup yang kamu miliki (owner)
#   .send help        → bantuan singkat
#
# Sumber pesan (pilih yang tersedia di perintah/random_messages.py):
#   - get_messages() -> list[str]
#   - RANDOM_MESSAGES: list[str]
#   - MESSAGES: list[str]
#
# Env opsional:
#   - SEND_RANDOM_MAX            (default 20) : batas maksimum saat input VALID
#   - SEND_RANDOM_DELAY          (default 0.6): jeda antar pesan
#   - SEND_RANDOM_FALLBACK_MAX   (default 12) : batas saat input ERROR/SALAH KETIK
#   - SEND_ALL_MAX_GROUPS        (default 100): batas jumlah grup diproses saat .send all
#
# Catatan:
# - Jika terjadi error/salah ketik pada N, bot tetap kirim pesan random Fallback Max (default 12) — dan tidak pernah lebih dari 12.
# - .send all hanya menargetkan group/supergroup yang KAMU miliki (creator/owner), bukan channel broadcast.

import os
import asyncio
import random
from typing import List, Optional, Tuple

from telethon import events
from telethon.errors import FloodWaitError
from telethon.tl.types import Chat, Channel, ChannelParticipantCreator
from telethon.tl.functions.channels import GetParticipantRequest

# ──────────────────────────────────────────────────────────────────────────────
# Konfigurasi
# ──────────────────────────────────────────────────────────────────────────────
SEND_RANDOM_MAX = int(os.getenv("SEND_RANDOM_MAX", "20"))              # input VALID
SEND_RANDOM_DELAY = float(os.getenv("SEND_RANDOM_DELAY", "0.8"))
FALLBACK_MAX = int(os.getenv("SEND_RANDOM_FALLBACK_MAX", "12"))        # input ERROR
SEND_ALL_MAX_GROUPS = int(os.getenv("SEND_ALL_MAX_GROUPS", "300"))

_REGISTERED = False
_HANDLERS = []

# ──────────────────────────────────────────────────────────────────────────────
# Loader pesan dari perintah/random_messages.py
# ──────────────────────────────────────────────────────────────────────────────
def _load_pool() -> List[str]:
    """
    Ambil list pesan dari perintah/random_messages.py.
    Prioritas: get_messages() -> RANDOM_MESSAGES -> MESSAGES.
    """
    msgs: Optional[List[str]] = None
    try:
        from .random_messages import get_messages as _rm_get  # type: ignore
        try:
            res = _rm_get()
            if isinstance(res, (list, tuple)):
                msgs = list(res)
        except Exception:
            msgs = None
    except Exception:
        msgs = None

    if msgs is None:
        try:
            from .random_messages import RANDOM_MESSAGES as _RM_LIST  # type: ignore
            if isinstance(_RM_LIST, (list, tuple)):
                msgs = list(_RM_LIST)
        except Exception:
            msgs = None

    if msgs is None:
        try:
            from .random_messages import MESSAGES as _RM_LIST2  # type: ignore
            if isinstance(_RM_LIST2, (list, tuple)):
                msgs = list(_RM_LIST2)
        except Exception:
            msgs = None

    if not msgs:
        return []
    # normalisasi: hanya string & tidak kosong
    clean = [str(x).strip() for x in msgs if isinstance(x, str) and str(x).strip()]
    return clean

def _pick_random(pool: List[str], n: int) -> List[str]:
    """
    Ambil n item acak. Jika n <= len(pool) → sample tanpa duplikasi.
    Jika n > len(pool) → ambil sample tanpa duplikasi sebanyak pool, sisanya dengan pengulangan.
    """
    if not pool or n <= 0:
        return []
    if n <= len(pool):
        return random.sample(pool, n)
    picked = random.sample(pool, len(pool))
    picked += random.choices(pool, k=(n - len(pool)))
    return picked

# ──────────────────────────────────────────────────────────────────────────────
# Helpers umum
# ──────────────────────────────────────────────────────────────────────────────
async def _del_cmd(event):
    """Hapus pesan perintah pengguna, dengan beberapa fallback agar tidak numpuk."""
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
        await asyncio.sleep(0.2)
        await event.client.delete_messages(event.chat_id, [event.message.id], revoke=True)
    except Exception:
        pass

def _is_group_dialog(entity) -> bool:
    """Apakah dialog ini group/supergroup (bukan channel broadcast)."""
    if isinstance(entity, Chat):
        return True
    if isinstance(entity, Channel):
        return bool(getattr(entity, "megagroup", False))
    return False

async def _is_owner(client, entity) -> bool:
    """True jika current user adalah owner/creator dari grup/supergroup."""
    # Small group (Chat)
    if isinstance(entity, Chat):
        return bool(getattr(entity, "creator", False))

    # Supergroup (Channel dengan megagroup=True)
    if isinstance(entity, Channel) and bool(getattr(entity, "megagroup", False)):
        me = await client.get_me()
        try:
            res = await client(GetParticipantRequest(entity, me))
            return isinstance(res.participant, ChannelParticipantCreator)
        except FloodWaitError as e:
            # Tangani flood-wait: tunggu, lalu coba sekali lagi
            try:
                await asyncio.sleep(getattr(e, "seconds", 5) + 1)
                res = await client(GetParticipantRequest(entity, me))
                return isinstance(res.participant, ChannelParticipantCreator)
            except Exception:
                return False
        except Exception:
            return False
    return False

async def _iter_owned_groups(client) -> List[Tuple[int, str]]:
    """
    Kembalikan list (chat_id, title) untuk semua grup yang kamu miliki (owner).
    """
    owned = []
    async for dialog in client.iter_dialogs():
        ent = dialog.entity
        if not _is_group_dialog(ent):
            continue
        try:
            if await _is_owner(client, ent):
                title = getattr(ent, "title", None) or getattr(ent, "username", None) or "Tanpa Judul"
                owned.append((dialog.id, str(title)))
        except Exception:
            pass
        if len(owned) >= SEND_ALL_MAX_GROUPS:
            break
    return owned

# ──────────────────────────────────────────────────────────────────────────────
# Handlers
# ──────────────────────────────────────────────────────────────────────────────
def _setup_handlers(client):
    global _REGISTERED, _HANDLERS
    if _REGISTERED:
        return

    # ── .send N (ke chat saat ini) ────────────────────────────────────────────
    async def send_random(event):
        # HAPUS PERINTAH di awal supaya chat bersih
        asyncio.create_task(_del_cmd(event))

        m = event.pattern_match
        n_raw = m.group(1) if m else None

        fallback_used = False
        if not n_raw:
            fallback_used = True
            n = FALLBACK_MAX
        else:
            try:
                n = int(n_raw)
                if n <= 0:
                    fallback_used = True
                    n = FALLBACK_MAX
            except ValueError:
                fallback_used = True
                n = FALLBACK_MAX

        # Pembatasan jumlah
        if fallback_used:
            n = min(n, FALLBACK_MAX, SEND_RANDOM_MAX)   # maks 12 saat fallback
        else:
            n = min(n, SEND_RANDOM_MAX)

        pool = _load_pool()
        if not pool:
            await event.client.send_message(event.chat_id, "ℹ️ Belum ada daftar pesan di `perintah/random_messages.py`.")
            return

        picks = _pick_random(pool, n)

        # Kirim satu-satu dengan jeda kecil
        for text in picks:
            try:
                await event.client.send_message(event.chat_id, text, link_preview=False)
            except FloodWaitError as e:
                await asyncio.sleep(getattr(e, "seconds", 5) + 1)
                try:
                    await event.client.send_message(event.chat_id, text, link_preview=False)
                except Exception:
                    pass
            except Exception:
                pass
            await asyncio.sleep(SEND_RANDOM_DELAY)

    # ── .send all N (ke semua grup yang kamu miliki) ──────────────────────────
    async def send_all_groups(event):
        # HAPUS PERINTAH & tampilkan loading ringkas
        asyncio.create_task(_del_cmd(event))
        m = event.pattern_match
        n_raw = m.group(1) if m else None

        fallback_used = False
        if not n_raw:
            fallback_used = True
            n = FALLBACK_MAX
        else:
            try:
                n = int(n_raw)
                if n <= 0:
                    fallback_used = True
                    n = FALLBACK_MAX
            except ValueError:
                fallback_used = True
                n = FALLBACK_MAX

        # Pembatasan jumlah per grup
        if fallback_used:
            n = min(n, FALLBACK_MAX, SEND_RANDOM_MAX)   # maks 12 saat fallback
        else:
            n = min(n, SEND_RANDOM_MAX)

        pool = _load_pool()
        if not pool:
            await event.reply("ℹ️ Belum ada daftar pesan di `perintah/random_messages.py`.")
            return

        loading = await event.reply(f"⏳ Menyiapkan pengiriman ke semua grup milikmu…")

        # Ambil semua grup yang kamu miliki (dibatasi SEND_ALL_MAX_GROUPS)
        groups = await _iter_owned_groups(event.client)
        total_groups = len(groups)
        if total_groups == 0:
            await loading.edit("ℹ️ Tidak ada grup yang kamu miliki (owner) untuk dikirimi pesan.")
            return

        # Kirim ke tiap grup
        sent_groups = 0
        for chat_id, title in groups:
            picks = _pick_random(pool, n)
            for text in picks:
                try:
                    await event.client.send_message(chat_id, text, link_preview=False)
                except FloodWaitError as e:
                    await asyncio.sleep(getattr(e, "seconds", 5) + 1)
                    try:
                        await event.client.send_message(chat_id, text, link_preview=False)
                    except Exception:
                        pass
                except Exception:
                    pass
                await asyncio.sleep(SEND_RANDOM_DELAY)
            sent_groups += 1
            # update progress ringan tiap grup
            try:
                await loading.edit(f"⏳ Mengirim… {sent_groups}/{total_groups} grup (≈{n} pesan/grup)")
            except Exception:
                pass

        await loading.edit(f"✅ Selesai: terkirim ke {sent_groups}/{total_groups} grup (≈{n} pesan/grup).")

    async def send_help(event):
        # HAPUS PERINTAH help juga
        asyncio.create_task(_del_cmd(event))
        lines = [
            "🆘 Help: pesan_random",
            "• `.send N` — kirim N pesan acak ke chat ini.",
            "• `.send all N` — kirim N pesan acak ke SEMUA grup yang kamu miliki (owner).",
            "  Sumber: `get_messages()` / `RANDOM_MESSAGES` / `MESSAGES` di `perintah/random_messages.py`.",
            f"• Batas input valid per grup: {SEND_RANDOM_MAX} (env SEND_RANDOM_MAX).",
            f"• Jika error/salah ketik: kirim maksimal {FALLBACK_MAX} (env SEND_RANDOM_FALLBACK_MAX, default 12).",
            f"• Jeda antar pesan: {SEND_RANDOM_DELAY}s (env SEND_RANDOM_DELAY).",
            f"• Batas jumlah grup saat `.send all`: {SEND_ALL_MAX_GROUPS} (env SEND_ALL_MAX_GROUPS).",
            "Contoh: `.send 5`, `.send all 3`",
        ]
        await event.reply("\n".join(lines), link_preview=False)

    ev_send = events.NewMessage(pattern=r"^\.send(?:\s+(\S+))?$")
    ev_send_all = events.NewMessage(pattern=r"^\.send\s+all(?:\s+(\S+))?$")
    ev_help = events.NewMessage(pattern=r"^\.send\s+help$")

    client.add_event_handler(send_random, ev_send)
    client.add_event_handler(send_all_groups, ev_send_all)
    client.add_event_handler(send_help, ev_help)

    _HANDLERS[:] = [(send_random, ev_send), (send_all_groups, ev_send_all), (send_help, ev_help)]
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

# Untuk sistem help loader
HELP = {
    "pesan_random": [
        "• `.send N` → Kirim N pesan acak ke chat ini.",
        "• `.send all N` → Kirim N pesan acak ke SEMUA grup yang kamu miliki (owner).",
        "• `.send help` → Bantuan.",
        "• Input error/salah ketik → kirim maksimal 12 (env SEND_RANDOM_FALLBACK_MAX).",
        "Env: SEND_RANDOM_MAX (default 20), SEND_RANDOM_DELAY (default 0.6), SEND_ALL_MAX_GROUPS (default 100).",
    ]
}
