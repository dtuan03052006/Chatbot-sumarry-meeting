import torch
from pyannote.audio import Pipeline

def speaker_diarization(audio_path):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
    pipeline = pipeline.to(device)
    output = pipeline(audio_path, min_speakers=1, max_speakers=8)

    segments = []

    # Dung label_timeline() - tranh itertracks(yield_label=True) bi loi tren Kaggle
    for speaker in output.labels():
        for segment, _ in output.label_timeline(speaker).itertracks():
            segments.append({
                "speaker": speaker,
                "start":   round(segment.start, 2),
                "end":     round(segment.end,   2),
            })

    # Sap xep theo thoi gian bat dau
    segments.sort(key=lambda x: x["start"])
    return segments
