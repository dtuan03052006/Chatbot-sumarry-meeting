import torch
from pyannote.audio import Pipeline
import numpy as np

def speaker_diarization(audio_path):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-community-1")
    pipeline=pipeline.to(device)
    output = pipeline(audio_path,min_speakers=2,max_speakers=10)

    diarization = output.speaker_diarization
    segments = []
    for turn, speaker in diarization.itertracks(yield_label=True):
        segments.append({
            "speaker": speaker,
            "start": round(turn.start, 2),
            "end": round(turn.end, 2), 
        })
    return segments

#thu model khac nhau,cac ngon ngu khac