import re
import json, os, time, requests
from typing import List, Dict

from torch import chunk

from Speaker_Diarization import speaker_diarization

OLLAMA_URL       = "http://localhost:11434/api/generate"
MODEL_NAME       = "gemma3:4b"
TARGET_LANGUAGE  = "Tiếng Việt"
CHUNK_WORD_LIMIT = 500          # số từ mỗi chunk MAP
INPUT_JSON       = "formatted_transcript.json"
OUTPUT_JSON      = "meeting_summary.json"

def load_formatted_script(json_path):
    with open(json_path,"r",encoding="utf-8") as f:
        data=json.load(f)
    return data

def split_into_chunks(segments,word_limit=CHUNK_WORD_LIMIT):
    chunks=[]
    curr_chunk=[]
    curr_wc=0
    for seg in segments:
        wc=len(seg["text_translated"].split())
        if curr_wc + wc > word_limit and curr_chunk:
            chunks.append(curr_chunk)
            curr_wc=0
            curr_chunk=[]
        curr_wc+=wc
        curr_chunk.append(seg)
        if(curr_chunk):
            chunks.append(curr_chunk)
    return chunks

def chunk_to_text(chunk: List[Dict]) -> str:
    """
    Chuyển list segment thành chuỗi dễ đọc cho LLM:
    [HH:MM:SS] SPEAKER_XX: <text>
    """
    lines = []
    for seg in chunk:
        start  = seg.get("start", "??:??")
        speaker = seg.get("speaker", "UNKNOWN")
        text    = seg.get("text_translated", seg.get("text", "")).strip()
        if text:
            # start có thể là float (giây) hoặc string (HH:MM:SS)
            if isinstance(start, float):
                m, s = int(start) // 60, int(start) % 60
                ts = f"{m:02d}:{s:02d}"
            else:
                ts = str(start)
            lines.append(f"[{ts}] {speaker}: {text}")
    return "\n".join(lines)

def call_llm(prompt,timeout):
    resp=requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream" : False,
            "options": {
                "temperature": 0.3,   # hơi sáng tạo để viết tóm tắt tự nhiên
                "num_predict": 2048,
            }
        },
        timeout=timeout
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()

def map_summarize_chunk(chunk_text: str,
                        chunk_idx: int,
                        total: int) -> str:

    prompt = f"""You are a professional meeting assistant.
Summarize the following meeting transcript excerpt in {TARGET_LANGUAGE}.
INSTRUCTIONS:
1. Write a concise summary of the main points discussed.
2. For each speaker (SPEAKER_XX), list their key points in 1-3 bullet points.
3. List any decisions or action items mentioned.
4. Write in {TARGET_LANGUAGE}. Be concise.
TRANSCRIPT EXCERPT (part {chunk_idx} of {total}):
{chunk_text}
SUMMARY IN {TARGET_LANGUAGE}:"""
    return call_llm(prompt,timeout=180)

def reduce_summaries(chunk_summaries: List[str]) -> str:

    combined = "\n\n---\n\n".join(
        [f"[PHẦN {i+1}]\n{s}" for i, s in enumerate(chunk_summaries)]
    )
    prompt = f"""You are a professional meeting minutes writer.
Below are summaries of different parts of a meeting. 
Create ONE comprehensive meeting summary in {TARGET_LANGUAGE}.
PARTIAL SUMMARIES:
{combined}
Create the final meeting summary with these EXACT sections in {TARGET_LANGUAGE}:
## I. TỔNG QUAN CUỘC HỌP
(2-4 câu tóm tắt toàn bộ cuộc họp)
## II. NỘI DUNG THEO TỪNG NGƯỜI NÓI
(Liệt kê ý chính của từng SPEAKER_XX theo định dạng bullet points)
## III. QUYẾT ĐỊNH VÀ HÀNH ĐỘNG CẦN THỰC HIỆN
(Action items – ai làm gì, deadline nếu có)
## IV. KẾT LUẬN
(1-2 câu kết luận)
FINAL SUMMARY IN {TARGET_LANGUAGE}:"""

    return call_llm(prompt, timeout=300)

def summarize_per_speaker(segments):
    speaker_text={}
    for seg in segments:
        speaker=seg.get("speaker","UNKOWN")
        text=seg.get("text_translated",seg.get("text","")).strip()
        if text:
            if speaker not in speaker_text:
                speaker_text[speaker]=[]
                speaker_text[speaker].append(text)
        summaries={}
        speakers=sorted(speaker_text.keys())
        for sp in speakers:
            all_text=" ".join(speaker_text[sp])
            word_count=len(all_text.split())
            prompt = f"""Summarize what {sp} said during the meeting in {TARGET_LANGUAGE}.
                        Their statements:
                        {all_text[:3000]}  
                    Write 3-5 bullet points summarizing their main contributions in {TARGET_LANGUAGE}:"""
            summaries[sp] = call_llm(prompt,timeout=180)
            time.sleep(0.5)   # tránh overload
    return summaries
    

def summarize_meeting(
    input_json:   str = INPUT_JSON,
    output_json:  str = OUTPUT_JSON,
    target_lang:  str = TARGET_LANGUAGE,
) -> Dict:
    segments=load_formatted_script(input_json)
    chunks=split_into_chunks(segments)
    chunks_summaries=[]
    for idx,chunk in enumerate(chunks):
        text=chunk_to_text(chunk)
        summary=map_summarize_chunk(text,idx,len(chunks))
        chunks_summaries.append(summary)
        time.sleep(1)
    overall_summary=reduce_summaries(chunks_summaries)
    speaker_summary=summarize_per_speaker(segments)
    result = {
        "overall_summary":  overall_summary,
        "per_speaker":       speaker_summary,
        "chunk_summaries":   chunks_summaries,
        "total_segments":    len(segments),
        "total_chunks":      len(chunks),
        "speakers":          sorted(set(s["speaker"] for s in segments)),
    }
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    return result
