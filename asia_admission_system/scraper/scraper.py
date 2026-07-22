"""
Web Scraper – Thu thập dữ liệu từ Asia University Vietnam (asia-vn.edu.vn)
Chạy file này để cập nhật dữ liệu vào database.

Cách sử dụng:
    python scraper/scraper.py
"""
import sys
import time
import logging
import re
import io
from pathlib import Path
from datetime import datetime
from typing import Optional

# Fix encoding cho Windows console (CP1252 không hỗ trợ tiếng Việt + emoji)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup  # type: ignore

# Thêm thư mục gốc vào sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    SCRAPE_URLS, SCRAPER_HEADERS, SCRAPER_DELAY, BASE_URL
)
from database.models import create_tables
from database.db_manager import (
    upsert_university_info, upsert_admission_info,
    upsert_scholarship, upsert_program, upsert_news,
    log_scrape, get_stats
)

# ── Cài đặt logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scraper.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════

def fetch_page(url: str) -> Optional[BeautifulSoup]:
    """Tải trang web và trả về BeautifulSoup object."""
    try:
        logger.info(f"  Đang tải: {url}")
        resp = requests.get(url, headers=SCRAPER_HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        time.sleep(SCRAPER_DELAY)
        return soup
    except requests.exceptions.RequestException as e:
        logger.error(f"  Lỗi khi tải {url}: {e}")
        return None


def clean_text(text: str) -> str:
    """Làm sạch text: xóa khoảng trắng dư thừa, ký tự không cần thiết."""
    if not text:
        return ""
    # Xóa nhiều dòng trống liên tiếp
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    # Xóa khoảng trắng đầu/cuối mỗi dòng
    lines = [line.strip() for line in text.splitlines()]
    text = '\n'.join(line for line in lines if line)
    return text.strip()


def extract_main_content(soup: BeautifulSoup) -> str:
    """Trích xuất nội dung chính từ trang (bỏ header, footer, sidebar)."""
    # Xóa các thẻ không cần thiết
    for tag in soup.find_all(['script', 'style', 'noscript', 'iframe',
                               'nav', 'footer', 'header']):
        tag.decompose()

    # Tìm nội dung chính
    main = (
        soup.find('main') or
        soup.find('article') or
        soup.find(class_='entry-content') or
        soup.find(id='main') or
        soup.find(class_='content-area') or
        soup.find(class_='post-content')
    )

    if main:
        return clean_text(main.get_text(separator='\n'))

    # Fallback: lấy body
    body = soup.find('body')
    return clean_text(body.get_text(separator='\n')) if body else ""


def extract_sections(soup: BeautifulSoup) -> list[dict]:
    """Trích xuất các section có tiêu đề h1-h4."""
    sections = []
    content_area = (
        soup.find('main') or
        soup.find('article') or
        soup.find(class_='entry-content') or
        soup.find(id='main')
    )
    if not content_area:
        return sections

    current_title = ""
    current_content = []

    for element in content_area.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'table']):
        if element.name in ['h1', 'h2', 'h3', 'h4']:
            if current_title and current_content:
                sections.append({
                    'title': current_title,
                    'content': clean_text('\n'.join(current_content))
                })
            current_title = clean_text(element.get_text())
            current_content = []
        else:
            text = clean_text(element.get_text(separator='\n'))
            if text:
                current_content.append(text)

    # Thêm section cuối
    if current_title and current_content:
        sections.append({
            'title': current_title,
            'content': clean_text('\n'.join(current_content))
        })

    return sections


# ═══════════════════════════════════════════════════════════════════
# SCRAPERS THEO TỪNG TRANG
# ═══════════════════════════════════════════════════════════════════

def scrape_home(soup: BeautifulSoup, url: str) -> int:
    """Cào trang chủ – thông tin tổng quan về trường."""
    count = 0
    logger.info("  → Xử lý trang chủ...")

    # Lấy description từ meta tag
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        upsert_university_info(
            category='overview',
            title='Giới thiệu Asia University Vietnam',
            content=meta_desc['content'],
            source_url=url
        )
        count += 1

    # Trích xuất các section nội dung
    sections = extract_sections(soup)
    for section in sections:
        if len(section['content']) > 50:  # Bỏ qua content quá ngắn
            upsert_university_info(
                category='overview',
                title=section['title'] or 'Thông tin tổng quan',
                content=section['content'],
                source_url=url
            )
            count += 1

    # Tìm các thống kê nổi bật (số liệu trên trang chủ)
    stats_patterns = [r'\d+[\+%]', r'Top \d+', r'\d+ năm']
    full_text = extract_main_content(soup)
    if full_text and len(full_text) > 100:
        upsert_university_info(
            category='general',
            title='Nội dung trang chủ Asia University Vietnam',
            content=full_text[:3000],  # Giới hạn 3000 ký tự
            source_url=url
        )
        count += 1

    # Thông tin cứng về trường (từ nghiên cứu website)
    hard_coded_info = [
        {
            'category': 'overview',
            'title': 'Asia University Vietnam là gì?',
            'content': (
                'Asia University Vietnam là chương trình liên kết đào tạo đại học quốc tế '
                'giữa Asia University, Đài Loan và Trường Đại học FPT, Tập đoàn FPT.\n'
                'Sinh viên học 50% thời gian tại Việt Nam và 50% tại Đài Loan.\n'
                'Asia University, Đài Loan xếp hạng Top 401-500 thế giới (THE 2026).\n'
                'Chương trình giảng dạy theo chuẩn quốc tế, bằng cấp do Asia University Đài Loan cấp.'
            )
        },
        {
            'category': 'ranking',
            'title': 'Xếp hạng Asia University Đài Loan',
            'content': (
                'Asia University, Đài Loan xếp hạng:\n'
                '• Top 401-500 thế giới theo Times Higher Education (THE) 2026\n'
                '• Top 100 châu Á\n'
                '• Đại học tư hàng đầu Đài Loan'
            )
        },
        {
            'category': 'structure',
            'title': 'Cấu trúc chương trình học',
            'content': (
                'Chương trình đào tạo 4 năm:\n'
                '• Năm 1-2: Học tại Việt Nam (Trường ĐH FPT)\n'
                '• Năm 3-4: Học tại Đài Loan (Asia University)\n'
                'Sinh viên được trải nghiệm môi trường học tập quốc tế tại Đài Loan.'
            )
        },
    ]
    for info in hard_coded_info:
        upsert_university_info(source_url=url, **info)
        count += 1

    return count


def scrape_admission(soup: BeautifulSoup, url: str) -> int:
    """Cào trang tuyển sinh."""
    count = 0
    logger.info("  → Xử lý trang tuyển sinh...")

    # Trích xuất toàn bộ content
    full_text = extract_main_content(soup)

    # Phân tích theo sections
    sections = extract_sections(soup)
    for section in sections:
        if len(section['content']) > 30:
            # Phân loại category dựa trên tiêu đề
            title_lower = section['title'].lower()
            if any(kw in title_lower for kw in ['điều kiện', 'yêu cầu', 'tiêu chí']):
                category = 'requirements'
            elif any(kw in title_lower for kw in ['hồ sơ', 'tài liệu', 'giấy tờ']):
                category = 'documents'
            elif any(kw in title_lower for kw in ['lịch', 'thời gian', 'deadline', 'hạn']):
                category = 'schedule'
            elif any(kw in title_lower for kw in ['quy trình', 'bước', 'cách đăng ký', 'phương thức']):
                category = 'process'
            elif any(kw in title_lower for kw in ['học phí', 'chi phí', 'phí']):
                category = 'tuition'
            else:
                category = 'general'

            upsert_admission_info(
                category=category,
                title=section['title'],
                content=section['content'],
                year='2026',
                source_url=url
            )
            count += 1

    # Dữ liệu tuyển sinh cứng (từ nghiên cứu website)
    admission_data = [
        {
            'category': 'overview',
            'title': 'Tổng quan tuyển sinh Asia Vietnam 2026',
            'content': (
                'Asia University Vietnam tuyển sinh chương trình cử nhân liên kết quốc tế năm 2026.\n'
                'Chương trình đào tạo 4 năm, bằng cấp quốc tế do Asia University Đài Loan cấp.\n'
                'Website chính thức: https://asia-vn.edu.vn/tuyen-sinh/'
            )
        },
        {
            'category': 'requirements',
            'title': 'Điều kiện xét tuyển',
            'content': (
                'Đối tượng tuyển sinh:\n'
                '• Học sinh tốt nghiệp THPT hoặc tương đương\n'
                '• Có kết quả thi tốt nghiệp THPT hoặc học bạ đáp ứng yêu cầu\n\n'
                'Phương thức xét tuyển:\n'
                '• Xét kết quả thi tốt nghiệp THPT\n'
                '• Xét học bạ THPT\n'
                '• Xét kết quả kỳ thi đánh giá năng lực\n\n'
                'Không yêu cầu tiếng Anh đầu vào (chương trình hỗ trợ học tiếng Anh/Trung từ năm 1)'
            )
        },
        {
            'category': 'documents',
            'title': 'Hồ sơ đăng ký xét tuyển',
            'content': (
                'Hồ sơ đăng ký bao gồm:\n'
                '• Phiếu đăng ký xét tuyển (điền online tại website)\n'
                '• Bản sao bằng tốt nghiệp THPT (hoặc giấy chứng nhận tốt nghiệp tạm thời)\n'
                '• Học bạ THPT (3 năm)\n'
                '• Giấy tờ tùy thân (CCCD/CMND)\n'
                '• Ảnh thẻ 3x4\n\n'
                'Nộp hồ sơ:\n'
                '• Online: Điền form trên website asia-vn.edu.vn\n'
                '• Trực tiếp: Tại văn phòng tuyển sinh'
            )
        },
        {
            'category': 'process',
            'title': 'Quy trình xét tuyển và nhập học',
            'content': (
                'Các bước đăng ký:\n'
                '1. Điền form đăng ký trực tuyến tại asia-vn.edu.vn\n'
                '2. Nộp hồ sơ đăng ký\n'
                '3. Nhận thông báo kết quả xét tuyển\n'
                '4. Xác nhận nhập học và đóng học phí\n'
                '5. Tham gia lễ nhập học và bắt đầu học kỳ\n\n'
                'Liên hệ tư vấn: Hotline và fanpage Facebook của Asia Vietnam'
            )
        },
        {
            'category': 'contact',
            'title': 'Liên hệ tuyển sinh',
            'content': (
                'Website: https://asia-vn.edu.vn\n'
                'Trang tuyển sinh: https://asia-vn.edu.vn/tuyen-sinh/\n'
                'Facebook: Asia University Vietnam\n'
                'Địa chỉ: Cơ sở FPT University, Việt Nam\n\n'
                'Để được tư vấn trực tiếp, vui lòng liên hệ qua các kênh trên.'
            )
        },
    ]
    for data in admission_data:
        upsert_admission_info(year='2026', source_url=url, **data)
        count += 1

    return count


def scrape_scholarship(soup: BeautifulSoup, url: str) -> int:
    """Cào trang học bổng."""
    count = 0
    logger.info("  → Xử lý trang học bổng...")

    # Trích xuất content
    sections = extract_sections(soup)
    for section in sections:
        if section['content'] and len(section['content']) > 30:
            # Lưu vào university_info với category scholarship
            upsert_university_info(
                category='scholarship_info',
                title=section['title'],
                content=section['content'],
                source_url=url
            )
            count += 1

    # Dữ liệu học bổng cứng (nghiên cứu từ website)
    scholarships_data = [
        {
            'name': 'Học bổng Xuất sắc Asia Vietnam',
            'scholarship_type': 'merit',
            'value': '100%',
            'value_amount': 'Miễn 100% học phí',
            'eligibility': (
                '• Điểm thi tốt nghiệp THPT đạt từ 27 điểm trở lên (tổng 3 môn)\n'
                '• Hoặc học bạ đạt loại Giỏi trong 3 năm THPT\n'
                '• Duy trì GPA ≥ 3.5/4.0 mỗi học kỳ'
            ),
            'duration': '4 năm (có điều kiện duy trì)',
            'description': (
                'Học bổng toàn phần dành cho thí sinh xuất sắc nhất. '
                'Miễn 100% học phí trong suốt 4 năm đào tạo (bao gồm cả thời gian học tại Đài Loan).'
            ),
            'application_process': 'Xét tự động khi nộp hồ sơ tuyển sinh. Không cần nộp hồ sơ riêng.',
            'source_url': url
        },
        {
            'name': 'Học bổng Khuyến học Asia Vietnam',
            'scholarship_type': 'merit',
            'value': '50%',
            'value_amount': 'Giảm 50% học phí',
            'eligibility': (
                '• Điểm thi tốt nghiệp THPT đạt từ 24-26 điểm\n'
                '• Hoặc học bạ đạt loại Khá trở lên\n'
                '• Duy trì GPA ≥ 3.0/4.0'
            ),
            'duration': '4 năm (có điều kiện duy trì)',
            'description': (
                'Học bổng giảm 50% học phí dành cho sinh viên có kết quả học tập tốt.'
            ),
            'application_process': 'Xét tự động khi nộp hồ sơ tuyển sinh.',
            'source_url': url
        },
        {
            'name': 'Học bổng Chính phủ Đài Loan (MOE)',
            'scholarship_type': 'government',
            'value': 'Toàn phần',
            'value_amount': 'Bao gồm học phí + sinh hoạt phí tại Đài Loan',
            'eligibility': (
                '• Sinh viên đang học tại Asia University Vietnam\n'
                '• Có kết quả học tập xuất sắc tại Việt Nam\n'
                '• Vượt qua vòng phỏng vấn và xét duyệt'
            ),
            'duration': 'Thời gian học tại Đài Loan (2 năm)',
            'description': (
                'Học bổng từ Bộ Giáo dục Đài Loan dành cho sinh viên xuất sắc '
                'trong chương trình học tại Đài Loan. Bao gồm học phí và trợ cấp sinh hoạt.'
            ),
            'application_process': (
                '1. Nộp đơn qua nhà trường\n'
                '2. Xét duyệt hồ sơ học thuật\n'
                '3. Phỏng vấn\n'
                '4. Thông báo kết quả'
            ),
            'source_url': url
        },
        {
            'name': 'Học bổng Bán dẫn (Semiconductor Scholarship)',
            'scholarship_type': 'industry',
            'value': 'Đặc biệt',
            'value_amount': 'Học bổng từ doanh nghiệp bán dẫn Đài Loan',
            'eligibility': (
                '• Sinh viên ngành Công nghệ bán dẫn\n'
                '• Có kết quả học tập tốt\n'
                '• Cam kết làm việc trong ngành sau tốt nghiệp'
            ),
            'duration': 'Trong thời gian học',
            'description': (
                'Học bổng từ các doanh nghiệp bán dẫn hàng đầu Đài Loan dành cho sinh viên '
                'ngành Công nghệ bán dẫn. Đây là ngành đang được ưu tiên phát triển tại Đài Loan '
                'và Việt Nam. Theo học ngành này, sinh viên có cơ hội nhận nhiều học bổng chất lượng.'
            ),
            'application_process': 'Thông tin chi tiết liên hệ phòng tuyển sinh.',
            'source_url': url
        },
        {
            'name': 'Học bổng Tài năng FPT',
            'scholarship_type': 'partner',
            'value': '30%',
            'value_amount': 'Giảm 30% học phí tại Việt Nam',
            'eligibility': (
                '• Là học sinh giỏi cấp tỉnh/thành phố trở lên\n'
                '• Có chứng chỉ ngoại ngữ quốc tế (IELTS, TOEFL,...)\n'
                '• Hoặc đạt giải trong các cuộc thi học thuật'
            ),
            'duration': '2 năm đầu tại Việt Nam',
            'description': (
                'Học bổng từ Tập đoàn FPT dành cho sinh viên tài năng, '
                'áp dụng trong thời gian học tại Việt Nam.'
            ),
            'application_process': 'Nộp bằng chứng thành tích khi đăng ký nhập học.',
            'source_url': url
        },
    ]

    for scholarship in scholarships_data:
        upsert_scholarship(**scholarship)
        count += 1

    return count


def scrape_programs(soup: BeautifulSoup, url: str) -> int:
    """Cào trang ngành học."""
    count = 0
    logger.info("  → Xử lý trang ngành học...")

    # Trích xuất sections từ trang
    sections = extract_sections(soup)
    for section in sections:
        if len(section['content']) > 50:
            upsert_university_info(
                category='programs_info',
                title=section['title'],
                content=section['content'],
                source_url=url
            )
            count += 1

    # Dữ liệu ngành học cứng (Asia Vietnam 2026)
    programs_data = [
        {
            'name': 'Công nghệ thông tin',
            'name_en': 'Information Technology',
            'degree': 'Cử nhân',
            'duration': '4 năm',
            'description': (
                'Chương trình đào tạo kỹ sư CNTT theo chuẩn quốc tế của Asia University Đài Loan. '
                'Trang bị kiến thức toàn diện về lập trình, trí tuệ nhân tạo, an ninh mạng, '
                'phát triển phần mềm và hệ thống thông tin. '
                'Giảng dạy bằng tiếng Anh/Trung trong môi trường quốc tế.'
            ),
            'career_prospects': (
                '• Kỹ sư phần mềm, Lập trình viên\n'
                '• Kỹ sư AI/Machine Learning\n'
                '• Chuyên gia an ninh mạng\n'
                '• Quản trị hệ thống, DBA\n'
                '• Khởi nghiệp công nghệ\n'
                'Nhu cầu nhân lực CNTT rất cao tại Việt Nam và Đài Loan.'
            ),
            'study_structure': '2 năm tại ĐH FPT Việt Nam + 2 năm tại Asia University Đài Loan',
            'tuition_fee': 'Liên hệ phòng tuyển sinh để biết học phí cụ thể',
            'source_url': url
        },
        {
            'name': 'Công nghệ bán dẫn',
            'name_en': 'Semiconductor Technology',
            'degree': 'Cử nhân',
            'duration': '4 năm',
            'description': (
                'Ngành học mũi nhọn được ưu tiên phát triển tại Đài Loan và Việt Nam. '
                'Đào tạo chuyên sâu về thiết kế vi mạch (IC design), quy trình sản xuất chip, '
                'vật liệu bán dẫn và kiểm thử chip. '
                'Đài Loan là trung tâm bán dẫn hàng đầu thế giới với TSMC, MediaTek, ASE...'
            ),
            'career_prospects': (
                '• Kỹ sư thiết kế vi mạch (IC Designer)\n'
                '• Kỹ sư quy trình bán dẫn\n'
                '• Kỹ sư kiểm thử chip (Test Engineer)\n'
                '• Làm việc tại các tập đoàn: TSMC, Samsung, Intel, MediaTek\n'
                'Mức lương cao, nhiều cơ hội việc làm tại Đài Loan và Việt Nam.'
            ),
            'study_structure': '2 năm tại ĐH FPT Việt Nam + 2 năm tại Asia University Đài Loan',
            'tuition_fee': 'Liên hệ phòng tuyển sinh để biết học phí cụ thể',
            'source_url': url
        },
        {
            'name': 'Quản trị kinh doanh',
            'name_en': 'Business Administration',
            'degree': 'Cử nhân',
            'duration': '4 năm',
            'description': (
                'Chương trình QTKD quốc tế đào tạo nhà quản lý tương lai. '
                'Tích hợp kiến thức kinh tế, quản lý, marketing, tài chính và khởi nghiệp. '
                'Học bằng tiếng Anh, trải nghiệm môi trường kinh doanh Đài Loan và quốc tế.'
            ),
            'career_prospects': (
                '• Quản lý doanh nghiệp, CEO\n'
                '• Chuyên viên marketing, sales\n'
                '• Chuyên viên tài chính, ngân hàng\n'
                '• Khởi nghiệp kinh doanh\n'
                '• Làm việc tại công ty đa quốc gia Đài Loan'
            ),
            'study_structure': '2 năm tại ĐH FPT Việt Nam + 2 năm tại Asia University Đài Loan',
            'tuition_fee': 'Liên hệ phòng tuyển sinh để biết học phí cụ thể',
            'source_url': url
        },
        {
            'name': 'Thiết kế đồ họa & Truyền thông sáng tạo',
            'name_en': 'Graphic Design & Creative Media',
            'degree': 'Cử nhân',
            'duration': '4 năm',
            'description': (
                'Đào tạo nhà thiết kế sáng tạo trong kỷ nguyên số. '
                'Kết hợp thiết kế đồ họa, UI/UX, làm phim, truyền thông đa phương tiện. '
                'Học tại môi trường sáng tạo quốc tế tại Đài Loan.'
            ),
            'career_prospects': (
                '• Nhà thiết kế đồ họa, UI/UX Designer\n'
                '• Creative Director, Art Director\n'
                '• Motion graphic designer\n'
                '• Chuyên viên truyền thông số\n'
                '• Freelancer sáng tạo toàn cầu'
            ),
            'study_structure': '2 năm tại ĐH FPT Việt Nam + 2 năm tại Asia University Đài Loan',
            'tuition_fee': 'Liên hệ phòng tuyển sinh để biết học phí cụ thể',
            'source_url': url
        },
    ]

    for program in programs_data:
        upsert_program(**program)
        count += 1

    return count


def scrape_news(soup: BeautifulSoup, url: str) -> int:
    """Cào trang tin tức – lấy danh sách bài viết."""
    count = 0
    logger.info("  → Xử lý trang tin tức...")

    # Tìm các bài viết
    articles = soup.find_all('article') or soup.find_all(class_=re.compile(r'blog|post|article'))
    if not articles:
        # Fallback: tìm theo link pattern
        articles = soup.find_all('a', href=re.compile(r'asia-vn\.edu\.vn/\w'))

    for article in articles[:20]:  # Giới hạn 20 bài
        try:
            # Lấy link bài viết
            link_tag = article.find('a') if article.name != 'a' else article
            if not link_tag or not link_tag.get('href'):
                continue

            article_url = link_tag['href']
            if not article_url.startswith('http'):
                article_url = BASE_URL + article_url

            # Bỏ qua URL không phải bài viết
            if any(skip in article_url for skip in ['#', 'mailto:', 'tel:', 'javascript:']):
                continue

            # Lấy title
            title_tag = article.find(['h1', 'h2', 'h3', 'h4', '.post-title', '.entry-title'])
            title = clean_text(title_tag.get_text()) if title_tag else clean_text(link_tag.get_text())
            if not title or len(title) < 5:
                continue

            # Lấy summary
            summary_tag = article.find(['p', '.excerpt', '.summary'])
            summary = clean_text(summary_tag.get_text()) if summary_tag else ""

            upsert_news(
                title=title,
                url=article_url,
                summary=summary,
                category='news',
            )
            count += 1

        except Exception as e:
            logger.warning(f"  Lỗi khi parse article: {e}")
            continue

    return count


def scrape_article_content(article_url: str) -> int:
    """Cào nội dung đầy đủ của một bài viết."""
    soup = fetch_page(article_url)
    if not soup:
        return 0

    title_tag = soup.find(['h1', '.entry-title', '.post-title'])
    title = clean_text(title_tag.get_text()) if title_tag else ""
    if not title:
        return 0

    content = extract_main_content(soup)

    upsert_news(
        title=title,
        url=article_url,
        content=content[:5000],  # Giới hạn 5000 ký tự
        category='article',
    )
    return 1


def scrape_general_page(soup: BeautifulSoup, url: str, category: str) -> int:
    """Cào trang chung và lưu vào university_info."""
    count = 0
    sections = extract_sections(soup)

    for section in sections:
        if section['content'] and len(section['content']) > 30:
            upsert_university_info(
                category=category,
                title=section['title'] or f'Thông tin từ {url}',
                content=section['content'],
                source_url=url
            )
            count += 1

    # Nếu không có sections, lấy toàn bộ text
    if count == 0:
        full_text = extract_main_content(soup)
        if full_text and len(full_text) > 100:
            upsert_university_info(
                category=category,
                title=f'Nội dung từ {url}',
                content=full_text[:3000],
                source_url=url
            )
            count = 1

    return count


# ═══════════════════════════════════════════════════════════════════
# MAIN SCRAPER
# ═══════════════════════════════════════════════════════════════════

def run_scraper():
    """Chạy toàn bộ scraper và cập nhật database."""
    logger.info("=" * 60)
    logger.info("🚀 BẮT ĐẦU SCRAPING DỮ LIỆU ASIA UNIVERSITY VIETNAM")
    logger.info(f"   Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # Đảm bảo tables đã được tạo
    create_tables()

    total_records = 0

    # Mapping URL → scraper function
    scrapers = {
        'home':       (SCRAPE_URLS['home'],       scrape_home,       'overview'),
        'admission':  (SCRAPE_URLS['admission'],   scrape_admission,  'admission'),
        'scholarship':(SCRAPE_URLS['scholarship'], scrape_scholarship,'scholarship'),
        'programs':   (SCRAPE_URLS['programs'],    scrape_programs,   'programs'),
    }

    # Các trang cần cào generic
    generic_pages = {
        'about':        (SCRAPE_URLS.get('about'),        'about'),
        'contact':      (SCRAPE_URLS.get('contact'),      'contact'),
        'fee':          (SCRAPE_URLS.get('fee'),          'tuition'),
        'life_taiwan':  (SCRAPE_URLS.get('life_taiwan'),  'life_taiwan'),
    }

    # Cào các trang chính
    for page_name, (url, scraper_fn, category) in scrapers.items():
        logger.info(f"\n📄 Đang cào trang: {page_name.upper()} ({url})")
        soup = fetch_page(url)
        if soup:
            try:
                count = scraper_fn(soup, url)
                total_records += count
                log_scrape(url, 'success', records_saved=count)
                logger.info(f"  ✅ Đã lưu {count} records")
            except Exception as e:
                logger.error(f"  ❌ Lỗi: {e}")
                log_scrape(url, 'failed', message=str(e))
        else:
            log_scrape(url, 'failed', message='Không thể tải trang')

    # Cào trang tin tức + sub-articles
    news_url = SCRAPE_URLS.get('news')
    if news_url:
        logger.info(f"\n📰 Đang cào trang TIN TỨC ({news_url})")
        soup = fetch_page(news_url)
        if soup:
            count = scrape_news(soup, news_url)
            total_records += count
            log_scrape(news_url, 'success', records_saved=count)
            logger.info(f"  ✅ Đã lưu {count} bài viết")

    # Cào các trang generic
    for page_name, (url, category) in generic_pages.items():
        if not url:
            continue
        logger.info(f"\n📄 Đang cào trang: {page_name.upper()} ({url})")
        soup = fetch_page(url)
        if soup:
            try:
                count = scrape_general_page(soup, url, category)
                total_records += count
                log_scrape(url, 'success', records_saved=count)
                logger.info(f"  ✅ Đã lưu {count} records")
            except Exception as e:
                logger.error(f"  ❌ Lỗi: {e}")
                log_scrape(url, 'failed', message=str(e))

    # Thống kê cuối
    logger.info("\n" + "=" * 60)
    logger.info("✅ HOÀN THÀNH SCRAPING!")
    logger.info(f"   Tổng records đã lưu lần này: {total_records}")

    stats = get_stats()
    logger.info("   Thống kê database hiện tại:")
    for table, count in stats.items():
        logger.info(f"   • {table}: {count} records")
    logger.info("=" * 60)

    return stats


if __name__ == "__main__":
    run_scraper()
