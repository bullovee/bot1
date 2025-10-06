# Gunakan base image Python versi ringan
FROM python:3.10-slim

# Set folder kerja di dalam container
WORKDIR /app

# Salin file requirements.txt ke container
COPY requirements.txt .

# Install semua dependensi bot
RUN pip install --no-cache-dir -r requirements.txt

# Salin semua file proyek ke container
COPY . .

# Perintah untuk menjalankan bot
CMD ["python", "bot.py"]
