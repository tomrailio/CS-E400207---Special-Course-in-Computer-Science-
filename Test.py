#! python3.7


import io
import os
import speech_recognition as sr
import whisper
import torch
import numpy as np
from datetime import datetime, timedelta
from queue import Queue
from tempfile import NamedTemporaryFile
from time import sleep
import soundfile as sf

def main():
    names = []
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        names.append([index, name])

    energy_threshold = 500
    record_timeout = 2
    phrase_timeout = 3

    # The last time a recording was retreived from the queue.
    phrase_time = None
    # Current raw audio bytes.
    last_sample = bytes()
    # Thread safe Queue for passing data from the threaded recording callback.
    data_queue = Queue()
    # We use SpeechRecognizer to record our audio because it has a nice feauture where it can detect when speech ends.
    recorder = sr.Recognizer()
    recorder.energy_threshold = energy_threshold
    # Definitely do this, dynamic energy compensation lowers the energy threshold dramtically to a point where the SpeechRecognizer never stops recording.
    recorder.dynamic_energy_threshold = False

    source = sr.Microphone(sample_rate=16000, device_index=2)

    # Load / Download model
    model = whisper.load_model("base")

    transcription = ['']

    #with source:
    #    recorder.adjust_for_ambient_noise(source)

    def record_callback(_, audio: sr.AudioData) -> None:
        """
        Threaded callback function to receive audio data when recordings finish.
        audio: An AudioData containing the recorded bytes.
        """
        # Grab the raw bytes and push it into the thread safe queue.
        data = audio.get_raw_data()
        data_queue.put(data)

    # Create a background thread that will pass us raw audio bytes.
    # We could do this manually but SpeechRecognizer provides a nice helper.
    recorder.listen_in_background(source, record_callback, phrase_time_limit=record_timeout)

    while True:
        try:
            now = datetime.utcnow()
            # Pull raw recorded audio from the queue.
            if not data_queue.empty():
                phrase_complete = False
                # If enough time has passed between recordings, consider the phrase complete.
                # Clear the current working audio buffer to start over with the new data.
                if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
                    last_sample = bytes()
                    phrase_complete = True
                # This is the last time we received new audio data from the queue.
                phrase_time = now

                # Concatenate our current audio data with the latest audio data.
                while not data_queue.empty():
                    data = data_queue.get()
                    last_sample += data

                # Use AudioData to convert the raw data to wav data.
                audio_data = sr.AudioData(last_sample, source.SAMPLE_RATE, source.SAMPLE_WIDTH)
                audio_data, samplerate = sf.read(io.BytesIO(audio_data.get_wav_data()))
                audio = whisper.pad_or_trim(audio_data.astype(np.float32))

                #make log-Mel spectrogram and move to the same device as the model
                mel = whisper.log_mel_spectrogram(audio).to(model.device)

                #decode the audio
                options = whisper.DecodingOptions(fp16=torch.cuda.is_available(), language="en")
                result = whisper.decode(model, mel, options)
                text = result.text

                # If we detected a pause between recordings, add a new item to our transcripion.
                if phrase_complete:
                    transcription.append(text)
                else:
                    transcription[-1] = text

                # Clear the console to reprint the updated transcription.
                os.system('cls' if os.name == 'nt' else 'clear')
                for line in transcription:
                    print(line)
                # Flush stdout.
                print('', end='', flush=True)

                # Infinite loops are bad for processors, must sleep.
                sleep(0.25)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()