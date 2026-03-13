<div align="center">
  <h1>📚 Metomi</h1>
  <p>A Modern & Lightweight Self-hosted E-book Manager</p>
  <p>
    <b>English</b> | <a href="./README_zh.md">中文</a>
  </p>
</div>

## ✨ Features

- **🖥 Modern UI**: Built with Vue 3 + Composition API, providing a smooth SPA experience and a beautiful design perfectly adapted for both desktop and mobile.
- **📖 Immersive Web Reader**: Built-in powerful web reader. Seamlessly open and read **PDF** and **EPUB** formats directly without downloading.
- **⚡️ Blazing Fast Backend**: Powered by Python FastAPI with a fully asynchronous architecture for rapid responses.
- **🕷 Smart Metadata Scraper**: Automatically fetch book titles, authors, publishers, descriptions, and high-res covers from external sources (e.g., Douban).
- **💾 Native Download Streaming**: Supports browser-native download progress bars, streaming large files directly from the server to prevent memory exhaustion.
- **🔒 Secure & Robust**: Hardened against common self-hosting security risks like Path Traversal and SSRF, ensuring your personal data stays safe.
- **🚀 Zero-config Startup**: The backend automatically initializes the SQLite database and necessary structures out-of-the-box.

---

## 📸 Screenshots

### Login Page
<img src="./docs/images/login.png" alt="Login" width="800">

### Library Dashboard
<img src="./docs/images/library.png" alt="Library" width="800">

### Web Reader
<img src="./docs/images/reader.png" alt="Reader" width="800">

---

## 🛠 Tech Stack

### Frontend
- **Core Framework**: Vue 3 (Composition API)
- **Routing**: Vue Router
- **HTTP Client**: Axios
- **Reader Core**: PDF.js, Epub.js
- **Build Tool**: Vite

### Backend
- **Core Framework**: FastAPI (Python)
- **Database & ORM**: SQLite, SQLAlchemy
- **Migrations**: Alembic
- **Validation**: Pydantic
- **Security**: JWT Authentication, bcrypt Password Hashing

---

## 🚀 Getting Started

### Option 1: Docker (Recommended) 🐳

You can quickly deploy Metomi using Docker. A unified image that includes both the frontend and backend is provided via `docker-compose.yml` in the project root.

1. **Download the configuration file**
   ```bash
   mkdir metomi && cd metomi
   wget https://raw.githubusercontent.com/SiwayLab/metomi/refs/heads/main/docker-compose.yml
   ```
2. Start the service:
   ```bash
   docker-compose up -d
   ```
3. Access the system:
   Open your browser and navigate to `http://localhost:8000`.

### Option 2: Manual Setup for Development 💻

Ensure you have Python 3.9+ and Node.js 16+ installed.

#### Backend Setup:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows, use .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend Setup:
```bash
cd frontend
npm install
npm run dev
```

---

## 🤝 Contributing

Issues and Pull Requests are welcome! This started as a personal self-hosted project, but we believe open source can make it even better. 
If you find this project helpful, please give it a ⭐️ Star!

## 📄 License

This project is licensed under the MIT License.
