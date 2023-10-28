import json
import os

import pydub
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence, detect_silence


dirname=r'C:/Users/c1/Videos/eng'
mp4name='raw.mp4'
noextname=os.path.splitext(mp4name)[0]
a_name=f"{dirname}/{noextname}.wav"
os.system(f"ffmpeg -y -i {dirname}/{mp4name} -acodec pcm_s16le -f s16le -ac 1  -f wav {a_name}")


def split_by_silence(name):
    # reading from audio mp3 file
    sound = AudioSegment.from_wav(name)
    # spliting audio files
    # audio_chunks = split_on_silence(sound, min_silence_len=500, silence_thresh=-40,keep_silence=500)
    audio_chunks = detect_silence(sound, min_silence_len=500)
    print(audio_chunks)
    # loop is used to iterate over the output list
    filepath=os.path.dirname(name)
    chunkname=os.path.splitext(os.path.basename(name))[0]
    chunkpath=f'{filepath}/##'+chunkname+"_tmp"
    nonslient_file = f'{chunkpath}/detected_voice.json'
    print(chunkpath)
    if not os.path.exists(chunkpath):
        os.makedirs(chunkpath,exist_ok=True)
    soundata=[]
    # for i, chunk in enumerate(audio_chunks):
    for i, chunk in enumerate(audio_chunks):
        print(chunk)
        start,end=chunk
        soundata.append([start,end,False])
        # duration=end-start
        # end=start+duration
        # start=end

    with open(nonslient_file, 'w') as outfile:
        json.dump(soundata, outfile)

    for i,duration in enumerate(soundata):
        start_time, end_time, buffered = duration
        chunk_filename = chunkpath + f"/c{i}_{start_time // 1000}_{end_time // 1000}.wav"
        audio_chunk = sound[start_time:end_time]
        audio_chunk.export(chunk_filename, format="wav")


split_by_silence(a_name)
# sound = AudioSegment.from_wav(a_name)
# list=pydub.silence.detect_silence(sound,min_silence_len=1000)
# print(f"{len(sound)}")
# total=0
# n=0
# for it in list:
#     print(it)
#     total+=(it[1]-it[0])
#     audio_chunk = sound[it[0]:it[1]]
#     audio_chunk.export(f"./tmp/{n}.wav", format="wav")
#     n+=1
# print(f"{total=}")

# r = sr.Recognizer()
# with sr.AudioFile(a_name) as source:
#     audio_listened = r.record(source)
#     text = r.recognize_whisper(audio_listened, language="en")
#     print(text)