# pesan_random.py — Kirim pesan acak dari perintah/random_messages.py
# Perintah:
#   .send N        → kirim N pesan random ke chat ini (pesan perintah otomatis DIHAPUS)
#   .send help     → bantuan singkat (pesan perintah otomatis DIHAPUS)
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
#
# Catatan: Jika terjadi error/salah ketik pada N, bot tetap kirim pesan random
# sebanyak Fallback Max (default 12) — dan TIDAK PERNAH lebih dari 12.

import os
import asyncio
import random
from typing import List, Optional

from telethon import events

# ──────────────────────────────────────────────────────────────────────────────
# Konfigurasi
# ──────────────────────────────────────────────────────────────────────────────
SEND_RANDOM_MAX = int(os.getenv("SEND_RANDOM_MAX", "20"))              # input VALID
SEND_RANDOM_DELAY = float(os.getenv("SEND_RANDOM_DELAY", "0.6"))
FALLBACK_MAX = int(os.getenv("SEND_RANDOM_FALLBACK_MAX", "12"))        # input ERROR

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
# Helper: selalu hapus pesan perintah user
# ──────────────────────────────────────────────────────────────────────────────
async def _del_cmd(event):
    # 1) coba hapus langsung
    try:
        await event.delete()
        return
    except Exception:
        pass
    # 2) fallback via delete_messages
    try:
        await event.client.delete_messages(event.chat_id, [event.message.id], revoke=True)
        return
    except Exception:
        pass
    # 3) fallback terakhir dengan delay kecil
    try:
        await asyncio.sleep(0.2)
        await event.client.delete_messages(event.chat_id, [event.message.id], revoke=True)
    except Exception:
        pass

# ──────────────────────────────────────────────────────────────────────────────
# Handlers
# ──────────────────────────────────────────────────────────────────────────────
def _setup_handlers(client):
    global _REGISTERED, _HANDLERS
    if _REGISTERED:
        return

    async def send_random(event):
        """
        .send N → kirim N pesan random dari pool
        - Jika N tidak ada / bukan angka / <= 0 → gunakan FALLBACK_MAX (default 12)
        - Saat fallback, jumlah TIDAK PERNAH melebihi 12.
        """
        # HAPUS PERINTAH diawal supaya chat bersih
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
            except Exception:
                pass
            await asyncio.sleep(SEND_RANDOM_DELAY)

    async def send_help(event):
        # HAPUS PERINTAH help juga
        asyncio.create_task(_del_cmd(event))
        lines = [
            "🆘 Help: pesan_random",
            "• `.send N` — kirim N pesan acak dari `perintah/random_messages.py`.",
            "  Sumber: `get_messages()` / `RANDOM_MESSAGES` / `MESSAGES`.",
            f"• Batas maksimum input valid: {SEND_RANDOM_MAX} (env SEND_RANDOM_MAX).",
            f"• Jika error/salah ketik: kirim maksimal {FALLBACK_MAX} (env SEND_RANDOM_FALLBACK_MAX, default 12).",
            f"• Jeda antar pesan: {SEND_RANDOM_DELAY}s (env SEND_RANDOM_DELAY).",
            "Contoh: `.send 5`",
        ]
        await event.reply("\n".join(lines), link_preview=False)

    ev_send = events.NewMessage(pattern=r"^\.send(?:\s+(\S+))?$")
    ev_help = events.NewMessage(pattern=r"^\.send\s+help$")

    client.add_event_handler(send_random, ev_send)
    client.add_event_handler(send_help, ev_help)

    _HANDLERS[:] = [(send_random, ev_send), (send_help, ev_help)]
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
        "• `.send N` → Kirim N pesan acak dari perintah/random_messages.py",
        "• `.send help` → Bantuan.",
        "• Input error/salah ketik → kirim maksimal 12 (ubah via env SEND_RANDOM_FALLBACK_MAX).",
        "Env: SEND_RANDOM_MAX (default 20), SEND_RANDOM_DELAY (default 0.6).",
    ]
}
