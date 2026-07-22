"""
Database Manager – Các hàm CRUD cho hệ thống tư vấn tuyển sinh
Asia University Vietnam
"""
import sqlite3
import uuid
from datetime import datetime
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATABASE_PATH


def get_connection():
    """Tạo kết nối đến SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Trả về dict-like rows
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ═══════════════════════════════════════════════════════════════════
# UNIVERSITY INFO
# ═══════════════════════════════════════════════════════════════════

def upsert_university_info(category: str, title: str, content: str, source_url: str = None):
    """Thêm hoặc cập nhật thông tin trường."""
    conn = get_connection()
    cursor = conn.cursor()
    # Kiểm tra đã tồn tại chưa
    cursor.execute(
        "SELECT id FROM university_info WHERE category=? AND title=?",
        (category, title)
    )
    row = cursor.fetchone()
    if row:
        cursor.execute(
            "UPDATE university_info SET content=?, source_url=?, updated_at=? WHERE id=?",
            (content, source_url, datetime.now(), row["id"])
        )
    else:
        cursor.execute(
            "INSERT INTO university_info (category, title, content, source_url) VALUES (?,?,?,?)",
            (category, title, content, source_url)
        )
    conn.commit()
    conn.close()


def get_all_university_info():
    """Lấy toàn bộ thông tin trường."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM university_info ORDER BY category, id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════
# PROGRAMS
# ═══════════════════════════════════════════════════════════════════

def upsert_program(name: str, **kwargs):
    """Thêm hoặc cập nhật ngành học."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM programs WHERE name=?", (name,))
    row = cursor.fetchone()
    if row:
        set_clause = ", ".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values()) + [datetime.now(), row["id"]]
        cursor.execute(
            f"UPDATE programs SET {set_clause}, updated_at=? WHERE id=?", values
        )
    else:
        cols = "name, " + ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * (len(kwargs) + 1))
        values = [name] + list(kwargs.values())
        cursor.execute(
            f"INSERT INTO programs ({cols}) VALUES ({placeholders})", values
        )
    conn.commit()
    conn.close()


def get_all_programs():
    """Lấy tất cả ngành học."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM programs ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════
# ADMISSION INFO
# ═══════════════════════════════════════════════════════════════════

def upsert_admission_info(category: str, title: str, content: str,
                          year: str = None, source_url: str = None):
    """Thêm hoặc cập nhật thông tin tuyển sinh."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM admission_info WHERE category=? AND title=?",
        (category, title)
    )
    row = cursor.fetchone()
    if row:
        cursor.execute(
            "UPDATE admission_info SET content=?, year=?, source_url=?, updated_at=? WHERE id=?",
            (content, year, source_url, datetime.now(), row["id"])
        )
    else:
        cursor.execute(
            "INSERT INTO admission_info (category, title, content, year, source_url) VALUES (?,?,?,?,?)",
            (category, title, content, year, source_url)
        )
    conn.commit()
    conn.close()


def get_admission_info(category: str = None):
    """Lấy thông tin tuyển sinh, lọc theo category nếu có."""
    conn = get_connection()
    if category:
        rows = conn.execute(
            "SELECT * FROM admission_info WHERE category=? ORDER BY id", (category,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM admission_info ORDER BY category, id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════
# SCHOLARSHIPS
# ═══════════════════════════════════════════════════════════════════

def upsert_scholarship(name: str, **kwargs):
    """Thêm hoặc cập nhật học bổng."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM scholarships WHERE name=?", (name,))
    row = cursor.fetchone()
    if row:
        set_clause = ", ".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values()) + [datetime.now(), row["id"]]
        cursor.execute(
            f"UPDATE scholarships SET {set_clause}, updated_at=? WHERE id=?", values
        )
    else:
        cols = "name, " + ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * (len(kwargs) + 1))
        values = [name] + list(kwargs.values())
        cursor.execute(
            f"INSERT INTO scholarships ({cols}) VALUES ({placeholders})", values
        )
    conn.commit()
    conn.close()


def get_all_scholarships():
    """Lấy tất cả học bổng."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM scholarships ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════
# NEWS ARTICLES
# ═══════════════════════════════════════════════════════════════════

def upsert_news(title: str, url: str, **kwargs):
    """Thêm hoặc cập nhật tin tức."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM news_articles WHERE url=?", (url,))
    row = cursor.fetchone()
    if row:
        set_clause = ", ".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values()) + [row["id"]]
        cursor.execute(
            f"UPDATE news_articles SET {set_clause} WHERE id=?", values
        )
    else:
        cols = "title, url, " + ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * (len(kwargs) + 2))
        values = [title, url] + list(kwargs.values())
        cursor.execute(
            f"INSERT OR IGNORE INTO news_articles ({cols}) VALUES ({placeholders})", values
        )
    conn.commit()
    conn.close()


def get_recent_news(limit: int = 10):
    """Lấy tin tức mới nhất."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM news_articles ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════
# CHAT SESSIONS & MESSAGES
# ═══════════════════════════════════════════════════════════════════

def create_session() -> str:
    """Tạo session chat mới, trả về session_id."""
    session_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute("INSERT INTO chat_sessions (id) VALUES (?)", (session_id,))
    conn.commit()
    conn.close()
    return session_id


def save_message(session_id: str, role: str, content: str):
    """Lưu tin nhắn vào database."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO chat_messages (session_id, role, content) VALUES (?,?,?)",
        (session_id, role, content)
    )
    conn.execute(
        "UPDATE chat_sessions SET updated_at=? WHERE id=?",
        (datetime.now(), session_id)
    )
    conn.commit()
    conn.close()


def get_session_history(session_id: str, limit: int = 10):
    """Lấy lịch sử hội thoại của session."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT role, content, created_at FROM chat_messages
           WHERE session_id=? ORDER BY created_at DESC LIMIT ?""",
        (session_id, limit)
    ).fetchall()
    conn.close()
    # Đảo ngược để có thứ tự thời gian tăng dần
    return [dict(r) for r in reversed(rows)]


# ═══════════════════════════════════════════════════════════════════
# SCRAPE LOGS
# ═══════════════════════════════════════════════════════════════════

def log_scrape(url: str, status: str, message: str = None, records_saved: int = 0):
    """Ghi log kết quả scraping."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO scrape_logs (url, status, message, records_saved) VALUES (?,?,?,?)",
        (url, status, message, records_saved)
    )
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════
# SEARCH – Dùng cho RAG context
# ═══════════════════════════════════════════════════════════════════

def search_all_content(query: str, limit: int = 5) -> str:
    """
    Tìm kiếm nội dung liên quan đến query trong tất cả các bảng.
    Trả về chuỗi text làm context cho AI.
    """
    conn = get_connection()
    results = []
    query_lower = f"%{query.lower()}%"

    # Tìm trong university_info
    rows = conn.execute(
        "SELECT title, content FROM university_info WHERE LOWER(title) LIKE ? OR LOWER(content) LIKE ? LIMIT ?",
        (query_lower, query_lower, limit)
    ).fetchall()
    for r in rows:
        results.append(f"[Thông tin trường] {r['title']}:\n{r['content']}")

    # Tìm trong admission_info
    rows = conn.execute(
        "SELECT title, content FROM admission_info WHERE LOWER(title) LIKE ? OR LOWER(content) LIKE ? LIMIT ?",
        (query_lower, query_lower, limit)
    ).fetchall()
    for r in rows:
        results.append(f"[Tuyển sinh] {r['title']}:\n{r['content']}")

    # Tìm trong scholarships
    rows = conn.execute(
        """SELECT name, value, eligibility, description FROM scholarships
           WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(eligibility) LIKE ? LIMIT ?""",
        (query_lower, query_lower, query_lower, limit)
    ).fetchall()
    for r in rows:
        results.append(
            f"[Học bổng] {r['name']}: Giá trị {r['value'] or 'N/A'}\n"
            f"Điều kiện: {r['eligibility'] or 'N/A'}\n{r['description'] or ''}"
        )

    # Tìm trong programs
    rows = conn.execute(
        """SELECT name, description, career_prospects, tuition_fee FROM programs
           WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ? LIMIT ?""",
        (query_lower, query_lower, limit)
    ).fetchall()
    for r in rows:
        results.append(
            f"[Ngành học] {r['name']}: {r['description'] or ''}\n"
            f"Cơ hội nghề nghiệp: {r['career_prospects'] or 'N/A'}\n"
            f"Học phí: {r['tuition_fee'] or 'N/A'}"
        )

    # Tìm trong news
    rows = conn.execute(
        "SELECT title, summary FROM news_articles WHERE LOWER(title) LIKE ? OR LOWER(summary) LIKE ? LIMIT ?",
        (query_lower, query_lower, 3)
    ).fetchall()
    for r in rows:
        results.append(f"[Tin tức] {r['title']}:\n{r['summary'] or ''}")

    conn.close()
    return "\n\n---\n\n".join(results)


def get_full_knowledge_base() -> str:
    """Lấy toàn bộ dữ liệu làm knowledge base cho AI."""
    conn = get_connection()
    sections = []

    # Thông tin trường
    rows = conn.execute("SELECT title, content FROM university_info ORDER BY category, id").fetchall()
    if rows:
        sections.append("=== THÔNG TIN TRƯỜNG ===")
        for r in rows:
            sections.append(f"• {r['title']}:\n{r['content']}")

    # Tuyển sinh
    rows = conn.execute("SELECT title, content FROM admission_info ORDER BY category, id").fetchall()
    if rows:
        sections.append("\n=== THÔNG TIN TUYỂN SINH ===")
        for r in rows:
            sections.append(f"• {r['title']}:\n{r['content']}")

    # Học bổng
    rows = conn.execute("SELECT name, value, eligibility, description, application_process FROM scholarships").fetchall()
    if rows:
        sections.append("\n=== HỌC BỔNG ===")
        for r in rows:
            sections.append(
                f"• {r['name']} (Giá trị: {r['value'] or 'N/A'}):\n"
                f"  Điều kiện: {r['eligibility'] or 'N/A'}\n"
                f"  Mô tả: {r['description'] or 'N/A'}\n"
                f"  Quy trình: {r['application_process'] or 'N/A'}"
            )

    # Ngành học
    rows = conn.execute("SELECT name, description, career_prospects, tuition_fee, study_structure FROM programs").fetchall()
    if rows:
        sections.append("\n=== NGÀNH HỌC ===")
        for r in rows:
            sections.append(
                f"• {r['name']}:\n"
                f"  Mô tả: {r['description'] or 'N/A'}\n"
                f"  Cơ hội nghề nghiệp: {r['career_prospects'] or 'N/A'}\n"
                f"  Học phí: {r['tuition_fee'] or 'N/A'}"
            )

    conn.close()
    return "\n".join(sections)


def get_stats() -> dict:
    """Thống kê số lượng records trong database."""
    conn = get_connection()
    stats = {
        "university_info": conn.execute("SELECT COUNT(*) FROM university_info").fetchone()[0],
        "programs": conn.execute("SELECT COUNT(*) FROM programs").fetchone()[0],
        "admission_info": conn.execute("SELECT COUNT(*) FROM admission_info").fetchone()[0],
        "scholarships": conn.execute("SELECT COUNT(*) FROM scholarships").fetchone()[0],
        "news_articles": conn.execute("SELECT COUNT(*) FROM news_articles").fetchone()[0],
    }
    conn.close()
    return stats
