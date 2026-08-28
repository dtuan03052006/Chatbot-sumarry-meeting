"""
Bước 4: Xử lý ngôn ngữ & Dịch thuật (Translation & Formatting)
----------------------------------------------------------------
Đầu vào  : final_transcriptions.json   (output từ Bước 3)
Đầu ra   : formatted_transcript.txt   +   formatted_transcript.json
"""

import json, os, time
from openai import OpenAI

# -------------------------------------------------
# Cấu hình (có thể chỉnh sửa trong quá trình chạy)
# -------------------------------------------------
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "your-api-key-here")
TARGET_LANGUAGE = "Tiếng Việt"          # Hoặc "Tiếng Anh", "Tiếng Trung", …
MODEL_NAME      = "gpt-4o-mini"        # Model rẻ, nhanh, đủ cho dịch thuật
BATCH_WORD_LIMIT = 2000                # ~2 k từ mỗi batch (đảm bảo < 4 k token)
INPUT_JSON      = "final_transcriptions.json"
OUTPUT_TXT      = "formatted_transcript.txt"
OUTPUT_JSON     = "formatted_transcript.json"


# -------------------------------------------------
# 4.1 Load transcript thô (JSON)
# -------------------------------------------------
def load_transcript(json_path: str) -> list[dict]:
    """Load list of segments:
    {speaker, start, end, text}
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"✅ Loaded {len(data)} segments from '{json_path}'")
    return data


# -------------------------------------------------
# 4.2 Định dạng lại thành chuỗi có cấu trúc
# -------------------------------------------------
def format_timestamp(seconds: float) -> str:
    """S → MM:SS (ví dụ 75.3 → '01:15')"""
    return f"{int(seconds)//60:02d}:{int(seconds)%60:02d}"


def segments_to_text(segments: list[dict]) -> str:
    """[MM:SS] SPEAKER_X: <text> (một dòng mỗi segment)"""
    lines = []
    for seg in segments:
        ts = format_timestamp(seg["start"])
        speaker = seg["speaker"]
        txt = seg["text"].strip()
        if txt:                     # bỏ segment rỗng
            lines.append(f"[{ts}] {speaker}: {txt}")
    return "\n".join(lines)


# -------------------------------------------------
# 4.3 Gom các segment thành batch (giới hạn số từ)
# -------------------------------------------------
def split_into_batches(segments: list[dict], word_limit: int = BATCH_WORD_LIMIT) -> list[list[dict]]:
    batches, cur_batch, cur_wc = [], [], 0
    for seg in segments:
        wc = len(seg["text"].split())
        if cur_wc + wc > word_limit and cur_batch:
            batches.append(cur_batch)
            cur_batch, cur_wc = [], 0
        cur_batch.append(seg)
        cur_wc += wc
    if cur_batch:
        batches.append(cur_batch)
    print(f"📦 {len(batches)} batch sẽ được gửi tới LLM")
    return batches


# -------------------------------------------------
# 4.4 Gửi batch tới LLM để dịch & làm sạch
# -------------------------------------------------
def build_translation_prompt(raw_text: str, target_language: str) -> str:
    """Prompt được thiết kế để LLM chỉ trả về văn bản đã dịch, không bổ sung / bớt."""
    return f"""Bạn là trợ lý xử lý biên bản cuộc họp chuyên nghiệp.

Dưới đây là đoạn biên bản cuộc họp thô, mỗi dòng có định dạng:
[MM:SS] SPEAKER_XX: <nội dung>

NHIỆM VỤ CỦA BẠN:
1. Dịch toàn bộ nội dung sang {target_language}.
2. Sửa các lỗi chính tả / lỗi nhận diện (tên riêng, từ lạ...).
3. GIỮ NGUYÊN định dạng mỗi dòng: [MM:SS] SPEAKER_XX: <nội dung đã dịch>.
4. KHÔNG thêm, bớt, hoặc bịa thông tin không có trong bản gốc.
5. KHÔNG gộp hay tách dòng — giữ nguyên số dòng.

BIÊN BẢN THÔ:
{raw_text}

BIÊN BẢN ĐÃ XỬ LÝ (chỉ trả về nội dung, không giải thích thêm):"""

def translate_batch_with_llm(
    client: OpenAI,
    raw_text: str,
    target_language: str,
    model: str = MODEL_NAME,
    max_retries: int = 3,
) -> str:
    prompt = build_translation_prompt(raw_text, target_language)

    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là chuyên gia dịch thuật, luôn trả về đúng định dạng yêu cầu."
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,      # giảm sáng tạo → dịch nhất quán
                max_tokens=4096,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if "rate_limit" in str(e).lower() and attempt < max_retries:
                wait = 2 ** attempt            # 2 s, 4 s, 8 s …
                print(f"⚠️ Rate limit – retry {attempt}/{max_retries} sau {wait}s")
                time.sleep(wait)
            else:
                raise RuntimeError(f"LLM call failed: {e}")


# -------------------------------------------------
# 4.5 Chuyển kết quả LLM (plain text) → JSON có cấu trúc
# -------------------------------------------------
def parse_translated_text_to_json(translated: str, original_segments: list[dict]) -> list[dict]:
    """
    Input: text đã dịch, mỗi dòng: [MM:SS] SPEAKER_XX: <dịch>
    Output: list of dicts giữ lại start/end/speaker + text_original + text_translated
    """
    result = []
    lines = [ln.strip() for ln in translated.split("\n") if ln.strip()]
    idx = 0
    for line in lines:
        if "]" in line and ":" in line:
            try:
                # tách "SPEAKER_X: nội dung"
                after = line.split("] ", 1)[-1]          # "SPEAKER_00: ..."
                _speaker, txt = after.split(": ", 1)
                txt = txt.strip()
                if idx < len(original_segments):
                    src = original_segments[idx]
                    result.append({
                        "speaker":          src["speaker"],
                        "start":            src["start"],
                        "end":              src["end"],
                        "text_original":    src["text"],
                        "text_translated":  txt,
                    })
                    idx += 1
            except (ValueError, IndexError):
                continue
    return result


# -------------------------------------------------
# 4.6 Hàm chính – thực thi toàn bộ pipeline
# -------------------------------------------------
def translate_and_format_transcript(
    input_json: str = INPUT_JSON,
    output_txt: str = OUTPUT_TXT,
    output_json: str = OUTPUT_JSON,
    target_language: str = TARGET_LANGUAGE,
    model: str = MODEL_NAME,
    api_key: str = OPENAI_API_KEY,
) -> tuple[str, list[dict]]:
    """Return (plain‑text, list‑of‑dict) và ghi ra 2 file."""
    # 1. Load
    segments = load_transcript(input_json)

    # 2. Batch
    batches = split_into_batches(segments)

    # 3. LLM client
    client = OpenAI(api_key=api_key)

    # 4. Dịch từng batch
    txt_parts, json_parts = [], []
    for i, batch in enumerate(batches, 1):
        print(f"\n🔄 Dịch batch {i}/{len(batches)} ({len(batch)} segment)…")
        raw = segments_to_text(batch)
        translated = translate_batch_with_llm(client, raw, target_language, model)
        txt_parts.append(translated)
        json_parts.extend(parse_translated_text_to_json(translated, batch))
        if i < len(batches):
            time.sleep(1)          # giảm nguy cơ rate‑limit

    # 5. Ghép lại
    full_text = "\n\n".join(txt_parts)

    # 6. Lưu TXT
    with open(output_txt, "w", encoding="utf-8") as f:
        header = (
            f"{'='*60}\n"
            f"  BIÊN BẢN CUỘC HỌP (Ngôn ngữ: {target_language})\n"
            f"  Bước 4: Dịch thuật & Định dạng – by AI\n"
            f"{'='*60}\n\n"
        )
        f.write(header + full_text)
    print(f"\n💾 Đã lưu transcript dạng TXT → '{output_txt}'")

    # 7. Lưu JSON
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(json_parts, f, ensure_ascii=False, indent=4)
    print(f"💾 Đã lưu transcript dạng JSON → '{output_json}'")

    return full_text, json_parts


# -------------------------------------------------
# Khi chạy file này trực tiếp (python Translation_and_formating.py)
# -------------------------------------------------
if __name__ == "__main__":
    txt, data = translate_and_format_transcript()
    print("\n" + "="*60)
    print("📄 PREVIEW (50 dòng đầu):")
    print("="*60)
    for line in txt.split("\n")[:50]:
        print(line)
    print(f"\n✅ HOÀN THÀNH Bước 4! Tổng cộng {len(data)} segment đã dịch.")