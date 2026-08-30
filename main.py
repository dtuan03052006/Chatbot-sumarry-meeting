from Gather_and_processing_sound import process_audio
from Speaker_Diarization import speaker_diarization
from transform_speed_to_text import transcribe_audio
import os
import json
from pydub import AudioSegment


audio_path = "/home/abc/Chatbot-sumarry-meeting/check.mp3"
audio_process=process_audio(input_source=None,
                            output_final_path="output.wav", 
                            is_live=True, 
                            device_id=0)

print("Processed audio saved at:", audio_process)

# Perform speaker diarization

diarization_result = speaker_diarization(audio_process)
print("Diarization result:", diarization_result)

unique_speakers = set() 

for segment in diarization_result:

    unique_speakers.add(segment["speaker"]) 

print("Number of speakers",len(unique_speakers))
# Transcribe audio segments for each speaker
transcriptions = transcribe_audio(audio_process, diarization_result, model_size="medium")
for trans in transcriptions:
  print(trans)
with open("final_transcriptions.json", "w", encoding="utf-8") as json_file:
        json.dump(transcriptions, json_file, ensure_ascii=False, indent=4)
print("Saved successfully file json: final_transcriptions.json") 
       
