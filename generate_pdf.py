"""
Bước 6: Xuất file PDF tóm tắt cuộc họp (PDF Generation)
---------------------------------------------------------
Đầu vào  : meeting_summary.json
Đầu ra   : Meeting_Summary.pdf
"""

import json
import os
import re
from fpdf import FPDF

# -------------------------------------------------
# Cấu hình
# -------------------------------------------------
INPUT_JSON  = "meeting_summary.json"
OUTPUT_PDF  = "Meeting_Summary.pdf"

SYSTEM_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


class MeetingPDF(FPDF):
    """Custom PDF class có Header và Footer"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.font_registered = False

    def header(self):
        # Chỉ set_font nếu font đã được nạp
        font_name = "MeetingFont" if self.font_registered else "Helvetica"
        self.set_font(font_name, "B" if self.font_registered else "", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "AI MEETING ASSISTANT - BIEN BAN TOM TAT CUOC HOP", border="B", ln=1, align="L")
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        font_name = "MeetingFont" if self.font_registered else "Helvetica"
        self.set_font(font_name, "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Trang {self.page_no()}", align="C")


def setup_unicode_fonts(pdf: MeetingPDF) -> bool:
    """Đăng ký font Unicode tiếng Việt TRƯỚC KHI add_page"""
    regular_font = None
    bold_font = None

    for p in SYSTEM_FONT_PATHS:
        if os.path.exists(p):
            if "Bold" in p and bold_font is None:
                bold_font = p
            elif "Bold" not in p and regular_font is None:
                regular_font = p

    if regular_font:
        try:
            pdf.add_font("MeetingFont", "", regular_font, uni=True)
            if bold_font:
                pdf.add_font("MeetingFont", "B", bold_font, uni=True)
            else:
                pdf.add_font("MeetingFont", "B", regular_font, uni=True)
            pdf.font_registered = True
            return True
        except TypeError:
            # Cho fpdf2 không cần tham số uni=True
            pdf.add_font("MeetingFont", "", regular_font)
            if bold_font:
                pdf.add_font("MeetingFont", "B", bold_font)
            else:
                pdf.add_font("MeetingFont", "B", regular_font)
            pdf.font_registered = True
            return True
        except Exception as e:
            print(f"⚠️ Lỗi nạp font: {e}")
            return False
    return False


def clean_markdown_line(line: str) -> str:
    """Loại bỏ ký tự markdown thô"""
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

    pdf = MeetingPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)

    # ⚠️ CÀI ĐẶT FONT TRƯỚC KHI GỌI add_page()
    has_unicode = setup_unicode_fonts(pdf)
    font_family = "MeetingFont" if has_unicode else "Helvetica"

    # Tạo trang đầu tiên (sẽ gọi header an toàn)
    pdf.add_page()

    # 1. TIÊU ĐỀ
    pdf.set_font(font_family, "B", 16)
    pdf.set_text_color(24, 76, 120)
    pdf.cell(0, 10, meeting_title, align="C", ln=1)

    # Thông tin
    pdf.set_font(font_family, "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, f"Người tham gia: {', '.join(speakers) if speakers else 'Không xác định'}", align="C", ln=1)
    pdf.ln(4)

    # Đường kẻ phân cách
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
            pdf.set_font(font_family, "B", 12)
            pdf.set_text_color(24, 76, 120)
            pdf.cell(0, 7, line.replace("#", "").strip(), ln=1)
            pdf.ln(1)

        elif raw_line.strip().startswith(("*", "-", "•")):
            bullet_text = line.lstrip("*-• ").strip()
            pdf.set_font(font_family, "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.set_x(20)
            pdf.multi_cell(0, 5.5, f"-  {bullet_text}")
            pdf.ln(1)

        else:
            pdf.set_font(font_family, "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 5.5, line)
            pdf.ln(1.5)

    # 3. IN NỘI DUNG TỪNG SPEAKER
    if per_speaker:
        pdf.ln(4)
        pdf.set_font(font_family, "B", 12)
        pdf.set_text_color(24, 76, 120)
        pdf.cell(0, 7, "V. CHI TIẾT Ý KIẾN TỪNG NGƯỜI NÓI", ln=1)
        pdf.ln(1)

        for sp, summary_text in per_speaker.items():
            pdf.set_font(font_family, "B", 10.5)
            pdf.set_text_color(40, 116, 166)
            pdf.cell(0, 6, f"Ý kiến của {sp}:", ln=1)

            sp_lines = summary_text.replace("\\n", "\n").split("\n")
            for sp_raw in sp_lines:
                sp_clean = clean_markdown_line(sp_raw)
                if not sp_clean:
                    continue
                pdf.set_font(font_family, "", 9.5)
                pdf.set_text_color(30, 30, 30)
                pdf.set_x(20)
                pdf.multi_cell(0, 5, f"-  {sp_clean.lstrip('*-• ')}")
                pdf.ln(1)
            pdf.ln(2)

    pdf.output(output_pdf)
    print(f"\n🎉 ĐÃ XUẤT FILE PDF THÀNH CÔNG: '{output_pdf}'")
    return output_pdf


if __name__ == "__main__":
    export_summary_to_pdf()
