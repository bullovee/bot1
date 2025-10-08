# cekgrub.py — Daftar grup yang kamu miliki (owner)
# Perintah:
#   .cekmygrub  / .cekmyygrub → tampilkan NAMA semua grup/supergroup yang kamu miliki (tanpa link)
#   .mygrub                   → tampilkan jumlah grup yang kamu miliki
#
# Fitur:
# - Pesan perintah otomatis DIHAPUS.
# - Tampilkan loading, lalu edit jadi hasil.
# - Jika daftar terlalu panjang, hapus loading & kirim sebagai file .txt (anti MessageTooLong).

import io
import asyncio
from typing import List

from telethon import events
from telethon.errors import MessageTooLongError, FloodWaitError
from telethon.tl.types import Chat, Channel, ChannelParticipantCreator
from telethon.tl.functions.channels import GetParticipantRequest

_MAX_TEXT_CHARS = 3500  # buffer aman di bawah limit Telegram
_REGISTERED = False
_HANDLERS = []


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


def _split_chunks_by_chars(lines: List[str], max_chars: int) -> List[str]:
    """Bagi daftar baris menjadi beberapa blok agar tiap blok <= max_chars."""
    chunks = []
    cur = "Berikut ini adalah grub yang kamu miliki\n"
    for line in lines:
        candidate = cur + line + "\n"
        if len(candidate) > max_chars:
            chunks.append(cur.rstrip())
            cur = line + "\n"
        else:
            cur = candidate
    if cur.strip():
        chunks.append(cur.rstrip())
    return chunks


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


def _setup_handlers(client):
    global _REGISTERED, _HANDLERS
    if _REGISTERED:
        return

    # .cekmygrub / .cekmyygrub → daftar NAMA
    @client.on(events.NewMessage(pattern=r"^\.cekmygrub$|^\.cekmyygrub$"))
    async def cek_my_grub(event):
        # Hapus perintah & tampilkan loading
        asyncio.create_task(_del_cmd(event))
        loading = await event.reply("⏳ Mengumpulkan daftar grup yang kamu miliki…")

        # Kumpulkan NAMA group/supergroup yang kamu miliki
        owned_names: List[str] = []
        async for dialog in event.client.iter_dialogs():
            ent = dialog.entity
            if not _is_group_dialog(ent):
                continue
            try:
                if await _is_owner(event.client, ent):
                    title = getattr(ent, "title", None) or getattr(ent, "username", None) or "Tanpa Judul"
                    owned_names.append(str(title))
            except Exception:
                pass

        if not owned_names:
            await loading.edit("ℹ️ Tidak ditemukan grup yang kamu miliki.", link_preview=False)
            return

        # Format daftar nama (tanpa link)
        lines = [f"{i}. {name}" for i, name in enumerate(owned_names, start=1)]
        full_text = "Berikut ini adalah grub yang kamu miliki\n" + "\n".join(lines)

        if len(full_text) <= _MAX_TEXT_CHARS:
            await loading.edit(full_text, link_preview=False)
            return

        # Terlalu panjang → hapus loading & kirim sebagai file .txt
        try:
            await loading.delete()
        except Exception:
            pass

        bio = io.BytesIO(full_text.encode("utf-8"))
        bio.name = "grup_yang_kamu_miliki.txt"
        try:
            await event.client.send_file(
                event.chat_id,
                bio,
                caption="📄 Daftar nama grup milikmu dikirim sebagai file (terlalu panjang untuk pesan).",
                force_document=True,
                link_preview=False,
            )
        except MessageTooLongError:
            # Fallback terakhir: pecah menjadi beberapa pesan
            for chunk in _split_chunks_by_chars(lines, _MAX_TEXT_CHARS):
                await event.reply(chunk, link_preview=False)

    # .mygrub → jumlah saja
    @client.on(events.NewMessage(pattern=r"^\.mygrub$"))
    async def my_grub_count(event):
        # Hapus perintah & tampilkan loading
        asyncio.create_task(_del_cmd(event))
        loading = await event.reply("⏳ Menghitung grup yang kamu miliki…")

        count = 0
        async for dialog in event.client.iter_dialogs():
            ent = dialog.entity
            if not _is_group_dialog(ent):
                continue
            try:
                if await _is_owner(event.client, ent):
                    count += 1
            except Exception:
                pass

        await loading.edit(f"📊 Kamu adalah owner dari **{count}** grup.", parse_mode="md", link_preview=False)

    _HANDLERS[:] = [(cek_my_grub, None), (my_grub_count, None)]
    _REGISTERED = True


def init(client):
    _setup_handlers(client)


def register(client):
    _setup_handlers(client)


# Help untuk loader help.py (opsional)
HELP = {
    "cekgrub": [
        "• `.cekmygrub` / `.cekmyygrub` → Tampilkan NAMA semua grup/supergroup yang kamu miliki (tanpa link).",
        "• `.mygrub` → Tampilkan jumlah grup yang kamu miliki (owner).",
        "• Pesan perintah otomatis dihapus, ada loading sebelum hasil.",
    ]
}
