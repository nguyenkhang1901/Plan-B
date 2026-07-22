"""
Database Models – Định nghĩa schema SQLite cho hệ thống tư vấn tuyển sinh
Asia University Vietnam
"""
import sqlite3
import sys
from pathlib import Path

# Thêm thư mục gốc vào sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATABASE_PATH


def create_tables():
    """Tạo tất cả các bảng trong database nếu chưa tồn tại."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # ── 1. Thông tin chung về trường ──────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS university_info (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            category    TEXT NOT NULL,   -- e.g. 'overview', 'ranking', 'facility'
            title       TEXT NOT NULL,
            content     TEXT NOT NULL,
            source_url  TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── 2. Chương trình / Ngành học ───────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS programs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,          -- Tên ngành
            name_en         TEXT,                   -- Tên tiếng Anh
            degree          TEXT DEFAULT 'Cử nhân', -- Bậc học
            duration        TEXT DEFAULT '4 năm',   -- Thời gian đào tạo
            description     TEXT,                   -- Mô tả ngành
            career_prospects TEXT,                  -- Cơ hội nghề nghiệp
            study_structure TEXT,                   -- Cấu trúc chương trình (VN + Đài Loan)
            tuition_fee     TEXT,                   -- Học phí
            source_url      TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── 3. Thông tin tuyển sinh ───────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admission_info (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            category        TEXT NOT NULL,   -- e.g. 'requirements', 'process', 'documents', 'schedule'
            title           TEXT NOT NULL,
            content         TEXT NOT NULL,
            year            TEXT,            -- Năm tuyển sinh
            source_url      TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── 4. Học bổng ───────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scholarships (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,       -- Tên học bổng
            scholarship_type TEXT,               -- Loại: 'merit', 'need-based', 'taiwan-govt', etc.
            value           TEXT,                -- Giá trị: '50%', '100%', 'toàn phần'
            value_amount    TEXT,                -- Số tiền cụ thể nếu có
            eligibility     TEXT,                -- Điều kiện nhận
            duration        TEXT,                -- Thời hạn
            description     TEXT,                -- Mô tả chi tiết
            application_process TEXT,            -- Quy trình đăng ký
            deadline        TEXT,                -- Hạn nộp hồ sơ
            source_url      TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── 5. Tin tức & Bài viết ────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news_articles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            category    TEXT,           -- e.g. 'tuyen-sinh', 'hoc-bong', 'su-kien'
            summary     TEXT,
            content     TEXT,
            author      TEXT,
            published_date TEXT,
            url         TEXT UNIQUE,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── 6. Session hội thoại ─────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id          TEXT PRIMARY KEY,    -- UUID
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── 7. Tin nhắn chat ─────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL REFERENCES chat_sessions(id),
            role        TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content     TEXT NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── 8. Log scraping ──────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scrape_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            url         TEXT NOT NULL,
            status      TEXT NOT NULL,   -- 'success', 'failed', 'skipped'
            message     TEXT,
            records_saved INTEGER DEFAULT 0,
            scraped_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Tất cả bảng đã được tạo thành công.")


if __name__ == "__main__":
    create_tables()
