# broadcast_reply.py — .bc [exme|only|all|help]
# Pakai sebagai reply ke pesan → .bc exme|only|all
#
# Env opsional:
#   - BC_DELAY        (default 0.6)  : jeda antar pengiriman (detik)
#   - BC_AS_COPY      (default "1")  : "1" kirim sebagai salinan; "0" forward biasa
#   - BC_MAX_TARGETS  (default 0)    : 0 = tanpa batas; >0 = batasi jumlah target pertama

import os
import asyncio
from typing import List, Tuple

from telethon import events
from telethon.tl.types import Chat, Channel

BC_DELAY = float(os.getenv("BC_DELAY", "0.6"))
BC_AS_COPY = os.getenv("BC_AS_COPY", "1").strip() not in ("0", "false", "False", "no", "No")
BC_MAX_TARGETS = int(os.getenv("BC_MAX_TARGETS", "0"))

_REGISTERED = False
_HANDLERS = []

async def _del_cmd(event):
    try:
        await event.delete()
        return
    except Exception:
        pass
    try:
        await event.client.delete_messages(event.chat_id, [event.message.id], revoke=True)
    except Exception:
        pass

def _is_group(entity) -> Tuple[bool, bool]:
    """
    Mengembalikan (is_group, is_my_group).
    - is_group: True untuk basic group / supergroup (bukan channel broadcast).
    - is_my_group: True jika kita creator/owner grup tsb.
    """
    if isinstance(entity, Chat):
        return True, bool(getattr(entity, "creator", False))
    if isinstance(entity, Channel):
        is_megagroup = bool(getattr(entity, "megagroup", False) or getattr(entity, "gigagroup", False))
        if not is_megagroup:
            return False, False  # channel broadcast → bukan target
        return True, bool(getattr(entity, "creator", False))
    return False, False

async def _collect_targets(client, mode: str) -> List[int]:
    """
    mode:
      - 'exme' : semua grup yang owner-nya bukan saya
      - 'only' : hanya grup yang owner-nya saya
      - 'all'  : semua grup (kecuali channel broadcast)
    """
    out: List[int] = []
    async for d in client.iter_dialogs():
        is_group, is_my = _is_group(d.entity)
        if not is_group:
            continue
        if mode == "exme" and is_my:
            continue
        if mode == "only" and not is_my:
            continue
        # mode == "all" → tidak filter owner
        out.append(d.id)
        if BC_MAX_TARGETS > 0 and len(out) >= BC_MAX_TARGETS:
            break
    return out

def _usage() -> str:
    return (
        "🆘 Usage:\n"
        "• (Reply ke pesan) `.bc exme` — kirim ke semua grup yang owner-nya bukan kamu (default).\n"
        "• (Reply ke pesan) `.bc only` — kirim hanya ke grup milikmu (creator).\n"
        "• (Reply ke pesan) `.bc all`  — kirim ke semua grup (kecuali channel broadcast).\n"
        "• `.bc help` — tampilkan bantuan.\n\n"
        f"Env: BC_DELAY={BC_DELAY}s, BC_AS_COPY={'1' if BC_AS_COPY else '0'}, BC_MAX_TARGETS={BC_MAX_TARGETS}."
    )

def _setup_handlers(client):
    global _REGISTERED, _HANDLERS
    if _REGISTERED:
        return

    @client.on(events.NewMessage(pattern=r"^\.bc(?:\s+(exme|only|all|help))?$"))
    async def handler_broadcast(event):
        # hapus perintah biar chat bersih (async supaya non-blocking)
        asyncio.create_task(_del_cmd(event))

        m = event.pattern_match
        arg = (m.group(1) or "").lower().strip() if m else ""

        if arg in ("help",):
            await event.respond(_usage(), link_preview=False)
            return

        # default mode: exme
        mode = arg if arg in ("exme", "only", "all") else "exme"

        # Harus reply ke sebuah pesan
        replied = await event.get_reply_message()
        if not replied:
            await event.respond("ℹ️ Pakai `.bc exme|only|all` sebagai *reply* ke pesan yang ingin disiarkan.\n\n" + _usage(), link_preview=False)
            return

        # Kumpulkan target sesuai mode
        targets = await _collect_targets(event.client, mode)
        if not targets:
            await event.client.send_message(event.chat_id, f"⚠️ Tidak ada grup target untuk mode `{mode}`.")
            return

        sent = 0
        failed = 0

        # Kirim ke tiap target
        for chat_id in targets:
            try:
                await event.client.forward_messages(
                    entity=chat_id,
                    messages=replied.id,
                    from_peer=event.chat_id,
                    as_copy=BC_AS_COPY,
                )
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(BC_DELAY)

        # Ringkasan ke chat asal
        try:
            await event.client.send_message(
                event.chat_id,
                (
                    "✅ Broadcast selesai.\n"
                    f"• Mode: {mode}\n"
                    f"• Terkirim: {sent}\n"
                    f"• Gagal: {failed}\n"
                    f"• Target: {len(targets)} grup\n"
                    f"• Mode kirim: {'copy' if BC_AS_COPY else 'forward'}\n"
                    f"• Delay: {BC_DELAY}s"
                )
            )
        except Exception:
            pass

    _HANDLERS[:] = [(handler_broadcast, None)]
    _REGISTERED = True

def _teardown_handlers(client):
    global _REGISTERED, _HANDLERS
    for fn, _ in _HANDLERS:
        try:
            client.remove_event_handler(fn)
        except Exception:
            pass
    _HANDLERS.clear()
    _REGISTERED = False

def init(client):
    _setup_handlers(client)

def register(client):
    _setup_handlers(client)

HELP = {
    "broadcast_reply": [
        "• (Reply) `.bc exme|only|all` — siarkan pesan reply ke grup sesuai mode.",
        "• `exme` = semua grup yang owner-nya bukan kamu (default).",
        "• `only` = hanya grup milikmu (creator).",
        "• `all`  = semua grup (kecuali channel broadcast).",
        "• Env: BC_DELAY, BC_AS_COPY (1/0), BC_MAX_TARGETS.",
    ]
}
