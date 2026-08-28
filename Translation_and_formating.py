import json, os, time
from openai import OpenAI

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "your-api-key-here")
TARGET_LANGUAGE = "Tiếng Việt"          # Hoặc "Tiếng Anh", "Tiếng Trung", …
MODEL_NAME      = "gpt-4o-mini"        # Model rẻ, nhanh, đủ cho dịch thuật
BATCH_WORD_LIMIT = 2000                # ~2 k từ mỗi batch (đảm bảo < 4 k token)
INPUT_JSON      = "final_transcriptions.json"
OUTPUT_TXT      = "formatted_transcript.txt"
OUTPUT_JSON     = "formatted_transcript.json"

def load_transcriptions(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def format_time(seconds):
    """Chuyển đổi giây sang định dạng HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{secs:02}"

def segments_to_text(segments):
    """Chuyển đổi danh sách segments thành văn bản định dạng"""
    formatted_text = ""
    for segment in segments:
        start_time = format_time(segment["start"])
        end_time = format_time(segment["end"])
        speaker=segment["speaker"]
        text = segment["text"].strip()
        if(text):
            formatted_text.append(f"[{start_time} - {end_time}] {speaker}: {text}\n")
    return "\n".join(formatted_text)

def split_into_batches(segments, word_limit):
    """Chia segments thành các batch dựa trên giới hạn từ"""
    batches = []
    current_batch = []
    current_word_count = 0
    for seg in segments:
        word_count=len(seg["text"].split())
        if(current_word_count+word_count>word_limit and current_batch):
            batches.append(current_batch)
            current_batch=[]
            current_word_count=0
        current_batch.append(seg)
        current_word_count+=word_count
    if current_batch:
        batches.append(current_batch)
    return batches

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