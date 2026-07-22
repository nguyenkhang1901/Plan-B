"""
Gemini AI Agent – Tư vấn tuyển sinh thông minh cho Asia University Vietnam
Sử dụng RAG (Retrieval-Augmented Generation) để trả lời chính xác
Dùng google-genai SDK (REST-based, tương thích Python 3.14)
"""
import sys
from pathlib import Path
from typing import Optional

from google import genai  # type: ignore
from google.genai import types  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import GEMINI_API_KEY, GEMINI_MODEL, MAX_HISTORY_MESSAGES, MAX_CONTEXT_CHARS
from database.db_manager import (
    search_all_content, get_full_knowledge_base,
    create_session, save_message, get_session_history, get_stats
)

# ── System Prompt ─────────────────────────────────────────────────────────────
# ── System Prompts ─────────────────────────────────────────────────────────────
BASE_SYSTEM_PROMPT_VI = """Bạn là **Trợ lý Tư vấn Tuyển sinh AI** của **Asia University Vietnam** – chương trình liên kết đào tạo quốc tế giữa Asia University (Đài Loan) và Đại học FPT (Việt Nam).

## Vai trò của bạn:
Hỗ trợ thí sinh, phụ huynh và người quan tâm tìm hiểu về:
- Chương trình đào tạo và các ngành học
- Điều kiện và quy trình tuyển sinh
- Học bổng và hỗ trợ tài chính
- Học phí và chi phí du học Đài Loan
- Cuộc sống và cơ hội nghề nghiệp sau tốt nghiệp
- Thông tin về Asia University Đài Loan và ĐH FPT

## Nguyên tắc trả lời:
1. **QUAN TRỌNG: Luôn trả lời bằng TIẾNG VIỆT**, bất kể người dùng hỏi bằng ngôn ngữ nào.
2. **Chính xác**: Chỉ trả lời dựa trên thông tin có trong DỮ LIỆU THAM KHẢO. Nếu không có thông tin, hãy nói thẳng và hướng dẫn liên hệ phòng tuyển sinh.
3. **Thân thiện**: Dùng ngôn ngữ tự nhiên, ấm áp, phù hợp với học sinh và phụ huynh Việt Nam.
4. **Cấu trúc rõ ràng**: Dùng bullet points, số thứ tự cho thông tin có nhiều mục.
5. **Proactive**: Đề xuất thêm thông tin liên quan mà người dùng có thể muốn biết.
6. **Giới hạn**: Không bịa đặt thông tin. Nếu không chắc, hãy khuyên liên hệ trực tiếp.

## Thông tin liên hệ:
- Website: https://asia-vn.edu.vn
- Tuyển sinh: https://asia-vn.edu.vn/tuyen-sinh/
- Facebook: Asia University Vietnam
"""

BASE_SYSTEM_PROMPT_EN = """You are the **AI Admission Consulting Assistant** of **Asia University Vietnam** – an international joint education program between Asia University (Taiwan) and FPT University (Vietnam).

## Your Role:
Help prospective students, parents and interested parties learn about:
- Academic programs and majors
- Admission requirements and procedures
- Scholarships and financial support
- Tuition fees and cost of studying in Taiwan
- Campus life and career opportunities after graduation
- Information about Asia University Taiwan and FPT University

## Response Guidelines:
1. **IMPORTANT: Always respond in ENGLISH**, regardless of the language the user writes in.
2. **Accurate**: Only answer based on information in the REFERENCE DATA. If no information is available, say so clearly and direct them to the admissions office.
3. **Friendly**: Use natural, warm language appropriate for students and parents.
4. **Clear structure**: Use bullet points and numbered lists for multi-item information.
5. **Proactive**: Suggest related information the user might want to know.
6. **Limit**: Do not fabricate information. If unsure, advise contacting directly.

## Contact Information:
- Website: https://asia-vn.edu.vn
- Admissions: https://asia-vn.edu.vn/tuyen-sinh/
- Facebook: Asia University Vietnam
"""


class GeminiAdmissionAgent:
    """AI Agent tư vấn tuyển sinh sử dụng Google GenAI SDK (REST-based)."""

    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError(
                "Thiếu GEMINI_API_KEY! Vui lòng thêm vào file .env\n"
                "Lấy API key miễn phí tại: https://aistudio.google.com/app/apikey"
            )
        self._client = genai.Client(api_key=GEMINI_API_KEY)
        self._knowledge_base: Optional[str] = None

    def _get_knowledge_base(self) -> str:
        """Lấy knowledge base (cache để tránh query nhiều lần)."""
        if self._knowledge_base is None:
            self._knowledge_base = get_full_knowledge_base()
        return self._knowledge_base

    def refresh_knowledge_base(self):
        """Làm mới knowledge base (gọi sau khi scraper chạy xong)."""
        self._knowledge_base = get_full_knowledge_base()

    def _build_context(self, user_message: str) -> str:
        """Xây dựng context từ database dựa trên câu hỏi của người dùng."""
        relevant_info = search_all_content(user_message, limit=5)

        if not relevant_info:
            kb = self._get_knowledge_base()
            return kb[:MAX_CONTEXT_CHARS]

        combined = relevant_info
        if len(combined) < MAX_CONTEXT_CHARS // 2:
            kb = self._get_knowledge_base()
            remaining = MAX_CONTEXT_CHARS - len(combined)
            combined += "\n\n--- THÊM TỪ KNOWLEDGE BASE ---\n" + kb[:remaining]

        return combined[:MAX_CONTEXT_CHARS]

    def chat(self, user_message: str, session_id: Optional[str] = None, language: str = 'vi') -> tuple[str, str]:
        """
        Gửi tin nhắn và nhận phản hồi từ AI.
        Args:
            user_message: Nội dung tin nhắn
            session_id: ID phiên chat (tạo mới nếu None)
            language: Ngôn ngữ phản hồi – 'vi' (tiếng Việt) hoặc 'en' (English)
        Returns: (response_text, session_id)
        """
        # Chọn system prompt theo ngôn ngữ
        system_prompt = BASE_SYSTEM_PROMPT_EN if language == 'en' else BASE_SYSTEM_PROMPT_VI
        if not session_id:
            session_id = create_session()

        save_message(session_id, 'user', user_message)

        history = get_session_history(session_id, limit=MAX_HISTORY_MESSAGES)
        context = self._build_context(user_message)

        # Xây dựng lịch sử chat (bỏ tin nhắn cuối – user message hiện tại)
        contents = []
        for msg in history[:-1]:
            role = "user" if msg['role'] == 'user' else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=msg['content'])]
            ))

        # Thêm tin nhắn hiện tại với context
        context_prefix = f"[DỮ LIỆU THAM KHẢO:\n{context}\n]\n\n" if context else ""
        current_message = context_prefix + user_message
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=current_message)]
        ))

        try:
            response = self._client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                    top_p=0.95,
                    max_output_tokens=2048,
                )
            )
            assistant_message = response.text

        except Exception as e:
            if language == 'en':
                assistant_message = (
                    f"Sorry, I encountered an error processing your question.\n"
                    f"Please try again or contact us directly:\n"
                    f"• Website: https://asia-vn.edu.vn\n\n"
                    f"(Technical error: {str(e)[:200]})"
                )
            else:
                assistant_message = (
                    f"Xin lỗi, tôi gặp lỗi khi xử lý câu hỏi của bạn.\n"
                    f"Vui lòng thử lại hoặc liên hệ trực tiếp:\n"
                    f"• Website: https://asia-vn.edu.vn\n\n"
                    f"(Lỗi kỹ thuật: {str(e)[:200]})"
                )

        save_message(session_id, 'assistant', assistant_message)
        return assistant_message, session_id

    def get_greeting(self) -> str:
        """Trả về tin nhắn chào hỏi ban đầu."""
        stats = get_stats()
        has_data = any(v > 0 for v in stats.values())

        if has_data:
            return (
                "👋 Xin chào! Tôi là **Trợ lý Tư vấn Tuyển sinh AI** của **Asia University Vietnam**.\n\n"
                "Tôi có thể giúp bạn tìm hiểu về:\n"
                "🎓 **Ngành học** – CNTT, Bán dẫn, QTKD, Thiết kế...\n"
                "📋 **Tuyển sinh** – Điều kiện, hồ sơ, quy trình\n"
                "🏆 **Học bổng** – Các loại học bổng hấp dẫn\n"
                "✈️ **Du học Đài Loan** – Chi phí, cuộc sống, cơ hội\n\n"
                "Bạn muốn biết thêm điều gì về Asia University Vietnam?"
            )
        else:
            return (
                "👋 Xin chào! Tôi là **Trợ lý Tư vấn Tuyển sinh AI** của **Asia University Vietnam**.\n\n"
                "Bạn muốn hỏi gì về Asia University Vietnam?"
            )


# Singleton instance
_agent_instance: Optional[GeminiAdmissionAgent] = None


def get_agent() -> GeminiAdmissionAgent:
    """Lấy singleton instance của agent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = GeminiAdmissionAgent()
    return _agent_instance
