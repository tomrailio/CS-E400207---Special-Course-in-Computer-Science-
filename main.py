from hugchat import hugchat
import whisper
import speech_recognition as sr
from TTS.api import TTS
import sounddevice as sf
import requests
import json
import sounddevice as sd
import soundfile as sf
import os

url = "https://app.coqui.ai/api/v2/speakers"


url = "https://app.coqui.ai/api/v2/samples/from-prompt/"

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer DZflHJcnJrWjVaHHpAc6CkyVG3JM7mM9tcBla0pYaJmlDpEX2vQEQV8rZ9R2iEnP"
}
model_name = TTS.list_models()[8]

tts = TTS(model_name=model_name, progress_bar=False, gpu=False)


def recongize(audio):
    audio = whisper.load_audio(audio)
    audio = whisper.pad_or_trim(audio)

    # make log-Mel spectrogram and move to the same device as the model
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    # detect the spoken language
    _, probs = model.detect_language(mel)
    print(f"Detected language: {max(probs, key=probs.get)}")

    # decode the audio
    options = whisper.DecodingOptions(fp16=False)
    result = whisper.decode(model, mel, options)

    return result.text


# Press the green button in the gutter to run the script.
if __name__ == '__main__':



    #INIT
    print('Initializing')
    model = whisper.load_model("base")
    chatbot = hugchat.ChatBot(cookie_path="cookies.json")
    r = sr.Recognizer()
    mic = sr.Microphone()
    #model_name = TTS.list_models()
    #model_name = TTS.list_models()[9]
    #tts = TTS(model_name)
    #speaker_list = tts.speakers
    #anguage_list = tts.languages

    audio_file = 'output.wav'

    # Possible Setup
    available_mics = sr.Microphone.list_microphone_names()

    #with mic as source:
    #    r.adjust_for_ambient_noise(source)
    #    audio = r.listen(source)
    #   with open(audio_file, "wb") as f:
    #        f.write(audio.get_wav_data())
    conversation_list = []
    path = "conversation_summary.txt"
    if os.path.isfile(path):
        with open(path) as f:
            prior_conversation = f.readlines()

    id_conv = 0
    while 1:
        text_answer = chatbot.chat(f"This was our prior conversation: {prior_conversation}")
        text_queue = recongize(audio_file)
        print(f'This is what I heard: {text_queue}')
        text_queue = text_queue
        text_answer = chatbot.chat(text_queue)
        print(f'This is my answer: {text_answer}')
        conversation_list.append(text_queue + text_answer)

        #wav = tts.tts("This is a test! This is also a test!!")
        #sf.play(wav, 22050)
        # Text to speech to a file
        #tts.tts_to_file(text=text_answer, file_path="output_response.wav", emotion="Happy", speed=1.5)

        #payload = {
        #    "prompt": "A man with a British accent and a pleasing, deep voice.",
        #   "emotion": "Neutral",
        #   "speed": 1,
        #    "text": text_answer
        #}
        #response = requests.post(url, json=payload, headers=headers)
        #test = json.loads(response.text)
        #url = test["audio_url"]
        #file_extension = '.wav'  # Example .wav
        #r = requests.get(url)
        filename = 'output_response.wav'
        #with open(filename, 'wb') as f:
        #    # You will get the file in base64 as content
        #    f.write(r.content)
        tts.tts_to_file(text=text_answer, file_path='output_response.wav')
        data, fs = sf.read(filename, dtype='float32')
        sd.play(data, fs)
        sd.wait()
        if id_conv == 2:
            conversation = ' '.join(conversation_list)
            text_answer = chatbot.chat(f'Summarize this text: {text_queue}')

            with open("conversation_summary.txt", "w") as f:
               f.write(text_answer)
            break

        id_conv += 1

    print("Conversation Completed")
    test = 1





