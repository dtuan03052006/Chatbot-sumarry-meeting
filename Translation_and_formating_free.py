"""
Bước 4: Xử lý ngôn ngữ & Dịch thuật (Translation & Formatting)
----------------------------------------------------------------
Đầu vào  : final_transcriptions.json   (output từ Bước 3)
Đầu ra   : formatted_transcript.txt   +   formatted_transcript.json

🆓 PHIÊN BẢN MIỄN PHÍ – dùng Ollama (LLM chạy local, không cần API key)
   Cấu trúc code GIỮ NGUYÊN 100% so với bản gốc OpenAI.
   Chỉ thay đổi 3 dòng:
     1. OPENAI_API_KEY  →  "ollama"
     2. MODEL_NAME      →  "gemma3:4b"
     3. OpenAI(...)     →  thêm base_url="http://localhost:11434/v1"

   Cài đặt một lần:
     curl -fsSL https://ollama.com/install.sh | sh
     ollama pull gemma3:4b
     ollama serve

   Sau đó chạy:
     python3 Translation_and_formating_free.py
"""

import json, os, time
from openai import OpenAI

# -------------------------------------------------
# Cấu hình
# -------------------------------------------------
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "ollama")   # THAY ĐỔI 1/3
TARGET_LANGUAGE = "Tiếng Việt"
MODEL_NAME      = "gemma3:4b"                             # THAY ĐỔI 2/3
BATCH_WORD_LIMIT = 2000
INPUT_JSON      = "final_transcriptions.json"
OUTPUT_TXT      = "formatted_transcript.txt"
OUTPUT_JSON     = "formatted_transcript.json"


def load_transcript(json_path: str) -> list[dict]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"✅ Loaded {len(data)} segments from '{json_path}'")
    return data


def format_timestamp(seconds: float) -> str:
    return f"{int(seconds)//60:02d}:{int(seconds)%60:02d}"


def segments_to_text(segments: list[dict]) -> str:
    lines = []
    for seg in segments:
        ts = format_timestamp(seg["start"])
        speaker = seg["speaker"]
        txt = seg["text"].strip()
        if txt:
            lines.append(f"[{ts}] {speaker}: {txt}")
    return "\n".join(lines)


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


def build_translation_prompt(raw_text: str, target_language: str) -> str:
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
                    {"role": "system", "content": "Bạn là chuyên gia dịch thuật, luôn trả về đúng định dạng yêu cầu."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=4096,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if "rate_limit" in str(e).lower() and attempt < max_retries:
                wait = 2 ** attempt
                print(f"⚠️ Rate limit – retry {attempt}/{max_retries} sau {wait}s")
                time.sleep(wait)
            else:
                raise RuntimeError(f"LLM call failed: {e}")


def parse_translated_text_to_json(translated: str, original_segments: list[dict]) -> list[dict]:
    result = []
    lines = [ln.strip() for ln in translated.split("\n") if ln.strip()]
    idx = 0
    for line in lines:
        if "]" in line and ":" in line:
            try:
                after = line.split("] ", 1)[-1]
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


def translate_and_format_transcript(
    input_json: str = INPUT_JSON,
    output_txt: str = OUTPUT_TXT,
    output_json: str = OUTPUT_JSON,
    target_language: str = TARGET_LANGUAGE,
    model: str = MODEL_NAME,
    api_key: str = OPENAI_API_KEY,
) -> tuple[str, list[dict]]:
    segments = load_transcript(input_json)
    batches = split_into_batches(segments)

    # THAY ĐỔI 3/3: thêm base_url trỏ tới Ollama – tất cả code còn lại giữ nguyên
    client = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key=api_key,
    )

    txt_parts, json_parts = [], []
    for i, batch in enumerate(batches, 1):
        print(f"\n🔄 Dịch batch {i}/{len(batches)} ({len(batch)} segment)…")
        raw = segments_to_text(batch)
        translated = translate_batch_with_llm(client, raw, target_language, model)
        txt_parts.append(translated)
        json_parts.extend(parse_translated_text_to_json(translated, batch))
        if i < len(batches):
            time.sleep(1)

    full_text = "\n\n".join(txt_parts)

    with open(output_txt, "w", encoding="utf-8") as f:
        header = (
            f"{'='*60}\n"
            f"  BIÊN BẢN CUỘC HỌP (Ngôn ngữ: {target_language})\n"
            f"  Bước 4: Dịch thuật & Định dạng – by AI\n"
            f"{'='*60}\n\n"
        )
        f.write(header + full_text)
    print(f"\n💾 Đã lưu transcript dạng TXT → '{output_txt}'")

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(json_parts, f, ensure_ascii=False, indent=4)
    print(f"💾 Đã lưu transcript dạng JSON → '{output_json}'")

    return full_text, json_parts


if __name__ == "__main__":
    txt, data = translate_and_format_transcript()
    print("\n" + "="*60)
    print("📄 PREVIEW (50 dòng đầu):")
    print("="*60)
    for line in txt.split("\n")[:50]:
        print(line)
    print(f"\n✅ HOÀN THÀNH Bước 4! Tổng cộng {len(data)} segment đã dịch.")
