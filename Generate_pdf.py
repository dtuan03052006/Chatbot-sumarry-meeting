

import json
import os
import re
from fpdf import FPDF

# -------------------------------------------------
# Cấu hình
# -------------------------------------------------
INPUT_JSON  = "meeting_summary.json"
OUTPUT_PDF  = "Meeting_Summary.pdf"

# Các đường dẫn font Unicode có sẵn trên hệ thống Linux / Kaggle / Ubuntu
SYSTEM_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]

class MeetingPDF(FPDF):
    """Custom PDF class có Header và Footer chuyên nghiệp"""

    def header(self):
        # Header ở đầu mỗi trang
        self.set_font("MeetingFont", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "AI MEETING ASSISTANT - BIÊN BẢN TÓM TẮT CUỘC HỌP", border="B", align="L")
        self.ln(12)

    def footer(self):
        # Footer ở cuối mỗi trang
        self.set_y(-15)
        self.set_font("MeetingFont", "", 8)
        self.set_text_color(150, 150, 150)
        page_text = f"Trang {self.page_no()}/{{nb}}"
        self.cell(0, 10, page_text, align="C")


def setup_unicode_fonts(pdf: FPDF) -> bool:
    """Đăng ký font Unicode tiếng Việt vào FPDF"""
    regular_font = None
    bold_font = None

    # Tìm font DejaVuSans hoặc LiberationSans trên hệ thống
    for p in SYSTEM_FONT_PATHS:
        if os.path.exists(p):
            if "Bold" in p and bold_font is None:
                bold_font = p
            elif "Bold" not in p and regular_font is None:
                regular_font = p

    # Nếu tìm thấy font hệ thống, nạp vào FPDF
    if regular_font:
        pdf.add_font("MeetingFont", "", regular_font)
        if bold_font:
            pdf.add_font("MeetingFont", "B", bold_font)
        else:
            pdf.add_font("MeetingFont", "B", regular_font)
        return True
    else:
        print(" Không tìm thấy font TTF hệ thống. Sử dụng font Helvetica mặc định.")
        pdf.set_fallback_fonts(["Helvetica"])
        return False


def clean_markdown_line(line: str) -> str:
    """Loại bỏ ký tự markdown thô (*, #) để in ra PDF sạch đẹp"""
    # Xoá dấu ** (in đậm markdown)
    line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
    # Xoá dấu * hoặc _ (in nghiêng)
    line = re.sub(r"[\*_](.*?)[\*_]", r"\1", line)
    return line.strip()


def export_summary_to_pdf(
    input_json: str = INPUT_JSON,
    output_pdf: str = OUTPUT_PDF,
    meeting_title: str = "BIÊN BẢN CUỘC HỌP TỔNG HỢP",
) -> str:
    """
    Đọc dữ liệu tóm tắt từ JSON và xuất thành file PDF chuẩn
    """
    if not os.path.exists(input_json):
        raise FileNotFoundError(f"Không tìm thấy file '{input_json}' từ Bước 5!")

    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    overall_summary = data.get("overall_summary", "")
    per_speaker = data.get("per_speaker", {})
    speakers = data.get("speakers", [])

    # Khởi tạo trang PDF (Khổ A4)
    pdf = MeetingPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Cài đặt font Unicode
    has_unicode = setup_unicode_fonts(pdf)
    font_family = "MeetingFont" if has_unicode else "Helvetica"

    # 1. TIÊU ĐỀ CHÍNH
    pdf.set_font(font_family, "B", 18)
    pdf.set_text_color(24, 76, 120)  # Xanh dương đậm
    pdf.cell(0, 12, meeting_title, align="C", ln=True)

    # Thông tin cuộc họp
    pdf.set_font(font_family, "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, f"Người tham gia: {', '.join(speakers) if speakers else 'Không xác định'}", align="C", ln=True)
    pdf.ln(6)

    # Đường phân cách
    pdf.set_draw_color(24, 76, 120)
    pdf.set_line_width(0.6)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(8)

    # 2. XỬ LÝ VÀ IN NỘI DUNG TỔNG QUAN (overall_summary)
    lines = overall_summary.replace("\\n", "\n").split("\n")

    for raw_line in lines:
        line = clean_markdown_line(raw_line)
        if not line:
            pdf.ln(3)
            continue

        # Header cấp 2 (## TIÊU ĐỀ MỤC)
        if raw_line.strip().startswith("##"):
            pdf.ln(4)
            pdf.set_font(font_family, "B", 13)
            pdf.set_text_color(24, 76, 120)  # Màu xanh tiêu đề mục
            pdf.cell(0, 8, line.replace("#", "").strip(), ln=True)
            pdf.ln(2)

        # Bullet point (* hoặc -)
        elif raw_line.strip().startswith(("*", "-", "•")):
            bullet_text = line.lstrip("*-• ").strip()
            pdf.set_font(font_family, "", 10.5)
            pdf.set_text_color(30, 30, 30)
            
            # Thụt lề cho gạch đầu dòng
            pdf.set_x(20)
            pdf.multi_cell(0, 6, f"•  {bullet_text}")
            pdf.ln(1)

        # Đoạn văn thông thường
        else:
            pdf.set_font(font_family, "", 10.5)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 6, line)
            pdf.ln(2)

    # 3. MỤC TÓM TẮT THEO TỪNG SPEAKER
    if per_speaker:
        pdf.ln(6)
        pdf.set_font(font_family, "B", 13)
        pdf.set_text_color(24, 76, 120)
        pdf.cell(0, 8, "V. CHI TIẾT Ý KIẾN TỪNG NGƯỜI NÓI", ln=True)
        pdf.ln(2)

        for sp, summary_text in per_speaker.items():
            pdf.set_font(font_family, "B", 11)
            pdf.set_text_color(40, 116, 166)
            pdf.cell(0, 7, f"Ý kiến của {sp}:", ln=True)

            sp_lines = summary_text.replace("\\n", "\n").split("\n")
            for sp_raw in sp_lines:
                sp_clean = clean_markdown_line(sp_raw)
                if not sp_clean:
                    continue
                pdf.set_font(font_family, "", 10)
                pdf.set_text_color(30, 30, 30)
                pdf.set_x(20)
                pdf.multi_cell(0, 5.5, f"•  {sp_clean.lstrip('*-• ')}")
                pdf.ln(1)
            pdf.ln(3)

    # Xuất file PDF
    pdf.output(output_pdf)
    print(f"\n Saved file pdf successfully: '{output_pdf}'")
    return output_pdf


if __name__ == "__main__":
    export_summary_to_pdf()
