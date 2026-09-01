"""
Bước 6: Xuất file PDF tóm tắt cuộc họp (PDF Generation)
---------------------------------------------------------
Yêu cầu: fpdf2 (pip install fpdf2)
Hỗ trợ 100% tiếng Việt có dấu.
"""

import json
import os
import re
import urllib.request
from fpdf import FPDF

INPUT_JSON  = "meeting_summary.json"
OUTPUT_PDF  = "Meeting_Summary.pdf"

FONT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_REGULAR_PATH = os.path.join(FONT_DIR, "Roboto-Regular.ttf")
FONT_BOLD_PATH    = os.path.join(FONT_DIR, "Roboto-Bold.ttf")


def get_unicode_fonts():
    """Lấy đường dẫn font Unicode tiếng Việt"""
    # 1. Font hệ thống
    system_paths = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]
    for reg, bld in system_paths:
        if os.path.exists(reg) and os.path.exists(bld):
            return reg, bld

    # 2. Font tải về local
    if os.path.exists(FONT_REGULAR_PATH) and os.path.exists(FONT_BOLD_PATH):
        return FONT_REGULAR_PATH, FONT_BOLD_PATH

    # 3. Tải font Roboto về
    print("⏳ Đang tải font chữ tiếng Việt (Roboto)...")
    try:
        urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", FONT_REGULAR_PATH)
        urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf", FONT_BOLD_PATH)
        return FONT_REGULAR_PATH, FONT_BOLD_PATH
    except Exception as e:
        print(f"⚠️ Lỗi tải font: {e}")
        return None, None


class MeetingPDF(FPDF):
    def header(self):
        self.set_font("Roboto", "B", 10)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, "AI MEETING ASSISTANT - BIÊN BẢN TÓM TẮT CUỘC HỌP", border="B", align="L")
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Roboto", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Trang {self.page_no()}/{{nb}}", align="C")


def clean_markdown_line(line: str) -> str:
    line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
    line = re.sub(r"[\*_](.*?)[\*_]", r"\1", line)
    return line.strip()


def export_summary_to_pdf(
    input_json: str = INPUT_JSON,
    output_pdf: str = OUTPUT_PDF,
    meeting_title: str = "BIÊN BẢN CUỘC HỌP TỔNG HỢP",
) -> str:
    if not os.path.exists(input_json):
        raise FileNotFoundError(f"Không tìm thấy file '{input_json}'!")

    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    overall_summary = data.get("overall_summary", "")
    per_speaker = data.get("per_speaker", {})
    speakers = data.get("speakers", [])

    reg_font, bold_font = get_unicode_fonts()

    pdf = MeetingPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)

    # Đăng ký font Roboto
    if reg_font:
        pdf.add_font("Roboto", "", reg_font)
        pdf.add_font("Roboto", "B", bold_font if bold_font else reg_font)
    else:
        pdf.set_fallback_fonts(["Helvetica"])

    pdf.add_page()

    # 1. TIÊU ĐỀ
    pdf.set_font("Roboto", "B", 16)
    pdf.set_text_color(24, 76, 120)
    pdf.cell(0, 10, meeting_title, align="C")
    pdf.ln(10)

    # Người tham gia
    pdf.set_font("Roboto", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, f"Người tham gia: {', '.join(speakers) if speakers else 'Không xác định'}", align="C")
    pdf.ln(6)

    # Đường phân cách
    pdf.set_draw_color(24, 76, 120)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    # 2. IN TỔNG QUAN
    lines = overall_summary.replace("\\n", "\n").split("\n")

    for raw_line in lines:
        line = clean_markdown_line(raw_line)
        if not line:
            pdf.ln(2)
            continue

        if raw_line.strip().startswith("##"):
            pdf.ln(3)
            pdf.set_font("Roboto", "B", 12)
            pdf.set_text_color(24, 76, 120)
            pdf.cell(0, 7, line.replace("#", "").strip())
            pdf.ln(7)

        elif raw_line.strip().startswith(("*", "-", "•")):
            bullet_text = line.lstrip("*-• ").strip()
            pdf.set_font("Roboto", "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.set_x(20)
            pdf.multi_cell(170, 5.5, f"•  {bullet_text}")
            pdf.ln(1)

        else:
            pdf.set_font("Roboto", "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(180, 5.5, line)
            pdf.ln(1.5)

    # 3. IN THEO TỪNG SPEAKER
    if per_speaker:
        pdf.ln(4)
        pdf.set_font("Roboto", "B", 12)
        pdf.set_text_color(24, 76, 120)
        pdf.cell(0, 7, "V. CHI TIẾT Ý KIẾN TỪNG NGƯỜI NÓI")
        pdf.ln(7)

        for sp, summary_text in per_speaker.items():
            pdf.set_font("Roboto", "B", 10.5)
            pdf.set_text_color(40, 116, 166)
            pdf.cell(0, 6, f"Ý kiến của {sp}:")
            pdf.ln(6)

            sp_lines = summary_text.replace("\\n", "\n").split("\n")
            for sp_raw in sp_lines:
                sp_clean = clean_markdown_line(sp_raw)
                if not sp_clean:
                    continue
                pdf.set_font("Roboto", "", 9.5)
                pdf.set_text_color(30, 30, 30)
                pdf.set_x(20)
                pdf.multi_cell(170, 5, f"•  {sp_clean.lstrip('*-• ')}")
                pdf.ln(1)
            pdf.ln(2)

    pdf.output(output_pdf)
    print(f"\n🎉 ĐÃ XUẤT FILE PDF TIẾNG VIỆT THÀNH CÔNG: '{output_pdf}'")
    return output_pdf


if __name__ == "__main__":
    export_summary_to_pdf()
