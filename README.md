# FreeReels Drama Automation Bot

Bot otomatis untuk mengunduh, menggabungkan, dan mengunggah drama dari FreeReels ke Telegram dengan fitur manajemen antrian dan database (PostgreSQL & Google Sheets).

## ✨ Fitur Utama
- **Auto-Scan Drama Baru**: Bot secara otomatis memantau endpoint `/new` untuk drama terbaru.
- **Pencegahan Duplikat**: Menggunakan PostgreSQL (untuk kecepatan) dan Google Sheets (untuk tracking) agar tidak mengunggah drama yang sama.
- **Smart Queue**: Antrian tugas dengan prioritas (High untuk manual `/id`, Low untuk auto-scan).
- **Video Merging**: Menggabungkan beberapa episode menjadi satu file film (atau per part jika sizenya > 2GB).
- **Subtitle Hardcode**: Otomatis menempelkan subtitle Indonesia (id-ID) ke video.
- **Bot Rest Loop**: Jeda otomatis 10 menit setelah setiap upload sukses untuk mencegah spam.

## 🛠 Instalasi di VPS (via Putty)

### 1. Persiapan Environment
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip ffmpeg aria2 screen -y
```

### 2. Clone Repository
```bash
git clone https://github.com/Lebo-20/freerls.git
cd freerls
```

### 3. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 4. Konfigurasi `.env`
Buat file env manual:
```bash
nano .env
```
Isi dengan data berikut:
```env
FREEREELS_API_KEY=YOUR_API_KEY
API_ID=YOUR_TELEGRAM_API_ID
API_HASH=YOUR_TELEGRAM_API_HASH
BOT_TOKEN=YOUR_BOT_TOKEN
CHANNEL_ID=YOUR_TARGET_CHANNEL_ID
ADMIN_ID=YOUR_ADMIN_ID
DATABASE_URL=postgresql://user:pass@host:port/dbname?sslmode=require
```

### 5. Jalankan Bot
Gunakan `screen` agar bot tetap jalan saat Putty ditutup:
```bash
screen -S freerels
python3 main.py
```
*Gunakan `Ctrl+A` lalu `D` untuk keluar dari tampilan screen tanpa mematikan bot.*

## 📋 Perintah Bot
- `/start` - Cek status bot.
- `/search [judul]` - Cari drama di FreeReels.
- `/id [drama_id]` - Masukkan drama ke antrian secara manual (High Priority).
- `/queue` - Lihat status antrian saat ini.

## 🗄 Database
Bot ini mendukung dua backend database secara bersamaan:
1. **PostgreSQL**: Backend utama untuk pengecekan cepat (disarankan menggunakan Neon.tech).
2. **Google Sheets**: Backend tracking yang bisa dilihat langsung via browser (memerlukan `credentials.json`).
3. **Local (JSON)**: Fallback otomatis jika database online tidak tersedia.

---
**Author**: Antigravity Assistant
**Github**: [Lebo-20/freerls](https://github.com/Lebo-20/freerls.git)
