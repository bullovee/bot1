import os
import io
import base64
import secrets
from pathlib import Path
from typing import Optional

from telethon import events
from openai import OpenAI

from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# -------------------------
# Configuration / Client
# -------------------------
ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
HELP = {
    "utility": [
        ".encrypt <password> (balas file) → Enkripsi file dengan password (AES-256)",
        ".encrypt --gen (balas file) → Generate password aman dan enkripsi file; bot akan menampilkan password",
        ".decrypt <password> (balas file) → Dekripsi file terenkripsi",
        ".encode (balas file) → Encode file jadi base64 (kirim sebagai .txt)",
        ".decode (balas file teks/base64) → Decode base64 jadi file asli",
        ".encrypt-explain (balas file terenkripsi + password) → Dekripsi lalu minta AI jelaskan isi (jika teks)"
    ]
}

# -------------------------
# Crypto helpers
# -------------------------
BACKEND = default_backend()
SALT_SIZE = 16
IV_SIZE = 16
KEY_LEN = 32  # AES-256
PBKDF2_ITERS = 200_000


def _derive_key(password: bytes, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=PBKDF2_ITERS,
        backend=BACKEND,
    )
    return kdf.derive(password)


def _aes_encrypt(key: bytes, data: bytes) -> (bytes, bytes):
    iv = secrets.token_bytes(IV_SIZE)
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(data) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=BACKEND)
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded) + encryptor.finalize()
    return iv, ct


def _aes_decrypt(key: bytes, iv: bytes, ct: bytes) -> Optional[bytes]:
    try:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=BACKEND)
        decryptor = cipher.decryptor()
        padded = decryptor.update(ct) + decryptor.finalize()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        data = unpadder.update(padded) + unpadder.finalize()
        return data
    except Exception:
        return None

# Output format for encrypted file: [salt (16)] + [iv (16)] + [ciphertext]

# -------------------------
# Utility helpers
# -------------------------

def _read_file_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def _write_bytes_to_file(path: str, data: bytes):
    with open(path, "wb") as f:
        f.write(data)


def _make_encrypted_blob(password: str, data: bytes) -> bytes:
    salt = secrets.token_bytes(SALT_SIZE)
    key = _derive_key(password.encode("utf-8"), salt)
    iv, ct = _aes_encrypt(key, data)
    return salt + iv + ct


def _parse_encrypted_blob(blob: bytes):
    if len(blob) < SALT_SIZE + IV_SIZE:
        return None
    salt = blob[:SALT_SIZE]
    iv = blob[SALT_SIZE:SALT_SIZE + IV_SIZE]
    ct = blob[SALT_SIZE + IV_SIZE:]
    return salt, iv, ct

# -------------------------
# Handlers (Telethon)
# -------------------------

def init(client):
    print("✅ Modul Crypto & AI (encrypt/decrypt/encode/decode) dimuat...")

    @client.on(events.NewMessage(pattern=r"^\.encrypt(?: |$)(.*)"))
    async def handler_encrypt(event):
        arg = event.pattern_match.group(1).strip()

        # gather file from reply
        if not event.is_reply:
            await event.reply("⚠️ Balas file yang ingin dienkripsi dengan `.encrypt <password>` atau `.encrypt --gen`.")
            return

        reply = await event.get_reply_message()
        if not reply.media:
            await event.reply("⚠️ Pesan yang dibalas harus berupa file.")
            return

        # download file
        await event.edit("🔒 Mengunduh file...")
        file_path = await reply.download_media()
        try:
            data = _read_file_bytes(file_path)
        except Exception as e:
            await event.edit(f"❌ Gagal baca file: {e}")
            return

        # password handling
        if arg == "--gen":
            # generate secure password locally (not via AI)
            password = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode('utf-8')
            show_password = True
        elif arg:
            password = arg
            show_password = False
        else:
            await event.edit("⚠️ Berikan password: `.encrypt <password>` atau gunakan `.encrypt --gen` untuk generate password aman.")
            return

        await event.edit("🔐 Mengenkripsi file...")
        try:
            blob = _make_encrypted_blob(password, data)
            out_path = f"{file_path}.enc"
            _write_bytes_to_file(out_path, blob)
            await event.client.send_file(event.chat_id, out_path, caption=(f"✅ File terenkripsi: {Path(out_path).name}\n" + (f"🔑 Password: `{password}`" if show_password else "")))
            await event.delete()
        except Exception as e:
            await event.edit(f"❌ Gagal enkripsi: {e}")
        finally:
            try:
                os.remove(file_path)
            except Exception:
                pass

    @client.on(events.NewMessage(pattern=r"^\.decrypt(?: |$)(.*)"))
    async def handler_decrypt(event):
        arg = event.pattern_match.group(1).strip()

        if not event.is_reply:
            await event.reply("⚠️ Balas file terenkripsi dengan `.decrypt <password>` untuk mendekripsi.")
            return

        reply = await event.get_reply_message()
        if not reply.media:
            await event.reply("⚠️ Pesan yang dibalas harus berupa file terenkripsi.")
            return

        if not arg:
            await event.reply("⚠️ Berikan password: `.decrypt <password>`")
            return

        password = arg
        await event.edit("🔓 Mengunduh file terenkripsi...")
        file_path = await reply.download_media()
        try:
            blob = _read_file_bytes(file_path)
        except Exception as e:
            await event.edit(f"❌ Gagal baca file: {e}")
            return

        parsed = _parse_encrypted_blob(blob)
        if not parsed:
            await event.edit("❌ File bukan format terenkripsi yang didukung.")
            return
        salt, iv, ct = parsed
        key = _derive_key(password.encode("utf-8"), salt)
        await event.edit("🔐 Mencoba dekripsi...")
        data = _aes_decrypt(key, iv, ct)
        if data is None:
            await event.edit("❌ Gagal dekripsi. Password mungkin salah atau file korup.")
            return

        out_path = f"{file_path}.dec"
        try:
            _write_bytes_to_file(out_path, data)
            await event.client.send_file(event.chat_id, out_path, caption=f"✅ File didekripsi: {Path(out_path).name}")
            await event.delete()
        except Exception as e:
            await event.edit(f"❌ Gagal menulis file dekripsi: {e}")
        finally:
            try:
                os.remove(file_path)
            except Exception:
                pass

    @client.on(events.NewMessage(pattern=r"^\.encode(?: |$)(.*)"))
    async def handler_encode(event):
        # encode file to base64
        if not event.is_reply:
            await event.reply("⚠️ Balas file dengan `.encode` untuk mengubahnya menjadi base64 (file .txt akan dikirim).")
            return

        reply = await event.get_reply_message()
        if not reply.media:
            await event.reply("⚠️ Pesan yang dibalas harus berupa file.")
            return

        await event.edit("🔧 Mengunduh file untuk di-encode...")
        file_path = await reply.download_media()
        try:
            data = _read_file_bytes(file_path)
            b64 = base64.b64encode(data).decode('utf-8')
            out_path = f"{file_path}.b64.txt"
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(b64)
            await event.client.send_file(event.chat_id, out_path, caption=f"✅ File base64: {Path(out_path).name}")
            await event.delete()
        except Exception as e:
            await event.edit(f"❌ Gagal encode: {e}")
        finally:
            try:
                os.remove(file_path)
            except Exception:
                pass

    @client.on(events.NewMessage(pattern=r"^\.decode(?: |$)(.*)"))
    async def handler_decode(event):
        # decode base64 from reply (either file or text)
        if not event.is_reply:
            await event.reply("⚠️ Balas pesan berisi base64 (atau file .b64.txt) dengan `.decode` untuk mengembalikan file asli.")
            return

        reply = await event.get_reply_message()
        b64_text = None

        if reply.media:
            # download file and read text
            await event.edit("🔧 Mengunduh file base64...")
            file_path = await reply.download_media()
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    b64_text = f.read()
            except Exception as e:
                await event.edit(f"❌ Gagal baca file base64: {e}")
                try:
                    os.remove(file_path)
                except Exception:
                    pass
                return
            finally:
                try:
                    os.remove(file_path)
                except Exception:
                    pass
        else:
            # take text
            b64_text = reply.text

        if not b64_text:
            await event.reply("⚠️ Tidak ada data base64 yang dapat dibaca.")
            return

        await event.edit("🔄 Mendecode base64...")
        try:
            data = base64.b64decode(b64_text)
            out_path = f"decoded_from_b64.bin"
            _write_bytes_to_file(out_path, data)
            await event.client.send_file(event.chat_id, out_path, caption=f"✅ Hasil decode base64: {Path(out_path).name}")
            await event.delete()
        except Exception as e:
            await event.edit(f"❌ Gagal decode base64: {e}")
        finally:
            try:
                os.remove(out_path)
            except Exception:
                pass

    @client.on(events.NewMessage(pattern=r"^\.encrypt-explain(?: |$)(.*)"))
    async def handler_encrypt_explain(event):
        # decrypt then ask AI to explain content (if textual)
        arg = event.pattern_match.group(1).strip()
        if not event.is_reply:
            await event.reply("⚠️ Balas file terenkripsi dengan `.encrypt-explain <password>` untuk mendekripsi & minta AI menjelaskan isinya (jika teks).")
            return

        if not arg:
            await event.reply("⚠️ Berikan password: `.encrypt-explain <password>`")
            return

        reply = await event.get_reply_message()
        if not reply.media:
            await event.reply("⚠️ Pesan yang dibalas harus berupa file terenkripsi.")
            return

        password = arg
        await event.edit("🔓 Mengunduh file terenkripsi...")
        file_path = await reply.download_media()
        try:
            blob = _read_file_bytes(file_path)
            parsed = _parse_encrypted_blob(blob)
            if not parsed:
                await event.edit("❌ File bukan format terenkripsi yang didukung.")
                return
            salt, iv, ct = parsed
            key = _derive_key(password.encode('utf-8'), salt)
            data = _aes_decrypt(key, iv, ct)
            if data is None:
                await event.edit("❌ Gagal dekripsi. Password mungkin salah atau file korup.")
                return

            # If data looks like text, send to AI to explain
            try:
                text = data.decode('utf-8')
            except Exception:
                await event.edit("ℹ️ File berhasil didekripsi tapi bukan teks; mengirim file sebagai hasil.")
                out_path = f"{file_path}.dec"
                _write_bytes_to_file(out_path, data)
                await event.client.send_file(event.chat_id, out_path, caption=f"✅ File didekripsi: {Path(out_path).name}")
                await event.delete()
                return

            await event.edit("🤖 Mengirim teks ke AI untuk penjelasan...")
            try:
                response = ai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Kamu adalah asisten yang menjelaskan isi teks teknis atau konfigurasi dengan jelas dan singkat."},
                        {"role": "user", "content": text}
                    ]
                )
                answer = response.choices[0].message.content.strip()
                await event.edit(f"🧠 **Penjelasan AI:**\n\n{answer}")
            except Exception as e:
                await event.edit(f"❌ Gagal minta penjelasan ke AI: {e}")

        finally:
            try:
                os.remove(file_path)
            except Exception:
                pass
