import torch
from pyannote.audio import Pipeline

def speaker_diarization(audio_path,hf_token):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", 
                                        use_auth_token=hf_token)
    pipeline.to(device)
    diarization = pipeline(audio_path)
    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append({
            "speaker": speaker,
            "start": round(turn.start, 2),
            "end": round(turn.end, 2), 
        })
    return segments

MY_TOKEN = "hf_your_huggingface_token_here"  # Replace with your actual Hugging Face token