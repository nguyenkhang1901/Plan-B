"""
Cấu hình chung cho hệ thống tư vấn tuyển sinh Asia University Vietnam
"""
import os
from pathlib import Path
from dotenv import load_dotenv  # type: ignore

# Load biến môi trường từ file .env
load_dotenv()

# ========================
# Đường dẫn thư mục
# ========================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ========================
# Database
# ========================
DATABASE_PATH = str(DATA_DIR / "asia_university.db")

# ========================
# Gemini API
# ========================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

# ========================
# Scraper
# ========================
BASE_URL = "https://asia-vn.edu.vn"

# Danh sách URL cần cào dữ liệu
SCRAPE_URLS = {
    "home": "https://asia-vn.edu.vn/",
    "admission": "https://asia-vn.edu.vn/tuyen-sinh/",
    "scholarship": "https://asia-vn.edu.vn/hoc-bong/",
    "programs": "https://asia-vn.edu.vn/nganh-hoc/",
    "about": "https://asia-vn.edu.vn/gioi-thieu/",
    "news": "https://asia-vn.edu.vn/tin-tuc/",
    "contact": "https://asia-vn.edu.vn/lien-he/",
    "fee": "https://asia-vn.edu.vn/hoc-phi/",
    "life_taiwan": "https://asia-vn.edu.vn/cuoc-song-dai-loan/",
}

# HTTP Headers để tránh bị block
SCRAPER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Delay giữa các request (giây)
SCRAPER_DELAY = 1.5

# ========================
# Flask
# ========================
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = False
SECRET_KEY = os.getenv("SECRET_KEY", "asia-vietnam-admission-2024")

# ========================
# Chatbot
# ========================
MAX_HISTORY_MESSAGES = 10  # Số tin nhắn lưu trong lịch sử hội thoại
MAX_CONTEXT_CHARS = 8000   # Số ký tự tối đa của context từ database
