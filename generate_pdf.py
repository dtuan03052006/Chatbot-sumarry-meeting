"""
Bước 6: Xuất file PDF tóm tắt cuộc họp (PDF Generation)
---------------------------------------------------------
Đầu vào  : meeting_summary.json (từ Bước 5)
Đầu ra   : Meeting_Summary.pdf

Hỗ trợ 100% tiếng Việt có dấu chuẩn đẹp qua font BeVietnamPro (Google Fonts).
"""

import json
import os
import re
import urllib.request
from fpdf import FPDF

INPUT_JSON  = "meeting_summary.json"
OUTPUT_PDF  = "Meeting_Summary.pdf"

FONT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_REGULAR = os.path.join(FONT_DIR, "BeVietnamPro-Regular.ttf")
FONT_BOLD    = os.path.join(FONT_DIR, "BeVietnamPro-Bold.ttf")

URL_REGULAR = "https://github.com/google/fonts/raw/main/ofl/bevietnampro/BeVietnamPro-Regular.ttf"
URL_BOLD    = "https://github.com/google/fonts/raw/main/ofl/bevietnampro/BeVietnamPro-Bold.ttf"


def get_font_paths() -> tuple[str, str]:
    """Tự động tải font BeVietnamPro (Google Fonts) hỗ trợ 100% tiếng Việt"""
    # 1. Kiểm tra nếu font đã có sẵn trong thư mục
    if os.path.exists(FONT_REGULAR) and os.path.exists(FONT_BOLD):
        return FONT_REGULAR, FONT_BOLD

    # 2. Kiểm tra các font hệ thống
    system_candidates = [
        ("/usr/share/fonts/TTF/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for reg, bld in system_candidates:
        if os.path.exists(reg) and os.path.exists(bld):
            return reg, bld

    # 3. Tải font BeVietnamPro từ Google Fonts CDN
    print("⏳ Đang tải font tiếng Việt BeVietnamPro từ Google Fonts...")
    try:
        urllib.request.urlretrieve(URL_REGULAR, FONT_REGULAR)
        urllib.request.urlretrieve(URL_BOLD, FONT_BOLD)
        print("✅ Tải font thành công!")
        return FONT_REGULAR, FONT_BOLD
    except Exception as e:
        print(f"⚠️ Lỗi tải font: {e}")
        return None, None


class MeetingPDF(FPDF):
    """Class tạo PDF có Header và Footer"""
    def __init__(self, font_name="VietFont", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.font_name = font_name

    def header(self):
        self.set_font(self.font_name, "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "AI MEETING ASSISTANT - BIÊN BẢN TÓM TẮT CUỘC HỌP", border="B", align="L")
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_name, "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Trang {self.page_no()}/{{nb}}", align="C")


def clean_line(text: str) -> str:
    """Lọc bỏ ký tự Markdown và các câu tiếng Anh thừa của AI"""
    skip_phrases = [
        "okay, here's a summary", "okay, here’s a summary",
        "would you like me to elaborate", "translation of the bullet points",
        "explanation of the summary", "here is a summary",
        "presented in bullet points", "broken down into"
    ]
    low = text.strip().lower()
    for phrase in skip_phrases:
        if phrase in low:
            return ""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"[\*_](.*?)[\*_]", r"\1", text)
    return text.strip()


def find_input_json(input_json: str) -> str:
    """Tìm file JSON ở các vị trí khả dĩ trên Kaggle/máy cá nhân"""
    candidates = [
        input_json,
        os.path.join(os.getcwd(), input_json),
        "/kaggle/working/meeting_summary.json",
        "/kaggle/working/Chatbot-sumarry-meeting/meeting_summary.json",
        os.path.join(FONT_DIR, input_json),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return input_json


def export_summary_to_pdf(
    input_json: str = INPUT_JSON,
    output_pdf: str = OUTPUT_PDF,
    meeting_title: str = "BIÊN BẢN CUỘC HỌP TỔNG HỢP",
) -> str:
    resolved_json = find_input_json(input_json)
    if not os.path.exists(resolved_json):
        raise FileNotFoundError(f"Không tìm thấy file '{input_json}'!")

    with open(resolved_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    overall_summary = data.get("overall_summary", "")
    per_speaker = data.get("per_speaker", {})
    speakers = data.get("speakers", [])

    # Chuẩn bị font tiếng Việt
    reg_font, bold_font = get_font_paths()
    font_name = "VietFont"

    pdf = MeetingPDF(font_name=font_name, orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)

    # Đăng ký font UTF-8
    if reg_font:
        pdf.add_font(font_name, "", reg_font)
        pdf.add_font(font_name, "B", bold_font if bold_font else reg_font)
    else:
        pdf.set_fallback_fonts(["Helvetica"])

    pdf.add_page()

    # 1. TIÊU ĐỀ
    pdf.set_font(font_name, "B", 16)
    pdf.set_text_color(24, 76, 120)
    pdf.cell(0, 10, meeting_title, align="C")
    pdf.ln(10)

    # Người tham gia
    pdf.set_font(font_name, "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, f"Người tham gia: {', '.join(speakers) if speakers else 'Không xác định'}", align="C")
    pdf.ln(6)

    # Đường phân cách
    pdf.set_draw_color(24, 76, 120)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    # 2. IN NỘI DUNG TỔNG QUAN
    lines = overall_summary.replace("\\n", "\n").split("\n")
    for raw_line in lines:
        line = clean_line(raw_line)
        if not line:
            continue

        if raw_line.strip().startswith("##"):
            pdf.ln(3)
            pdf.set_font(font_name, "B", 12)
            pdf.set_text_color(24, 76, 120)
            pdf.cell(0, 7, line.replace("#", "").strip())
            pdf.ln(7)

        elif raw_line.strip().startswith(("*", "-", "•")):
            bullet_text = line.lstrip("*-• ").strip()
            pdf.set_font(font_name, "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.set_x(20)
            pdf.multi_cell(0, 5.5, f"•  {bullet_text}")
            pdf.ln(1)

        else:
            pdf.set_font(font_name, "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 5.5, line)
            pdf.ln(2)

    # 3. IN NỘI DUNG TỪNG SPEAKER
    if per_speaker:
        pdf.ln(4)
        pdf.set_font(font_name, "B", 12)
        pdf.set_text_color(24, 76, 120)
        pdf.cell(0, 7, "V. CHI TIẾT Ý KIẾN TỪNG NGƯỜI NÓI")
        pdf.ln(7)

        for sp, summary_text in per_speaker.items():
            pdf.set_font(font_name, "B", 10.5)
            pdf.set_text_color(40, 116, 166)
            pdf.cell(0, 6, f"Ý kiến của {sp}:")
            pdf.ln(6)

            sp_lines = summary_text.replace("\\n", "\n").split("\n")
            for sp_raw in sp_lines:
                sp_clean = clean_line(sp_raw)
                if not sp_clean:
                    continue
                pdf.set_font(font_name, "", 9.5)
                pdf.set_text_color(30, 30, 30)
                pdf.set_x(20)
                pdf.multi_cell(0, 5, f"•  {sp_clean.lstrip('*-• ')}")
                pdf.ln(1)
            pdf.ln(2)

    pdf.output(output_pdf)
    print(f"\n🎉 ĐÃ XUẤT FILE PDF TIẾNG VIỆT THÀNH CÔNG: '{output_pdf}'")
    return output_pdf


if __name__ == "__main__":
    export_summary_to_pdf()
