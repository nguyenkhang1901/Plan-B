"""
Flask Backend – API Server cho hệ thống tư vấn tuyển sinh Asia University Vietnam
"""
import sys
import threading
from pathlib import Path
from flask import Flask, request, jsonify, render_template, session  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG, SECRET_KEY
from database.models import create_tables
from database.db_manager import get_all_programs, get_all_scholarships, get_stats
from ai.gemini_agent import get_agent

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['JSON_AS_ASCII'] = False  # Hỗ trợ tiếng Việt trong JSON

# ── Khởi tạo database ────────────────────────────────────────────────────────
create_tables()


# ═══════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """Trang chat UI chính."""
    return render_template('index.html')


@app.route('/api/health', methods=['GET'])
def health():
    """Kiểm tra trạng thái hệ thống."""
    stats = get_stats()
    has_data = any(v > 0 for v in stats.values())
    return jsonify({
        'status': 'ok',
        'database_stats': stats,
        'has_data': has_data,
        'message': 'Hệ thống hoạt động bình thường'
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint xử lý tin nhắn chat."""
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'Thiếu trường message'}), 400

    user_message = data['message'].strip()
    if not user_message:
        return jsonify({'error': 'Tin nhắn không được để trống'}), 400

    if len(user_message) > 2000:
        return jsonify({'error': 'Tin nhắn quá dài (tối đa 2000 ký tự)'}), 400

    # Lấy session_id và language từ request
    session_id = data.get('session_id') or session.get('chat_session_id')
    language = data.get('language', 'vi')  # 'vi' hoặc 'en'
    if language not in ('vi', 'en'):
        language = 'vi'

    try:
        agent = get_agent()
        response_text, session_id = agent.chat(user_message, session_id, language=language)

        # Lưu session_id vào Flask session
        session['chat_session_id'] = session_id

        return jsonify({
            'response': response_text,
            'session_id': session_id,
            'status': 'success'
        })

    except ValueError as e:
        # Lỗi cấu hình (thiếu API key, ...)
        return jsonify({
            'error': str(e),
            'status': 'config_error'
        }), 503
    except Exception as e:
        return jsonify({
            'error': f'Lỗi hệ thống: {str(e)[:200]}',
            'status': 'error'
        }), 500


@app.route('/api/greeting', methods=['GET'])
def greeting():
    """Lấy tin nhắn chào hỏi ban đầu."""
    try:
        agent = get_agent()
        return jsonify({
            'greeting': agent.get_greeting(),
            'status': 'success'
        })
    except ValueError as e:
        return jsonify({
            'greeting': (
                "👋 Xin chào! Tôi là Trợ lý AI của Asia University Vietnam.\n"
                "⚠️ Lưu ý: Chưa cấu hình Gemini API key. "
                "Vui lòng thêm GEMINI_API_KEY vào file .env để sử dụng chatbot."
            ),
            'status': 'no_api_key'
        })


@app.route('/api/programs', methods=['GET'])
def programs():
    """Lấy danh sách ngành học."""
    data = get_all_programs()
    return jsonify({'programs': data, 'count': len(data)})


@app.route('/api/scholarships', methods=['GET'])
def scholarships():
    """Lấy danh sách học bổng."""
    data = get_all_scholarships()
    return jsonify({'scholarships': data, 'count': len(data)})


@app.route('/api/stats', methods=['GET'])
def stats():
    """Thống kê database."""
    return jsonify(get_stats())


@app.route('/api/scrape', methods=['POST'])
def trigger_scrape():
    """Trigger chạy scraper trong background thread."""
    def run_scraper_thread():
        try:
            from scraper.scraper import run_scraper
            run_scraper()
            # Refresh knowledge base sau khi scrape xong
            try:
                agent = get_agent()
                agent.refresh_knowledge_base()
            except Exception:
                pass
        except Exception as e:
            print(f"[Scraper Error] {e}")

    thread = threading.Thread(target=run_scraper_thread, daemon=True)
    thread.start()

    return jsonify({
        'status': 'started',
        'message': 'Scraper đang chạy trong background. Kiểm tra /api/stats để xem tiến trình.'
    })


@app.route('/api/new-session', methods=['POST'])
def new_session():
    """Tạo session chat mới."""
    session.pop('chat_session_id', None)
    return jsonify({'status': 'ok', 'message': 'Đã tạo session mới'})


# ═══════════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint không tồn tại'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Lỗi server nội bộ'}), 500


if __name__ == '__main__':
    print(f"\n{'='*50}")
    print("🎓 ASIA UNIVERSITY VIETNAM - AI Admission Chatbot")
    print(f"{'='*50}")
    print(f"🌐 Truy cập: http://localhost:{FLASK_PORT}")
    print(f"📊 API Health: http://localhost:{FLASK_PORT}/api/health")
    print(f"{'='*50}\n")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
