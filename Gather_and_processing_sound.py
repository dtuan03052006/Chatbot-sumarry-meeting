
import os
from pydub import AudioSegment
import sounddevice as sd
import wavio
import torch 
import torchaudio
import numpy as np
#Transform the audio files to a specific format(WAV,16kHz,1 channel)
def standardi_audio(input_path, output_path):
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(output_path, format="wav")
    return output_path

#record_meeting
def record_meeting(output_path,device_index):
    fs=48000
    recording=[]
    print("Recording... Press Enter to stop.")
    def callback(indata, frames, time, status):
        if status:
            print(status)
        recording.append(indata.copy())

    with sd.InputStream(samplerate=fs, channels=1, device=device_index, callback=callback):
        input()
    print("Recording stopped.")
    audio_data=np.concatenate(recording, axis=0)
    wavio.write(output_path, audio_data, fs, sampwidth=2)
    return output_path


#remove_silence
def remove_silence(audio_path,output_path):
    model,utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                 model='silero_vad', 
                                 force_reload=False)
    get_speech_timestamps, save_audio, read_audio, _, _ = utils

    wav=read_audio(audio_path, sampling_rate=16000)
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
    speech_audio=torch.cat(chunks)

    save_audio(output_path, speech_audio, sampling_rate=16000)
    return output_path


def process_audio(input_source, output_final_path, is_live=False, device_id=None):

    temp_standard_wav = "temp_standard.wav"
    temp_recorded_wav = "temp_recorded.wav"
    
    if is_live:
        record_meeting(temp_recorded_wav, device_id)
        standardi_audio(temp_recorded_wav, temp_standard_wav)
        os.remove(temp_recorded_wav)
    else:
        standardi_audio(input_source, temp_standard_wav)
        
    result_path = remove_silence(temp_standard_wav, output_final_path)
    
    if os.path.exists(temp_standard_wav):
        os.remove(temp_standard_wav)
        
    return result_path     