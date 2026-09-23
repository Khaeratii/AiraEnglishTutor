# Aira English Tutor

> Conversational English Practice & Feedback Agent berbasis AI untuk membantu pengguna beginner hingga intermediate berlatih Bahasa Inggris secara mandiri.

Aira adalah AI-powered English tutor yang menggabungkan percakapan natural dengan feedback pembelajaran. Aira tidak hanya merespons seperti chatbot, tetapi juga mengamati penggunaan Bahasa Inggris pengguna, memberikan koreksi yang relevan, dan menyimpan data pembelajaran untuk menghasilkan insight yang lebih personal.

## Tujuan

Aira dibuat untuk membantu pengguna:

- Berlatih conversational English secara mandiri.
- Mendapatkan feedback grammar dan naturalness.
- Menganalisis kemampuan berdasarkan percakapan.
- Melacak perkembangan kemampuan Bahasa Inggris.
- Mengidentifikasi pola kesalahan yang berulang.
- Mendapatkan learning analysis yang lebih personal.

## Fitur Utama

### 1. Conversational English Practice

Pengguna dapat melakukan percakapan Bahasa Inggris dengan Aira melalui antarmuka web. Aira merespons secara natural sambil mempertahankan perannya sebagai English tutor yang suportif.

### 2. Grammar & Naturalness Feedback

Aira menganalisis penggunaan Bahasa Inggris pengguna dan dapat:

- Menganalisis grammar.
- Memberikan koreksi kalimat.
- Memberikan alternatif kalimat yang lebih natural.
- Menganalisis word choice dan sentence structure.

### 3. Skill Assessment

Kemampuan pengguna dianalisis berdasarkan beberapa aspek berikut:

| Aspek              | Fokus Analisis                              |
| ------------------ | ------------------------------------------- |
| Fluency            | Kelancaran dalam menyampaikan ide           |
| Communication      | Kejelasan dan efektivitas penyampaian pesan |
| Vocabulary         | Penggunaan dan variasi kosakata             |
| Naturalness        | Seberapa alami penggunaan Bahasa Inggris    |
| Grammar            | Ketepatan tata bahasa                       |
| Sentence Structure | Susunan dan kualitas struktur kalimat       |

### 4. Learning Progress

Aira menampilkan perkembangan kemampuan pengguna, termasuk level saat ini dan progress menuju level berikutnya.

### 5. Learning Analysis

Hasil percakapan dianalisis untuk mengidentifikasi:

- Strengths pengguna.
- Areas for improvement.
- Recurring mistakes dan pola kesalahan yang sering muncul.

### 6. Personalized Learning Profile

Aira menyimpan informasi perkembangan dan pola pembelajaran pengguna. Data tersebut digunakan untuk menghasilkan insight pembelajaran yang lebih personal.

### 7. Authentication

Fitur autentikasi yang tersedia meliputi:

- Sign In dan Sign Up.
- Password hashing.
- Session management.
- Password reset menggunakan token.

### 8. Persistent Learning Data

Data pembelajaran disimpan secara persisten, meliputi:

- Conversation history.
- Messages.
- Learning events.
- Recurring mistakes.
- Learning profiles.
- Daily analyses.
- User progress.

## Tampilan Aplikasi

Berikut beberapa tampilan utama Aira. Klik gambar untuk melihat screenshot dalam ukuran penuh.

### Sign In

[![Aira Sign In](docs/aira-signin.png)](docs/aira-signin.png)

### Conversation Practice

[![Aira Chat](docs/aira-chat.png)](docs/aira-chat.png)

### Learning Analysis

[![Aira Analysis](docs/aira-analysis.png)](docs/aira-analysis.png)

## Arsitektur

```mermaid
flowchart LR
    User[User] --> Frontend[Frontend<br/>HTML, CSS, JavaScript]
    Frontend --> Backend[Flask Backend]
    Backend --> Gemini[Gemini API]
    Backend --> Database[(PostgreSQL / Neon)]
```

| Komponen          | Fungsi                                                                                                          |
| ----------------- | --------------------------------------------------------------------------------------------------------------- |
| User              | Melakukan percakapan, melihat feedback, dan memantau progress belajar.                                          |
| Frontend          | Menyediakan antarmuka web untuk autentikasi, conversation practice, history, profile, statistics, dan analysis. |
| Flask Backend     | Menangani request aplikasi, autentikasi, percakapan, feedback, learning events, dan akses database.             |
| Gemini API        | Menghasilkan respons percakapan dan membantu analisis penggunaan Bahasa Inggris.                                |
| PostgreSQL / Neon | Menyimpan data pengguna, percakapan, feedback, serta progress pembelajaran secara persisten.                    |

## Teknologi

### Backend

- Python
- Flask
- SQLAlchemy
- Flask-Login
- Flask-Bcrypt
- Flask-CORS
- Gunicorn

### AI

- Google Gemini API
- `google-genai`

### Database

- PostgreSQL
- Neon
- Psycopg

### Speech & Audio

- gTTS
- SpeechRecognition
- pydub

### Data Processing

- Pandas

### Frontend

- HTML
- CSS
- JavaScript

### Development

- Git
- GitHub
- Python Virtual Environment

## Struktur Project

```text
AiraEnglishTutor/
├── backend/
│   ├── app.py
│   ├── analytics.py
│   ├── config.py
│   ├── database.py
│   ├── learning.py
│   ├── models.py
│   └── utils/
│       ├── ai_service.py
│       ├── audio_service.py
│       └── history_service.py
├── frontend/
│   ├── assets/
│   ├── css/
│   ├── js/
│   ├── analysis.html
│   ├── history.html
│   ├── index.html
│   ├── login.html
│   ├── profile.html
│   ├── signup.html
│   └── statistics.html
├── docs/
│   ├── aira-analysis.png
│   ├── aira-chat.png
│   └── asia-signin.png
├── migrations/
│   └── 001_password_reset_tokens.sql
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

## Database

Aira menggunakan **PostgreSQL** sebagai persistent database. **Neon** digunakan sebagai layanan PostgreSQL yang menyimpan data aplikasi di luar proses aplikasi sehingga data tetap tersedia antar sesi.

Tabel utama yang digunakan:

- `users`
- `conversations`
- `messages`
- `learning_events`
- `recurring_mistakes`
- `learning_profiles`
- `daily_analyses`
- `user_progress`
- `password_reset_tokens`

## Environment Variables

Buat file `.env` di root project dan isi konfigurasi berikut:

```env
DATABASE_URL=postgresql+psycopg://username:password@host/database
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=your_secret_key
```

`DATABASE_URL` digunakan untuk koneksi PostgreSQL, `GEMINI_API_KEY` untuk akses Google Gemini API, dan `SECRET_KEY` untuk kebutuhan session serta keamanan aplikasi.

> Jangan commit file `.env` ke GitHub. Gunakan environment variables dan pastikan `.env` tercantum dalam `.gitignore`.

## Instalasi Lokal

### 1. Clone repository

```bash
git clone https://github.com/Khaeratii/AiraEnglishTutor.git
cd AiraEnglishTutor
```

### 2. Buat dan aktifkan virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Konfigurasi `.env`

Buat file `.env` berdasarkan contoh pada bagian [Environment Variables](#environment-variables), lalu isi credential PostgreSQL dan Google Gemini API.

### 5. Jalankan aplikasi

```bash
python -m backend.app
```

## Security

Aira menerapkan beberapa praktik keamanan dasar:

- Password disimpan menggunakan hashing.
- API keys dan credential disimpan melalui environment variables.
- File `.env` tidak dimasukkan ke repository.
- Session authentication digunakan untuk mengelola sesi pengguna.
- Password reset menggunakan token.
- Data aplikasi disimpan pada PostgreSQL.

## Status

**Active Development**

Fitur yang sudah tersedia:

- [x] Conversational English Practice
- [x] Grammar & Naturalness Feedback
- [x] Skill Assessment
- [x] Learning Progress
- [x] Learning Analysis
- [x] Personalized Learning Profile
- [x] Sign In dan Sign Up
- [x] Password hashing dan session management
- [x] Password reset
- [x] Persistent learning data
- [x] Conversation history
- [x] Statistics dan progress view

## Future Development

Beberapa pengembangan potensial untuk Aira:

- Improved AI feedback
- Deeper learning analysis
- Adaptive learning
- Pronunciation feedback
- Learning recommendations
- Improved progress visualization
- Performance optimization
