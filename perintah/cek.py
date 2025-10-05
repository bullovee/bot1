# cek.py
# Perintah: .cek
# Compatible with Telethon userbot (register(client) style)
# Place inside your modules/perintah folder and restart userbot.

import re
import os
from datetime import datetime
from telethon import events
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.functions.photos import GetUserPhotosRequest
from telethon.tl.types import User, Channel, Chat

HELP = {
    "utility": [
        ".cek (balas pesan / id / @username) -> Tampilkan info lengkap User / Group / Channel",
    ]
}

# Simple country prefix map (extendable)
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
    # add more prefixes as needed
}

def safe(v):
    if v is None or v == "" or (isinstance(v, (list, dict)) and len(v) == 0):
        return "❌"
    return v

def detect_country_from_phone(phone: str):
    if not phone:
        return (None, None)
    phone = phone.lstrip("+")
    # try longest prefix first (3,2,1)
    for length in range(3, 0, -1):
        prefix = phone[:length]
        if prefix in COUNTRY_PREFIXES:
            return COUNTRY_PREFIXES[prefix]
    return (None, None)

def fmt_dt(ts):
    if ts is None:
        return "❌"
    if isinstance(ts, datetime):
        return ts.strftime("%d %b %Y %H:%M:%S")
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%d %b %Y %H:%M:%S")
    except Exception:
        return str(ts)

def register(client):
    print("✅ Modul CEK (.cek) dimuat...")

    @client.on(events.NewMessage(pattern=r"^\.cek(?: |$)(.*)"))
    async def handler_cek(event):
        arg = event.pattern_match.group(1).strip()

        # Resolve target: arg -> reply message content -> reply sender id
        target = None
        if arg:
            target = arg
        elif event.is_reply:
            reply = await event.get_reply_message()
            if not reply:
                await event.edit("⚠️ Tidak ada pesan yang direply.")
                return
            # try extract id or username inside reply text
            txt = reply.text or ""
            m = re.search(r"(-?100\d{5,}|\d{5,}|@[\w\d_]+)", txt)
            if m:
                target = m.group(0)
            else:
                # fallback to sender id
                if reply.sender_id:
                    target = str(reply.sender_id)
                else:
                    await event.edit("⚠️ Tidak dapat menentukan target dari pesan yang direply.")
                    return
        else:
            await event.edit("⚠️ Berikan ID / @username atau reply pesan user/channel.")
            return

        # Try to get entity safely
        try:
            # numeric id or -100 channel id
            if isinstance(target, str) and target.lstrip("-").isdigit():
                ent = await client.get_entity(int(target))
            else:
                ent = await client.get_entity(target)
        except Exception as e:
            # entity might not be discoverable due to privacy or never interacted
            await event.edit(f"❌ Gagal mengambil entity: {e}\n\n"
                             "Kemungkinan: target belum pernah berinteraksi dengan akun ini, "
                             "atau username/ID salah, atau privasi ketat.")
            return

        # collect fields
        fields = {}
        fields['id'] = getattr(ent, "id", None)
        fields['access_hash'] = getattr(ent, "access_hash", None)
        fields['username'] = getattr(ent, "username", None)
        fields['first_name'] = getattr(ent, "first_name", None)
        fields['last_name'] = getattr(ent, "last_name", None)
        fields['title'] = getattr(ent, "title", None)

        # defaults
        fields['phone'] = None
        fields['lang_code'] = None
        fields['about'] = None
        fields['profile_photos_count'] = None
        fields['is_deleted'] = False
        fields['is_verified'] = False
        fields['is_scam'] = False
        fields['is_fake'] = False
        fields['is_premium'] = False
        fields['mutual_contact'] = False
        fields['is_support'] = False
        fields['dc_id'] = None
        fields['status'] = None
        fields['was_online'] = None
        fields['bot_info_version'] = None
        fields['broadcast'] = False
        fields['megagroup'] = False
        fields['participants_count'] = None
        fields['about_channel'] = None
        fields['location'] = None

        # Try get fuller objects depending on type
        try:
            if isinstance(ent, User):
                full = await client(GetFullUserRequest(ent.id))
                u = full.user
                fu = full.full_user
                fields['phone'] = getattr(u, 'phone', None)
                fields['lang_code'] = getattr(u, 'lang_code', None)
                fields['about'] = getattr(fu, 'about', None) if fu else None
                # profile photos count
                try:
                    photos = await client(GetUserPhotosRequest(user_id=ent.id, offset=0, max_id=0, limit=1))
                    fields['profile_photos_count'] = photos.count if hasattr(photos, 'count') else None
                except Exception:
                    fields['profile_photos_count'] = None

                fields['is_deleted'] = getattr(u, 'deleted', False)
                fields['is_verified'] = getattr(u, 'verified', False)
                fields['is_scam'] = getattr(u, 'scam', False)
                fields['is_fake'] = getattr(u, 'fake', False)
                fields['is_premium'] = getattr(u, 'premium', False)
                fields['mutual_contact'] = getattr(u, 'mutual_contact', False)
                fields['is_support'] = getattr(u, 'support', False)
                fields['dc_id'] = getattr(u, 'dc_id', None)
                # status
                status = getattr(u, 'status', None)
                if status is None:
                    fields['status'] = None
                else:
                    fields['status'] = type(status).__name__
                    fields['was_online'] = getattr(status, 'was_online', None)
                fields['bot_info_version'] = getattr(u, 'bot_info_version', None)

            elif isinstance(ent, Channel):
                # Channel / supergroup
                try:
                    full_ch = await client(GetFullChannelRequest(ent))
                    # full_ch may contain .chats and .full_chat/full_channel
                    fields['title'] = getattr(ent, 'title', None)
                    fields['about_channel'] = getattr(full_ch, 'about', None)
                    # participants count
                    pc = getattr(full_ch, 'participants_count', None) or getattr(full_ch, 'participants_count', None)
                    fields['participants_count'] = pc
                    fields['broadcast'] = getattr(ent, 'broadcast', False)
                    fields['megagroup'] = getattr(ent, 'megagroup', False)
                    fields['verified'] = getattr(ent, 'verified', False)
                    fields['scam'] = getattr(ent, 'scam', False)
                    fields['fake'] = getattr(ent, 'fake', False)
                    # location
                    try:
                        loc = getattr(full_ch, 'location', None)
                        if loc:
                            fields['location'] = getattr(loc, 'address', None) or str(loc)
                    except Exception:
                        fields['location'] = None
                except Exception:
                    # partial fallback
                    fields['title'] = getattr(ent, 'title', None)

            elif isinstance(ent, Chat):
                try:
                    full_chat = await client(GetFullChatRequest(ent.id))
                    fields['title'] = getattr(ent, 'title', None)
                    fields['participants_count'] = getattr(full_chat, 'participants_count', None)
                except Exception:
                    fields['title'] = getattr(ent, 'title', None)

        except Exception:
            # non-fatal, continue with what we have
            pass

        # detect country from phone
        country_name, country_emoji = (None, None)
        if fields.get('phone'):
            cname, cemoji = detect_country_from_phone(str(fields['phone']))
            country_name, country_emoji = cname, cemoji
            fields['country'] = f"{country_emoji} {country_name}" if cname else None
        else:
            fields['country'] = None

        # heuristics popularity
        popularity = 0
        try:
            if fields.get('is_verified'):
                popularity += 50
            uname = fields.get('username')
            if uname and len(uname) <= 5:
                popularity += 20
            pp = fields.get('profile_photos_count')
            if pp and pp >= 5:
                popularity += 10
            if fields.get('mutual_contact'):
                popularity += 5
            if fields.get('is_premium'):
                popularity += 5
        except Exception:
            pass

        fields['popularity_score'] = popularity
        fields['is_famous'] = True if popularity >= 40 else False

        # build lines
        lines = []
        lines.append("📊 USERINFO DETAIL")
        lines.append("────────────────────────────────────────")
        lines.append(f"ID: {safe(fields.get('id'))}")
        lines.append(f"Access Hash: {safe(fields.get('access_hash'))}")
        lines.append(f"Username: {safe(fields.get('username'))}")
        # name / title
        if safe(fields.get('title')) != "❌":
            lines.append(f"Title: {safe(fields.get('title'))}")
        else:
            lines.append(f"First Name: {safe(fields.get('first_name'))}")
            lines.append(f"Last Name: {safe(fields.get('last_name'))}")
        lines.append(f"Phone: {safe(fields.get('phone'))}")
        lines.append(f"Country: {safe(fields.get('country'))}")
        lines.append(f"Language Code: {safe(fields.get('lang_code'))}")
        lines.append(f"Bio/About: {safe(fields.get('about'))}")
        lines.append(f"Profile Photos Count: {safe(fields.get('profile_photos_count'))}")
        lines.append(f"Is Bot: {safe(getattr(ent, 'bot', False))}")
        lines.append(f"Is Deleted: {safe(fields.get('is_deleted'))}")
        lines.append(f"Is Verified: {safe(fields.get('is_verified'))}")
        lines.append(f"Is Scam: {safe(fields.get('is_scam'))}")
        lines.append(f"Is Fake: {safe(fields.get('is_fake'))}")
        lines.append(f"Is Premium: {safe(fields.get('is_premium'))}")
        lines.append(f"Is Support: {safe(fields.get('is_support'))}")
        lines.append(f"Mutual Contact: {safe(fields.get('mutual_contact'))}")
        lines.append(f"DC ID: {safe(fields.get('dc_id'))}")
        lines.append(f"Status: {safe(fields.get('status'))}")
        lines.append(f"Was Online: {fmt_dt(fields.get('was_online'))}")
        lines.append(f"Bot Info Version: {safe(fields.get('bot_info_version'))}")
        lines.append(f"Popularity Score: {safe(fields.get('popularity_score'))}")
        lines.append(f"Is Famous: {safe(fields.get('is_famous'))}")

        if isinstance(ent, Channel) or isinstance(ent, Chat):
            lines.append("")
            lines.append("📢 CHANNEL / GROUP INFO")
            lines.append("────────────────────────────────────────")
            lines.append(f"Title: {safe(fields.get('title'))}")
            lines.append(f"About: {safe(fields.get('about_channel'))}")
            lines.append(f"Participants Count: {safe(fields.get('participants_count'))}")
            lines.append(f"Broadcast: {safe(fields.get('broadcast'))}")
            lines.append(f"Megagroup: {safe(fields.get('megagroup'))}")
            lines.append(f"Verified: {safe(fields.get('verified'))}")
            lines.append(f"Scam: {safe(fields.get('scam'))}")
            lines.append(f"Fake: {safe(fields.get('fake'))}")
            lines.append(f"Location: {safe(fields.get('location'))}")

        # raw entity for debugging
        try:
            lines.append("")
            lines.append("┄ Raw Entity ┄")
            lines.append(repr(ent))
        except Exception:
            pass

        # compose outputs
        out_text = "```" + "\n".join(lines) + "\n```"
        txt_content = "\n".join(lines)

        # edit original message with result
        try:
            await event.edit(out_text)
        except Exception:
            # fallback to reply
            await event.reply(out_text)

        # send profile photo if available (user) or chat photo (channel)
        try:
            # for users
            if isinstance(ent, User):
                if fields.get('profile_photos_count') and fields['profile_photos_count'] and fields['profile_photos_count'] > 0:
                    try:
                        # download best profile photo
                        file_photo = await client.download_profile_photo(ent, file=f"profile_{ent.id}.jpg")
                        if file_photo:
                            await client.send_file(event.chat_id, file_photo, caption=f"Photo profile: {safe(fields.get('username'))}")
                            os.remove(file_photo)
                    except Exception:
                        pass
            else:
                # channel chat photo (attempt)
                try:
                    file_photo = await client.download_profile_photo(ent, file=f"profile_{fields.get('id')}.jpg")
                    if file_photo:
                        await client.send_file(event.chat_id, file_photo, caption=f"Photo: {safe(fields.get('title') or fields.get('username'))}")
                        os.remove(file_photo)
                except Exception:
                    pass
        except Exception:
            pass

        # create txt file and send
        fname = f"userinfo_{fields.get('id','unknown')}.txt"
        try:
            with open(fname, "w", encoding="utf-8") as f:
                f.write(txt_content)
            await client.send_file(event.chat_id, fname, caption=f"Userinfo: {safe(fields.get('id'))}")
        except Exception:
            pass
        finally:
            try:
                if os.path.exists(fname):
                    os.remove(fname)
            except Exception:
                pass

    # end handler
