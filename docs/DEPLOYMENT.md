# Dokumentasi Deployment Aira

Aira telah dikonfigurasi agar siap untuk deployment pada lingkungan produksi menggunakan Flask, Gunicorn sebagai WSGI server, PostgreSQL sebagai basis data, dan Google Gemini API sebagai layanan AI.

> **Status:** Aira belum di-deploy ke server produksi publik. Dokumentasi ini menjelaskan persiapan dan konfigurasi yang telah dilakukan untuk mendukung deployment di tahap selanjutnya.

## 1. Arsitektur Deployment

```text
Pengguna
   │
   ▼
Aplikasi Aira
   │
   ├──────────────► Google Gemini API
   │
   ▼
PostgreSQL (Neon)
```

Aira menggunakan **Flask** sebagai backend aplikasi, **Google Gemini API** untuk mendukung fitur AI dalam latihan dan evaluasi bahasa Inggris, serta **Neon PostgreSQL** sebagai basis data relasional untuk menyimpan data pengguna dan aktivitas pembelajaran.

## 2. Konfigurasi Produksi

Aira menggunakan **Gunicorn** sebagai WSGI server untuk menjalankan aplikasi pada lingkungan produksi.

Perintah untuk menjalankan aplikasi:

```bash
gunicorn backend.app:app
```

Seluruh dependensi yang diperlukan oleh aplikasi tercantum dalam:

```text
requirements.txt
```

Dengan konfigurasi tersebut, aplikasi tidak bergantung pada Flask Development Server ketika dijalankan pada lingkungan produksi.

## 3. Konfigurasi Basis Data

Aira menggunakan **PostgreSQL yang di-host pada Neon**.

Koneksi basis data dikonfigurasi menggunakan environment variable:

```text
DATABASE_URL=postgresql+psycopg://...
```

Aplikasi menggunakan:

- **SQLAlchemy** sebagai Object-Relational Mapping (ORM)
- **psycopg** sebagai driver PostgreSQL

Basis data Aira memiliki beberapa tabel utama:

```text
users
conversations
messages
learning_events
recurring_mistakes
learning_profiles
daily_analyses
user_progress
password_reset_tokens
```

Inisialisasi dan validasi struktur basis data ditangani oleh modul database pada aplikasi.

## 4. Environment Variables

Informasi yang bersifat sensitif disimpan menggunakan **environment variables** dan tidak disimpan secara langsung di repository GitHub.

Environment variable utama yang digunakan Aira adalah:

```text
DATABASE_URL
GEMINI_API_KEY
```

Pada lingkungan pengembangan lokal, konfigurasi dapat disimpan dalam file:

```text
.env
```

File `.env` **tidak boleh diunggah ke repository GitHub** karena dapat berisi informasi sensitif, seperti API key dan kredensial basis data.

Pada lingkungan produksi, environment variables dikonfigurasi melalui fitur environment variables atau secrets yang disediakan oleh platform hosting.

## 5. Platform Deployment yang Dipertimbangkan

Beberapa platform dipertimbangkan untuk deployment Aira, antara lain:

- Render
- Koyeb
- Vercel
- PythonAnywhere
- Hugging Face Spaces
- Helipod

Evaluasi platform dilakukan berdasarkan kebutuhan proyek, yaitu:

- Mendukung aplikasi Python Flask
- Mendukung WSGI server seperti Gunicorn
- Dapat terhubung dengan PostgreSQL
- Mendukung koneksi ke Google Gemini API
- Mendukung environment variables
- Mendukung integrasi dengan GitHub
- Menyediakan akses melalui URL publik
- Memiliki biaya yang sesuai dengan kebutuhan proyek

Pada tahap ini, platform deployment belum ditetapkan sebagai lingkungan produksi aktif.

## 6. Persiapan Deployment

Aira telah dipersiapkan untuk deployment produksi dengan konfigurasi berikut:

- Migrasi basis data dari SQLite ke PostgreSQL Neon
- Konfigurasi SQLAlchemy untuk PostgreSQL
- Pembuatan dan validasi struktur basis data
- Konfigurasi Gunicorn sebagai WSGI server
- Penggunaan environment variables untuk konfigurasi sensitif
- Persiapan repository GitHub
- Pengujian aplikasi dan koneksi basis data secara lokal

## 7. Status Deployment

Saat ini:

**Aira belum di-deploy ke server produksi publik.**

Tahap deployment publik ditunda hingga pengembangan dan pengujian aplikasi selesai.

Meskipun belum tersedia URL publik, struktur aplikasi telah dipersiapkan agar dapat dijalankan pada platform hosting yang mendukung Python Flask dan PostgreSQL.

## 8. Alur Deployment

Ketika deployment publik dilakukan, alur yang digunakan adalah:

```text
Repository GitHub
       │
       ▼
Platform Hosting
       │
       ▼
Konfigurasi Environment Variables
       │
       ├── DATABASE_URL
       └── GEMINI_API_KEY
       │
       ▼
Instalasi Dependencies
       │
       ▼
Menjalankan Gunicorn
       │
       ▼
Aplikasi Aira dapat diakses secara publik
```

Struktur Aira dirancang agar platform hosting dapat diganti tanpa perlu mengubah logika utama aplikasi.

## 9. Pengujian Lokal

Sebelum deployment, aplikasi dapat dijalankan secara lokal menggunakan:

```bash
python -m backend.app
```

Koneksi basis data dapat diperiksa menggunakan:

```bash
python -c "from backend.database import get_database_info; print(get_database_info())"
```

Inisialisasi basis data dapat diperiksa menggunakan:

```bash
python -c "from backend.database import init_db; init_db(); print('Database initialization successful')"
```

Jika aplikasi dijalankan menggunakan production server, entry point yang digunakan adalah:

```text
backend.app:app
```

dengan perintah:

```bash
gunicorn backend.app:app
```

## 10. Keamanan Konfigurasi

Informasi sensitif tidak disimpan di dalam repository. File seperti `.env`, database lokal, virtual environment, dan file cache Python dikecualikan melalui `.gitignore`.

Contoh informasi yang **tidak boleh diunggah ke GitHub**:

```text
.env
venv/
*.db
*.sqlite
__pycache__/
```

Untuk repository GitHub, GitHub juga merekomendasikan penggunaan fitur keamanan seperti secret scanning, push protection, dan Dependabot untuk membantu mengurangi risiko kebocoran secret dan kerentanan dependensi.

## 11. Kesimpulan

Aira telah dipersiapkan untuk deployment produksi dengan komponen utama:

- **Flask** sebagai backend
- **Gunicorn** sebagai WSGI server
- **PostgreSQL Neon** sebagai basis data
- **Google Gemini API** sebagai layanan AI
- **SQLAlchemy** sebagai ORM
- **Environment variables** untuk konfigurasi sensitif
- **GitHub** sebagai repository kode

Pada tahap ini, Aira **belum di-deploy ke server produksi publik**. Deployment publik akan menjadi tahap lanjutan setelah proses pengembangan dan pengujian aplikasi dinyatakan selesai.
