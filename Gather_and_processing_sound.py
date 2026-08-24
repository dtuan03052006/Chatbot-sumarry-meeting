
import os
from pydub import AudioSegment
import sounddevice as sd
import wavio
import torch 
import torchaudio

#Transform the audio files to a specific format(WAV,16kHz,1 channel)
def standardi_audio(input_path, output_path):
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(output_path, format="wav")
    return output_path

#record_meeting
def record_meeting(seconds,output_path,device_index):
    fs=16000
    recording= sd.rec(int(seconds*fs)
                      ,samplerate=fs, 
                      channels=1, 
                      device=device_index)
    sd.wait()
    wavio.write(output_path, recording, fs, sampwidth=2)
    return output_path

#remove_silence
def remove_silence(audio_path,output_path):
    model,utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                 model='silero_vad', 
                                 force_reload=False)
    get_speech_timestamps, save_audio, read_audio, _, _ = utils
    wav=read_audio(audio_path)
    speech_timestamps=get_speech_timestamps(wav,
                                            model,
                                            sampling_rate=16000)
    if len(speech_timestamps)==0:
        return None
    chunks=[]
    for ts in speech_timestamps:
        start=ts['start']
        end=ts['end']
        audio=wav[start:end]
        chunks.append(audio)
    save_audio(output_path, chunks, sampling_rate=16000)
    return output_path

def process_audio(input_source, output_final_path, is_live=False, duration=None, device_id=None):
    temp_standard_wav = "temp_standard.wav"
    
    if is_live:
        record_meeting(duration, temp_standard_wav, device_id)
    else:
        standardi_audio(input_source, temp_standard_wav)
        
    result_path = remove_silence(temp_standard_wav, output_final_path)
    
    if os.path.exists(temp_standard_wav):
        os.remove(temp_standard_wav)
        
    return result_path