"""
Entry point – Khởi động hệ thống tư vấn tuyển sinh Asia University Vietnam

Cách sử dụng:
    python run.py

Hoặc chạy từng bước:
    python scraper/scraper.py   ← Thu thập dữ liệu trước
    python run.py               ← Khởi động server
"""
import sys
import os
from pathlib import Path

# Thêm thư mục gốc vào sys.path
sys.path.insert(0, str(Path(__file__).parent))

from config import FLASK_PORT, FLASK_HOST, FLASK_DEBUG
from database.models import create_tables
from database.db_manager import get_stats


def check_api_key():
    """Kiểm tra cấu hình API key."""
    from config import GEMINI_API_KEY
    if not GEMINI_API_KEY or GEMINI_API_KEY == 'your_gemini_api_key_here':
        print("\n" + "⚠️ " * 20)
        print("CẢNH BÁO: Chưa cấu hình GEMINI_API_KEY!")
        print("─" * 50)
        print("Để chatbot hoạt động:")
        print("1. Lấy API key miễn phí tại: https://aistudio.google.com/app/apikey")
        print("2. Tạo file .env trong thư mục asia_admission_system/")
        print("3. Thêm dòng: GEMINI_API_KEY=your_api_key_here")
        print("4. Restart server")
        print("⚠️ " * 20 + "\n")
        return False
    print("✅ Gemini API Key: Đã cấu hình")
    return True


def check_database():
    """Kiểm tra dữ liệu trong database."""
    stats = get_stats()
    total = sum(stats.values())
    if total == 0:
        print("\n📭 Database trống! Chạy scraper để thu thập dữ liệu:")
        print("   python scraper/scraper.py")
        print("   Hoặc gọi API: POST /api/scrape\n")
    else:
        print("✅ Database:")
        for table, count in stats.items():
            if count > 0:
                print(f"   • {table}: {count} records")
    return total > 0


def main():
    print("\n" + "═" * 55)
    print("🎓  ASIA UNIVERSITY VIETNAM")
    print("    Hệ thống Tư vấn Tuyển sinh AI")
    print("═" * 55)

    # Khởi tạo database
    print("\n[1/3] Khởi tạo database...")
    create_tables()
    print("✅ Database sẵn sàng")

    # Kiểm tra dữ liệu
    print("\n[2/3] Kiểm tra dữ liệu...")
    check_database()

    # Kiểm tra API key
    print("\n[3/3] Kiểm tra cấu hình...")
    check_api_key()

    # Khởi động Flask server
    print("\n" + "─" * 55)
    print(f"🌐 Server đang khởi động tại: http://localhost:{FLASK_PORT}")
    print(f"📊 API Health:  http://localhost:{FLASK_PORT}/api/health")
    print(f"🤖 Chat UI:    http://localhost:{FLASK_PORT}/")
    print(f"📡 Scrape:     POST http://localhost:{FLASK_PORT}/api/scrape")
    print("─" * 55)
    print("Nhấn Ctrl+C để dừng server\n")

    # Import và chạy Flask app
    from app.app import app
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)


if __name__ == "__main__":
    main()
