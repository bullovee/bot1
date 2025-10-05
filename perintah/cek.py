"""
userinfo.py
Perintah: .cek
Deskripsi: Cek info lengkap untuk user / grup / channel.
Cara pakai:
 - .cek (reply ke pesan user)  -> edit pesan perintah dengan info
 - .cek <id|@username>         -> edit pesan perintah dengan info

Catatan:
 - Dijalankan sebagai modul Telethon userbot (init(client) dipanggil oleh loader)
 - Beberapa field memerlukan hak akses atau tidak tersedia tergantung privasi target
 - Field yang tidak tersedia ditampilkan sebagai '❌'

"""

import re
import os
import math
import json
import asyncio
from datetime import datetime
from telethon import events
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.functions.photos import GetUserPhotosRequest
from telethon.tl.types import User, Channel, Chat, MessageMediaGeo

# HELP entry (loader akan menggabungkan ke help global jika ada mekanisme tersebut)
HELP = {
    "userinfo": [
        ".cek (reply) -> Tampilkan info lengkap user dari pesan yang direply",
        ".cek <id|@username> -> Tampilkan info lengkap berdasarkan id/username",
    ]
}

# Peta kode negara sederhana (extendable)
COUNTRY_PREFIXES = {
    '62': ('Indonesia', '🇮🇩'),
    '1': ('United States/Canada', '🇺🇸'),
    '81': ('Japan', '🇯🇵'),
    '82': ('South Korea', '🇰🇷'),
    '7': ('Russia', '🇷🇺'),
    '44': ('United Kingdom', '🇬🇧'),
    '49': ('Germany', '🇩🇪'),
    '33': ('France', '🇫🇷'),
    '91': ('India', '🇮🇳'),
    '61': ('Australia', '🇦🇺'),
    '55': ('Brazil', '🇧🇷'),
    '63': ('Philippines', '🇵🇭'),
    '60': ('Malaysia', '🇲🇾'),
    '66': ('Thailand', '🇹🇭'),
}

# Utility helpers

def safe(value):
    """Return a human-readable value or ❌"""
    if value is None or value == "" or (isinstance(value, (list, dict)) and len(value) == 0):
        return '❌'
    return value


def detect_country_from_phone(phone: str):
    """Return (country_name, emoji) or (None, None)"""
    if not phone:
        return (None, None)
    phone = phone.lstrip('+')
    # try longest prefix first
    for length in range(3, 0, -1):
        prefix = phone[:length]
        if prefix in COUNTRY_PREFIXES:
            return COUNTRY_PREFIXES[prefix]
    return (None, None)


def format_bool_flag(flag):
    if flag is None:
        return '❌'
    return '✅' if flag else '❌'


def format_datetime(ts):
    if not ts:
        return '❌'
    if isinstance(ts, datetime):
        return ts.strftime('%d %b %Y %H:%M:%S')
    try:
        return datetime.fromtimestamp(int(ts)).strftime('%d %b %Y %H:%M:%S')
    except Exception:
        return str(ts)


# Main init function used by many userbot loaders

def init(client):
    print('✅ Modul USERINFO (.cek) dimuat...')

    @client.on(events.NewMessage(pattern=r"^\.cek(?: |$)(.*)"))
    async def handler_cek(event):
        arg = event.pattern_match.group(1).strip()

        # Determine target: arg, reply to message, or error
        target = None
        if arg:
            target = arg
        elif event.is_reply:
            reply_msg = await event.get_reply_message()
            # If reply contains text id or username, prefer that; else use sender_id
            if reply_msg and reply_msg.text:
                txt = reply_msg.text.strip()
                # try to extract pattern like -100123... or 123456 or @username
                m = re.search(r"(-?100\d{5,}|\d{5,}|@\w+)", txt)
                if m:
                    target = m.group(0)
                else:
                    # fallback to sender id
                    if reply_msg.sender_id:
                        target = str(reply_msg.sender_id)
            else:
                if reply_msg and reply_msg.sender_id:
                    target = str(reply_msg.sender_id)

        if not target:
            await event.edit('⚠️ Berikan ID / username atau reply ke pesan user yang ingin dicek.')
            return

        # Try to resolve entity
        try:
            # allow numeric ids and -100... channel ids and @usernames
            if isinstance(target, str) and target.lstrip('-').isdigit():
                ent = await client.get_entity(int(target))
            else:
                ent = await client.get_entity(target)
        except Exception as e:
            await event.edit(f'❌ Gagal mengambil entity: `{e}`')
            return

        # Prepare storage for many fields
        fields = {}

        # Common fields
        fields['id'] = getattr(ent, 'id', None)
        fields['access_hash'] = getattr(ent, 'access_hash', None)
        fields['username'] = getattr(ent, 'username', None)
        # name: user has first_name, channel has title
        fields['first_name'] = getattr(ent, 'first_name', None)
        fields['last_name'] = getattr(ent, 'last_name', None)
        fields['title'] = getattr(ent, 'title', None)
        fields['is_bot'] = getattr(ent, 'bot', False) if hasattr(ent, 'bot') else False
        fields['is_channel'] = isinstance(ent, Channel)
        fields['is_chat'] = isinstance(ent, Chat)

        # Try to fetch fuller data depending on type
        full_user = None
        full_channel = None
        full_chat = None

        try:
            if isinstance(ent, User):
                full = await client(GetFullUserRequest(ent.id))
                full_user = full
                # base user object
                u = full.user
                fu = full.full_user
                fields['phone'] = getattr(u, 'phone', None)
                fields['lang_code'] = getattr(u, 'lang_code', None)
                fields['about'] = getattr(fu, 'about', None) if fu else None
                fields['profile_photos'] = None
                try:
                    photos = await client(GetUserPhotosRequest(user_id=ent.id, offset=0, max_id=0, limit=1))
                    fields['profile_photos'] = photos.count if hasattr(photos, 'count') else None
                except Exception:
                    fields['profile_photos'] = None

                # flags
                fields['is_deleted'] = getattr(u, 'deleted', False)
                fields['is_verified'] = getattr(u, 'verified', False)
                fields['is_scam'] = getattr(u, 'scam', False)
                fields['is_fake'] = getattr(u, 'fake', False)
                fields['is_premium'] = getattr(u, 'premium', False)
                fields['mutual_contact'] = getattr(u, 'mutual_contact', False)
                # status
                try:
                    status = getattr(u, 'status', None)
                    if status is None:
                        fields['status'] = None
                    else:
                        fields['status'] = type(status).__name__
                        # try extract was_online if present
                        was_online = getattr(status, 'was_online', None)
                        fields['was_online'] = was_online
                except Exception:
                    fields['status'] = None

                # business & other optional
                fields['bot_info'] = getattr(u, 'bot_info_version', None)
                fields['is_support'] = getattr(u, 'support', False)
                fields['dc_id'] = getattr(u, 'dc_id', None)

            elif isinstance(ent, Channel):
                # Channel or supergroup
                try:
                    full_ch = await client(GetFullChannelRequest(ent))
                    full_channel = full_ch
                    ch = full_ch.chats[0] if full_ch.chats else ent
                    # many fields available in full_ch
                    fields['title'] = getattr(ch, 'title', None)
                    fields['about'] = getattr(full_ch, 'about', None)
                    fields['participants_count'] = getattr(full_ch, 'participant_count', None) or getattr(full_ch, 'participants_count', None) or None
                    # flags
                    fields['broadcast'] = getattr(ent, 'broadcast', False)
                    fields['megagroup'] = getattr(ent, 'megagroup', False)
                    fields['verified'] = getattr(ent, 'verified', False)
                    fields['scam'] = getattr(ent, 'scam', False)
                    fields['fake'] = getattr(ent, 'fake', False)
                    # location if present
                    try:
                        loc = getattr(full_ch, 'location', None)
                        if loc:
                            fields['location'] = getattr(loc, 'address', None) or str(loc)
                        else:
                            fields['location'] = None
                    except Exception:
                        fields['location'] = None
                except Exception:
                    # fallback to basic channel
                    fields['title'] = getattr(ent, 'title', None)
                    fields['about'] = None

            elif isinstance(ent, Chat):
                # basic group
                try:
                    full_c = await client(GetFullChatRequest(ent.id))
                    full_chat = full_c
                    fields['title'] = getattr(ent, 'title', None)
                    # try participants
                    fields['participants_count'] = getattr(full_c, 'participants_count', None)
                except Exception:
                    fields['title'] = getattr(ent, 'title', None)

        except Exception as e:
            # non-fatal
            pass

        # Country detection from phone if available
        country_name, country_emoji = (None, None)
        if fields.get('phone'):
            cname, cemoji = detect_country_from_phone(str(fields['phone']))
            country_name, country_emoji = cname, cemoji
            fields['country'] = f"{country_emoji} {country_name}" if cname else None
        else:
            fields['country'] = None

        # Heuristics: popularity / famous detection
        popularity_score = 0
        try:
            if fields.get('is_verified'):
                popularity_score += 50
            # username short
            uname = fields.get('username')
            if uname and len(uname) <= 5:
                popularity_score += 20
            # many photos
            pp = fields.get('profile_photos')
            if pp and pp >= 5:
                popularity_score += 10
            # mutual contacts and premium
            if fields.get('mutual_contact'):
                popularity_score += 5
            if fields.get('is_premium'):
                popularity_score += 5
        except Exception:
            pass

        fields['popularity_score'] = popularity_score
        fields['is_famous'] = True if popularity_score >= 40 else False

        # Build output text (very detailed)
        lines = []
        def L(label, key):
            lines.append(f"{label}: {safe(fields.get(key))}")

        lines.append('📊 USERINFO DETAIL')
        lines.append('────────────────────────────────────────')
        L('ID', 'id')
        L('Access Hash', 'access_hash')
        L('Username', 'username')
        # name variants
        if fields.get('title'):
            L('Title', 'title')
        else:
            L('First Name', 'first_name')
            L('Last Name', 'last_name')
        L('Phone', 'phone')
        L('Country', 'country')
        L('Language Code', 'lang_code')
        L('Bio/About', 'about')
        L('Profile Photos Count', 'profile_photos')
        L('Is Bot', 'is_bot')
        L('Is Deleted', 'is_deleted')
        L('Is Verified', 'is_verified')
        L('Is Scam', 'is_scam')
        L('Is Fake', 'is_fake')
        L('Is Premium', 'is_premium')
        L('Is Support', 'is_support')
        L('Mutual Contact', 'mutual_contact')
        L('DC ID', 'dc_id')
        L('Status', 'status')
        L('Was Online', 'was_online')
        L('Bot Info Version', 'bot_info')
        L('Popularity Score', 'popularity_score')
        L('Is Famous', 'is_famous')

        # Channel/group extras
        if isinstance(ent, Channel) or isinstance(ent, Chat):
            lines.append('\n📢 CHANNEL / GROUP INFO')
            lines.append('────────────────────────────────────────')
            L('Title', 'title')
            L('About', 'about')
            L('Participants Count', 'participants_count')
            L('Broadcast', 'broadcast')
            L('Megagroup', 'megagroup')
            L('Verified', 'verified')
            L('Scam', 'scam')
            L('Fake', 'fake')
            L('Location', 'location')

        # Fallback: include raw entity repr for debugging
        try:
            raw = repr(ent)
            lines.append('\n┄ Raw Entity ┄')
            lines.append(raw)
        except Exception:
            pass

        # Compose final strings
        out_text = "```" + "\n".join(lines) + "\n```"
        # Also prepare txt file
        txt_content = '\n'.join(lines)

        # Edit original command message with result
        try:
            # Edit message (user requested edit mode)
            await event.edit(out_text)
        except Exception as e:
            # Fallback to reply
            await event.reply(out_text)

        # Save txt file and send
        fname = f"userinfo_{fields.get('id', 'unknown')}.txt"
        try:
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(txt_content)
            await event.client.send_file(event.chat_id, fname, caption=f"Userinfo: {fields.get('id')}")
        except Exception:
            pass
        finally:
            try:
                if os.path.exists(fname):
                    os.remove(fname)
            except Exception:
                pass

    # end handler

# end init
