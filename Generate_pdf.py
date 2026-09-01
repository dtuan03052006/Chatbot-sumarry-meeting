"""
Bước 6: Xuất file PDF tóm tắt cuộc họp (PDF Generation)
---------------------------------------------------------
Đầu vào  : meeting_summary.json
Đầu ra   : Meeting_Summary.pdf

Hỗ trợ 100% Tiếng Việt có dấu (Unicode) không bao giờ bị lỗi font.
"""

import json
import os
import re
import urllib.request
from fpdf import FPDF

# -------------------------------------------------
# Cấu hình
# -------------------------------------------------
INPUT_JSON  = "meeting_summary.json"
OUTPUT_PDF  = "Meeting_Summary.pdf"

FONT_REGULAR_URL = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
FONT_BOLD_URL    = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"

FONT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_REGULAR_PATH = os.path.join(FONT_DIR, "Roboto-Regular.ttf")
FONT_BOLD_PATH    = os.path.join(FONT_DIR, "Roboto-Bold.ttf")


def ensure_unicode_font_exists():
    """Tự động tải font Roboto hỗ trợ tiếng Việt nếu chưa có trên máy"""
    # 1. Kiểm tra các font hệ thống có sẵn trên Linux
    system_paths = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]
    for reg, bld in system_paths:
        if os.path.exists(reg) and os.path.exists(bld):
            return reg, bld

    # 2. Nếu đã tải file về thư mục hiện tại
    if os.path.exists(FONT_REGULAR_PATH) and os.path.exists(FONT_BOLD_PATH):
        return FONT_REGULAR_PATH, FONT_BOLD_PATH

    # 3. Tải tự động từ internet
    print("Đang tải font chữ tiếng Việt (Roboto)...")
    try:
        urllib.request.urlretrieve(FONT_REGULAR_URL, FONT_REGULAR_PATH)
        urllib.request.urlretrieve(FONT_BOLD_URL, FONT_BOLD_PATH)
        print("Tải font thành công!")
        return FONT_REGULAR_PATH, FONT_BOLD_PATH
    except Exception as e:
        print(f"Không thể tải font: {e}")
        return None, None


class MeetingPDF(FPDF):
    """Custom PDF class có Header và Footer"""
    def __init__(self, font_name="VietFont", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.font_name = font_name

    def header(self):
        self.set_font(self.font_name, "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "AI MEETING ASSISTANT - BIÊN BẢN TÓM TẮT CUỘC HỌP", border="B", ln=1, align="L")
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_name, "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Trang {self.page_no()}", align="C")


def clean_markdown_line(line: str) -> str:
    """Loại bỏ ký tự markdown thô (*, #)"""
    line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
    line = re.sub(r"[\*_](.*?)[\*_]", r"\1", line)
    return line.strip()


def export_summary_to_pdf(
    input_json: str = INPUT_JSON,
    output_pdf: str = OUTPUT_PDF,
    meeting_title: str = "BIÊN BẢN CUỘC HỌP TỔNG HỢP",
) -> str:
    if not os.path.exists(input_json):
        raise FileNotFoundError(f"Không tìm thấy file '{input_json}' từ Bước 5!")

    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    overall_summary = data.get("overall_summary", "")
    per_speaker = data.get("per_speaker", {})
    speakers = data.get("speakers", [])

    # Chuẩn bị font tiếng Việt
    reg_font, bold_font = ensure_unicode_font_exists()
    font_name = "VietFont" if reg_font else "Helvetica"

    pdf = MeetingPDF(font_name=font_name, orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)

    # Đăng ký font UTF-8
    if reg_font:
        pdf.add_font("VietFont", "", reg_font)
        pdf.add_font("VietFont", "B", bold_font if bold_font else reg_font)

    # Tạo trang đầu
    pdf.add_page()

    # 1. TIÊU ĐỀ
    pdf.set_font(font_name, "B", 16)
    pdf.set_text_color(24, 76, 120)
    pdf.cell(0, 10, meeting_title, align="C", ln=1)

    # Người tham gia
    pdf.set_font(font_name, "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, f"Người tham gia: {', '.join(speakers) if speakers else 'Không xác định'}", align="C", ln=1)
    pdf.ln(4)

    # Đường phân cách
    pdf.set_draw_color(24, 76, 120)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    # 2. IN NỘI DUNG TỔNG QUAN
    lines = overall_summary.replace("\\n", "\n").split("\n")

    for raw_line in lines:
        line = clean_markdown_line(raw_line)
        if not line:
            pdf.ln(2)
            continue

        if raw_line.strip().startswith("##"):
            pdf.ln(3)
            pdf.set_font(font_name, "B", 12)
            pdf.set_text_color(24, 76, 120)
            pdf.cell(0, 7, line.replace("#", "").strip(), ln=1)
            pdf.ln(1)

        elif raw_line.strip().startswith(("*", "-", "•")):
            bullet_text = line.lstrip("*-• ").strip()
            pdf.set_font(font_name, "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.set_x(20)
            pdf.multi_cell(0, 5.5, f"-  {bullet_text}")
            pdf.ln(1)

        else:
            pdf.set_font(font_name, "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 5.5, line)
            pdf.ln(1.5)

    # 3. IN NỘI DUNG TỪNG SPEAKER
    if per_speaker:
        pdf.ln(4)
        pdf.set_font(font_name, "B", 12)
        pdf.set_text_color(24, 76, 120)
        pdf.cell(0, 7, "V. CHI TIẾT Ý KIẾN TỪNG NGƯỜI NÓI", ln=1)
        pdf.ln(1)

        for sp, summary_text in per_speaker.items():
            pdf.set_font(font_name, "B", 10.5)
            pdf.set_text_color(40, 116, 166)
            pdf.cell(0, 6, f"Ý kiến của {sp}:", ln=1)

            sp_lines = summary_text.replace("\\n", "\n").split("\n")
            for sp_raw in sp_lines:
                sp_clean = clean_markdown_line(sp_raw)
                if not sp_clean:
                    continue
                pdf.set_font(font_name, "", 9.5)
                pdf.set_text_color(30, 30, 30)
                pdf.set_x(20)
                pdf.multi_cell(0, 5, f"-  {sp_clean.lstrip('*-• ')}")
                pdf.ln(1)
            pdf.ln(2)

    pdf.output(output_pdf)
    print(f"\n ĐÃ XUẤT FILE PDF TIẾNG VIỆT THÀNH CÔNG: '{output_pdf}'")
    return output_pdf



