from hugchat import hugchat
from hugchat.login import Login
import whisper
import speech_recognition as sr
from TTS.api import TTS
import sounddevice as sd
import soundfile as sf
import os
import tkinter
import customtkinter
from PIL import Image
import pandas as pd
import threading
import time
import torch
from datetime import datetime, timedelta
from queue import Queue
import io
from time import sleep
import numpy as np
import random


questions = pd.read_csv('QuestionSurvey_2.csv')
starting_question = questions.loc[0]['Question']
number_questions = len(questions.index)

email = "silas.rech@aalto.fi"
sign = Login(email, "Pandomac:;14")
cookies = sign.login()
sign.saveCookies()
chatbot = hugchat.ChatBot(cookies=cookies.get_dict())

# Save cookies to usercookies/<email>.json
sign.saveCookies()

test = chatbot.chat("HI")
model_name = TTS.list_models()[8]

# tts = TTS(model_name=model_name, progress_bar=False, gpu=True)
tts = TTS(model_name="tts_models/multilingual/multi-dataset/your_tts", progress_bar=False, gpu=True)

customtkinter.set_appearance_mode("dark")  # Modes: system (default), light, dark
customtkinter.set_default_color_theme("dark-blue")  # Themes: blue (default), dark-blue, green

print('Initializing')

# Needed paths and folders
recording_folder = 'OutputRecordings'
trust_scores_folder = 'OutputTrustScores'
recording_in_folder = 'InputRecordings'
final_answer_folder = 'FinalAnswers'

path = "conversation_summary.txt"
audio_file = 'output.wav'

folders = [recording_folder, trust_scores_folder, recording_folder, final_answer_folder]

for folder in folders:
    if not os.path.exists(folder):
       os.makedirs(folder)

# Possible Mic - Run when you run the programm the first time to select the right microphone
available_mics = sr.Microphone.list_microphone_names()
# print(available_mics)
# 2 for home computer, 1 for uni computer
mic_index = 2

# If debugging and logging needed
debug = False

# Initialize Text-to-Speech
model = whisper.load_model("base")


# Init Speech Rec
# Initialize Speech Recognizer
r = sr.Recognizer()
mic = sr.Microphone(device_index=mic_index, sample_rate=16000)

energy_threshold = 500
record_timeout = 2
phrase_timeout = 3

# Current raw audio bytes.
last_sample = bytes()
# Thread safe Queue for passing data from the threaded recording callback.
data_queue = Queue()
text_queue = Queue()
interjection_queue = Queue()

# We use SpeechRecognizer to record our audio because it has a nice feauture where it can detect when speech ends.
recorder = sr.Recognizer()
recorder.energy_threshold = energy_threshold

# Definitely do this, dynamic energy compensation lowers the energy threshold dramtically to a point where the
# SpeechRecognizer never stops recording.
recorder.dynamic_energy_threshold = False


def record_callback(_, audio: sr.AudioData) -> None:
    """
    Threaded callback function to receive audio data when recordings finish.
    audio: An AudioData containing the recorded bytes.
    """
    # Grab the raw bytes and push it into the thread safe queue.
    data = audio.get_raw_data()
    data_queue.put(data)


with mic as source:
    r.adjust_for_ambient_noise(source)


class App(customtkinter.CTk):

    frames = {"Study_Frame": None, "Talking_Frame": None}

    def study_Frame_selector(self):
        self.title("Voice Assistant Example")
        self.geometry(f"{1300}x{1000}")
        self.create_talking_frame()
        #App.frames['Talking_Frame'].pack_forget()
        App.frames["Study_Frame"].pack(in_=self.main_container, side=tkinter.TOP, fill=tkinter.BOTH, expand=True,
                                  padx=0, pady=0)

    def talking_Frame_selector(self):
        self.title("Voice Assistant Example")
        self.geometry(f"{1300}x{1000}")
        self.create_study_frame()
        #App.frames["Study_Frame"].pack_forget()
        App.frames['Talking_Frame'].pack(in_=self.main_container, side=tkinter.TOP, fill=tkinter.BOTH, expand=True,
                                  padx=0, pady=0)

    def stop_event(self):
        self.stop = 1

        self.progressbar_talking.stop()
        self.talk_button.configure(text="Talk to the Virtual Assistant")
        self.stop_listening(wait_for_stop=False)
        print('Stopping...')
        sd.stop()
        text_queue.queue.clear()

        sleep(0.2)
        self.talk_button.configure(state="normal")

    def prior_conversations_event(self,):
        id_conv = 2
        text_queue = 2
        text_answer = chatbot.chat(f"This was our prior conversation: {prior_conversation}")

        #conversation_list.append(text_queue + text_answer)
        #if id_conv == 2:
        #    conversation = ' '.join(conversation_list)
        #   text_answer = chatbot.chat(f'Summarize this text: {text_queue}')#
        #    with open("conversation_summary.txt", "w") as f:
        #        f.write(text_answer)

    def submit_event(self):
        self.progress_questions += 1
        self.logo_label.configure(text=questions.loc[self.progress_questions]['Question'])
        self.progressbar_1.set(self.progress_questions / number_questions)

        if not debug:
            with open(os.path.join(final_answer_folder, f"final_answer_{self.subject_id}.txt"), "w") as f:
                for lines in self.conversation_tracker:
                    f.write(lines)

            with open(os.path.join(trust_scores_folder, f"TrustScores_{self.subject_id}.txt"), "w") as f:
                f.write(f"{questions.loc[self.progress_questions]['Question'], self.radio_var.get()}")

        id = chatbot.new_conversation()
        chatbot.change_conversation(id)
        self.conversation_tracker = []
        self.talking_counter = 0
        self.entry.configure(placeholder_text="Type your answer here")
        self.entry.configure(textvariable="Type your answer here")

    def back_event(self):
        self.progress_questions -= 1
        if self.progress_questions >= 0:
            self.logo_label.configure(text=questions.loc[self.progress_questions]['Question'])
            self.progressbar_1.set(self.progress_questions / number_questions)

    def interjections_event(self):
        data, fs = sf.read('Mhmm.wav', dtype='float32')
        sd.play(data, fs)

    def display_text(self):
        # self.textbox_SR.delete("0.0", "end")
        while not self.transcription_completed:
            text = text_queue.get()
            display_t = ' '.join(text)
            print(f"Text: {display_t}")
            self.textbox_SR.insert("end", text=display_t)
            sleep(0.1)

        self.textbox_SR.insert("end", text='\n')

    def display_response(self):
        self.textbox.delete("0.0", "end")
        display_t = self.text_answer
        self.textbox.insert("end", text="Voice Assistant: ")
        print(display_t)
        for character in display_t:
            self.textbox.insert("end", text=character)
            time.sleep(0.03)

    def play_audio(self):
        fs = 16000
        tts.tts_to_file(self.text_answer, speaker_wav="SilasVoice.wav", language="en", file_path="output.wav")
        # data = tts.tts(text=self.text_answer)
        data, fs = sf.read("output.wav")
        sd.play(data, fs)

    # Interjection mmmmm...     for Ehhhm

    def recognition_and_answering(self):
        # self.textbox_SR.configure(state="normal")

        if self.mode != "Study":

            self.textbox_SR.configure(state="normal")
            self.textbox_SR = customtkinter.CTkTextbox(self.conversation, wrap="word", height=60, width=600)
            #self.textbox_SR.configure(state="normal")
            self.textbox_SR.grid(row=(2 + 2 * self.conversation_number), column=0, padx=(20, 20), pady=(10, 10), sticky="e")
            self.textbox_SR.insert("0.0", "You: ")

        self.recognize()

        self.transcription_completed = True
        # self.conversation_number += 1

        if self.transcription == '':
            self.text_answer = 'It seems like you did not say anything yet, if you are ready to talk press the talk - button again.'
        else:
            self.text_answer = chatbot.chat(self.transcription)

        if self.mode != "Study":
            self.textbox = customtkinter.CTkTextbox(self.conversation, wrap="word", height=60, width=600)
            self.textbox.configure(state="normal")
            self.textbox.grid(row=(3 + 2 * self.conversation_number), column=0, padx=(20, 20), pady=(10, 10), sticky="w")
            self.textbox.insert("0.0", "Voice Assistant: ...")
            self.conversation_number += 1

        responding_thread = threading.Thread(target=self.display_response)
        responding_thread.start()
        print(f'This is my answer: {self.transcription}')

        self.filename = os.path.join(recording_folder, f"output_response_{self.subject_id}_{self.talking_counter}.wav")

        playing_thread = threading.Thread(target=self.play_audio)
        playing_thread.start()

        self.conversation_tracker.append(self.text_queue)
        self.conversation_tracker.append(self.text_answer)

        self.progressbar_talking.stop()
        self.talk_button.configure(text="Talk to the Virtual Assistant")
        self.talk_button.configure(state="normal")
        self.talking_counter += 1
        self.transcription = []

    def recording_event(self):

        self.talk_button.configure(state="disabled")
        self.talk_button.configure(text="Listening...")
        self.transcription_completed = False

        if self.mode == "Study":
            self.progressbar_talking.grid(row=0, column=1, columnspan=1, padx=(20, 10), pady=(10, 10), sticky="ew")

        else:
            self.progressbar_talking.grid(row=0, column=0, padx=(20, 10), pady=(10, 10), sticky="ew")

        self.progressbar_talking.start()

        threading.Thread(target=self.display_text).start()
        self.recognition_process = threading.Thread(target=self.recognition_and_answering)
        self.recognition_process.start()

    def recognize(self):
        test_mode = False
        if not self.stop_listening:
            self.stop_listening = recorder.listen_in_background(mic, record_callback, phrase_time_limit=record_timeout)

        if test_mode:
            audio_data = whisper.load_audio(os.path.join("Output Recordings", "output0.wav"))
            audio = whisper.pad_or_trim(audio_data.astype(np.float32))
            # make log-Mel spectrogram and move to the same device as the model
            mel = whisper.log_mel_spectrogram(audio).to(model.device)
            # decode the audio
            options = whisper.DecodingOptions(fp16=torch.cuda.is_available(), language="en")
            result = whisper.decode(model, mel, options)
            words = result.text.split()

            #if result.text[-1] == '.':
            #   if random.random() > 0.1:
            #       threading.Thread(target=self.interjections_event).start()
            # if
            # interjection_queue.put()

            # self.transcription = corrected_text

            # If we detected a pause between recordings, add a new item to our transcription.
            text_queue.put(words)
            self.transcription = result.text
        else:
            print('Starting Transcription')
            recognition_complete = False

            start_timer = datetime.utcnow()
            test = []
            while not recognition_complete:
                now = datetime.utcnow()
                # Pull raw recorded audio from the queue.
                if not data_queue.empty():
                    start_timer = now
                    phrase_complete = False
                    # If enough time has passed between recordings, consider the phrase complete.
                    # Clear the current working audio buffer to start over with the new data.
                    if self.phrase_time and now - self.phrase_time > timedelta(seconds=phrase_timeout):
                        self.last_sample = bytes()
                        phrase_complete = True
                    # This is the last time we received new audio data from the queue.
                    self.phrase_time = now

                    # Concatenate our current audio data with the latest audio data.
                    while not data_queue.empty():
                        data = data_queue.get()
                        self.last_sample += data

                    # Use AudioData to convert the raw data to wav data.
                    audio_data = sr.AudioData(self.last_sample, source.SAMPLE_RATE, source.SAMPLE_WIDTH)
                    audio_data, samplerate = sf.read(io.BytesIO(audio_data.get_wav_data()))

                    #audio_data = whisper.load_audio('output0.wav')
                    audio = whisper.pad_or_trim(audio_data.astype(np.float32))
                    # make log-Mel spectrogram and move to the same device as the model
                    mel = whisper.log_mel_spectrogram(audio).to(model.device)
                    # decode the audio
                    options = whisper.DecodingOptions(fp16=torch.cuda.is_available(), language="en")
                    result = whisper.decode(model, mel, options)
                    test.append(result.text)
                    words = result.text.split()

                    if result.text[-1] == '.':
                        if random.random() > 1:
                            threading.Thread(target=self.interjections_event).start()

                    #if
                    #interjection_queue.put()

                    #self.transcription = corrected_text

                    # If we detected a pause between recordings, add a new item to our transcription.
                    text_queue.put(words)
                    self.transcription = result.text
                if now - start_timer > timedelta(seconds=4):
                    recognition_complete = True

    def test_function(self):
        test_button = 1
        self.textbox = customtkinter.CTkTextbox(self.conversation, wrap="word", height=50, width=350)
        self.textbox.insert("0.0", "Voice Assistant: ...")
        self.textbox.grid(row=2 * self.conversation_number, column=0, padx=(20, 20), pady=(10, 10), sticky="e")
        self.conversation_number += 1

    def create_talking_frame(self):

        self.conversation_number = 0
        self.mode = "Talking"
        App.frames["Study_Frame"] = customtkinter.CTkFrame(self, corner_radius=0, width=1300, height=1000)
        frame = App.frames['Study_Frame']

        # Voice Assistant Answer
        self.conversation = customtkinter.CTkFrame(frame, width=1300, height=1000)
        self.conversation.grid(row=5, column=0, sticky="nsew")
        self.conversation.grid_rowconfigure(5, weight=1)
        self.conversation.grid_columnconfigure(0, weight=1)

        # Answer Speech Text Box
        # self.textbox = customtkinter.CTkTextbox(conversation, wrap="word", height=50, width=350)
        # Recognized Speech Text Box
        self.textbox_SR = customtkinter.CTkTextbox(self.conversation, wrap="word", height=60, width=600)
        # self.textbox.insert("0.0", "Voice Assistant: ...")
        self.textbox_SR.insert("0.0", "You: ...")
        self.textbox_SR.configure(state="disabled")
        # self.textbox.configure(state="disabled")

        self.entry = customtkinter.CTkEntry(self.conversation, placeholder_text="Type here", height=30)

        # Recording Button
        image_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_images")
        mic_image = customtkinter.CTkImage(Image.open(os.path.join(image_path, "microphone.png")),
                                           size=(26, 26))

        self.talk_button = customtkinter.CTkButton(frame, text="Talk to the Virtual Assistant",
                                                   font=customtkinter.CTkFont(size=15, weight="bold"), image=mic_image,
                                                   height=75, width=400,
                                                   command=self.recording_event)

        # self.test_button  = customtkinter.CTkButton(frame, text="Test",
        #                                           font=customtkinter.CTkFont(size=15, weight="bold"), image=mic_image,
        #                                          height=75, width=400,
        #                                          command=self.test_function)
        # Recording in Progree Bar
        self.progressbar_talking = customtkinter.CTkProgressBar(frame, mode="indeterminate")

        # voicelabel = customtkinter.CTkLabel(recognized_speech,
        #                                    text="Here you will find the whole conversation:",
        #                                   font=customtkinter.CTkFont(size=15, weight="bold"))
        # voicelabel.grid(row=0, column=1, columnspan=2, padx=20, pady=(10, 10), sticky='w')

        # Stop Button
        stop_button = customtkinter.CTkButton(text="Stop", master=frame, fg_color="red", width=50, border_width=2,
                                              command=self.stop_event)
        stop_button.grid(padx=(20, 20), pady=(20, 20), sticky="sew")

        # Grid Layout
        # self.progressbar_talking.grid(row=0, column=1, columnspan=1, padx=(20, 10), pady=(10, 10), sticky="ew")

        self.talk_button.grid(row=1, column=0, padx=(20, 20), pady=(20, 20), sticky="nsew")
        # self.test_button.grid(row=4, column=0, padx=(20, 20), pady=(20, 20), sticky="nsew")

        self.textbox_SR.grid(row=2, column=0, padx=(20, 20), pady=(20, 20), sticky="w")
        # self.textbox.grid(row=2, column=0, padx=(20, 20), pady=(10, 10), sticky="e")

        # self.entry.grid(row=3, column=0, padx=(20, 20), pady=(10, 10), sticky="nsew")

        # set default values

    def create_study_frame(self):
        App.frames["Talking_Frame"] = customtkinter.CTkFrame(self, corner_radius=0, width=1300, height=1000)

        frame = App.frames['Talking_Frame']

        # Confidence Label
        radio_button_size = 15
        progress_questions = 0
        App.frames["Talking_Frame"].grid_rowconfigure((0, 1), weight=1)
        App.frames["Talking_Frame"].grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        frame = App.frames['Talking_Frame']
        # create sidebar frame with widgets
        sidebar_frame = customtkinter.CTkFrame(frame, corner_radius=0)
        sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        sidebar_frame.grid_rowconfigure(5, weight=1)

        # Progress Bar
        self.progressbar_1 = customtkinter.CTkProgressBar(frame)
        self.progressbar_1.grid(row=0, column=0, columnspan=1, padx=(20, 10), pady=(10, 10), sticky="ew")

        # Question
        self.logo_label = customtkinter.CTkLabel(frame, text=starting_question,
                                            font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=1, column=0, padx=20, pady=(20, 10), sticky='w')

        # Voice Assistant Answer
        assistant_answer = customtkinter.CTkFrame(frame)
        assistant_answer.grid(row=2, column=0, rowspan=1, sticky="nsew")
        assistant_answer.grid_rowconfigure(2, weight=1)
        assistant_answer.grid_columnconfigure(0, weight=1)

        voicelabel = customtkinter.CTkLabel(assistant_answer, text="Voice Assistant Answer:",
                                            font=customtkinter.CTkFont(size=15, weight="bold"))
        voicelabel.grid(row=1, column=0, padx=20, pady=(10, 10), sticky='w')

        self.textbox = customtkinter.CTkTextbox(assistant_answer, width=400, wrap="word")
        self.textbox.grid(row=2, column=0, padx=(20, 20), pady=(10, 10), sticky="nsew")

        # create radiobutton frame
        radiobutton_frame = customtkinter.CTkFrame(frame)
        radiobutton_frame.grid(row=3, column=0, padx=(20, 20), pady=(20, 0), sticky="nsew")

        label_radio_group = customtkinter.CTkLabel(master=radiobutton_frame,
                                                   text="How confident are you in the response of the assistant?")
        label_radio_group.grid(row=0, column=0, columnspan=5, padx=10, pady=10, sticky="w")

        label_radio_confidenceHigh = customtkinter.CTkLabel(master=radiobutton_frame,
                                                            text="High Confidence")
        label_radio_confidenceHigh.grid(row=1, column=6, columnspan=1, padx=10, pady=10, sticky="w")

        label_radio_confidenceLow = customtkinter.CTkLabel(master=radiobutton_frame,
                                                           text="No confidence")
        label_radio_confidenceLow.grid(row=1, column=0, columnspan=1, padx=10, pady=10, sticky="e")

        radio_button_1 = customtkinter.CTkRadioButton(master=radiobutton_frame, variable=self.radio_var, value=0, text='',
                                                      radiobutton_width=radio_button_size,
                                                      radiobutton_height=radio_button_size)
        radio_button_1.grid(row=1, column=1, pady=5, padx=10, sticky="")

        radio_button_2 = customtkinter.CTkRadioButton(master=radiobutton_frame, variable=self.radio_var,
                                                      value=1, text='', radiobutton_width=radio_button_size,
                                                      radiobutton_height=radio_button_size)
        radio_button_2.grid(row=1, column=2, pady=5, padx=10, sticky="")

        radio_button_3 = customtkinter.CTkRadioButton(master=radiobutton_frame, variable=self.radio_var,
                                                      value=2, text='', radiobutton_width=radio_button_size,
                                                      radiobutton_height=radio_button_size)
        radio_button_3.grid(row=1, column=3, pady=5, padx=10, sticky="")

        radio_button_4 = customtkinter.CTkRadioButton(master=radiobutton_frame, variable=self.radio_var,
                                                      value=3, text='', radiobutton_width=radio_button_size,
                                                      radiobutton_height=radio_button_size)
        radio_button_4.grid(row=1, column=4, pady=5, padx=10, sticky="")

        radio_button_5 = customtkinter.CTkRadioButton(master=radiobutton_frame, variable=self.radio_var,
                                                      value=4, text='', radiobutton_width=radio_button_size,
                                                      radiobutton_height=radio_button_size)
        radio_button_5.grid(row=1, column=5, pady=5, padx=10, sticky="")

        # User Answer
        user_frame = customtkinter.CTkFrame(frame)
        user_frame.grid(row=4, column=0, rowspan=1, sticky="nsew")
        user_frame.grid_rowconfigure(2, weight=1)
        user_frame.grid_columnconfigure(0, weight=1)

        yourAnswer = customtkinter.CTkLabel(user_frame, text="Your Answer",
                                            font=customtkinter.CTkFont(size=15, weight="bold"))
        yourAnswer.grid(row=0, column=0, padx=(20, 20), pady=(10, 10), sticky='w')

        self.entry = customtkinter.CTkEntry(user_frame, placeholder_text="Type your final answer here")
        self.entry.grid(row=1, column=0, columnspan=2, padx=(20, 20), pady=(10, 10), sticky="nsew")

        # Submission Button
        submit_button = customtkinter.CTkButton(text="Submit", master=frame, border_width=2, command=self.submit_event)
        submit_button.grid(row=5, column=0, padx=(20, 20), pady=(20, 20), sticky="e")

        # Back Button
        back_button = customtkinter.CTkButton(text="Back", master=frame, fg_color="transparent", border_width=2,
                                              command=self.back_event)
        back_button.grid(row=5, column=0, padx=(20, 20), pady=(20, 20), sticky="w")

        # Stop Button
        stop_button = customtkinter.CTkButton(text="Stop", master=frame, fg_color="red", border_width=2,
                                              command=self.stop_event)
        stop_button.grid(row=5, column=1, padx=(20, 20), pady=(20, 20), sticky="e")

        # Recording Button
        image_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_images")
        mic_image = customtkinter.CTkImage(Image.open(os.path.join(image_path, "microphone.png")),
                                           size=(26, 26))

        self.talk_button = customtkinter.CTkButton(frame, text="Talk to the Virtual Assistant",
                                              font=customtkinter.CTkFont(size=15, weight="bold"), image=mic_image, height=75,
                                              command=self.recording_event)

        self.talk_button.grid(row=1, column=1, rowspan=1, padx=(20, 20), pady=(20, 20), sticky="nsew")

        # Recording in Progree Bar
        self.progressbar_talking = customtkinter.CTkProgressBar(frame, mode="indeterminate")

        # Recognized Answer
        recognized_speech = customtkinter.CTkFrame(frame)
        recognized_speech.grid(row=2, column=1, rowspan=3, sticky="nw")
        recognized_speech.grid_rowconfigure(2, weight=1)
        recognized_speech.grid_columnconfigure(0, weight=1)

        voicelabel = customtkinter.CTkLabel(recognized_speech,
                                            text="Here you will find the whole conversation:",
                                            font=customtkinter.CTkFont(size=15, weight="bold"))
        voicelabel.grid(row=0, column=1, columnspan=2, padx=20, pady=(10, 10), sticky='w')

        self.textbox_SR = customtkinter.CTkTextbox(recognized_speech, wrap="word", width=400)
        self.textbox_SR.grid(row=1, column=1, padx=(20, 20), pady=(20, 0), sticky="w")

        # set default values
        self.progressbar_1.set(progress_questions / number_questions)
        self.textbox.insert("0.0", "This is where your voice assistant's answer will be \n\n")
        self.textbox_SR.insert("0.0", "You: ...")

    def __init__(self):
        super().__init__()
        self.stop_listening = None
        self.merge_index = 0
        self.phrase_time = None
        self.starting = True
        self.last_sample = bytes()
        self.transcription_completed = False
        self.transcription = []
        self.subject_id = '0000'
        self.num_of_frames = 2
        self.stop = 0
        self.radio_var = tkinter.IntVar(value=2)
        self.title("Voice Assistant")
        #self.geometry("1300x1000")
        self.talking_counter = 0
        # contains everything
        self.main_container = customtkinter.CTkFrame(self, width=1300, height=1000)
        self.main_container.pack(fill=None, expand=True, padx=10, pady=10)
        self.mode = "Study"

        # buttons to select the frames for main menu
        bt_Study_Frame = customtkinter.CTkButton(self.main_container, text="Just have a conversation \n with HuggingChat", command=self.study_Frame_selector, width=150, height=128, font=customtkinter.CTkFont(size=20, weight="bold"))
        bt_Study_Frame.place(relx=0.3, rely=0.5, anchor=tkinter.CENTER)

        bt_Talking_Frame = customtkinter.CTkButton(self.main_container, text="Start Study Experiment", command=self.talking_Frame_selector, width=150, height=128, font=customtkinter.CTkFont(size=20, weight="bold"))
        bt_Talking_Frame.place(relx=0.7, rely=0.5, anchor=tkinter.CENTER)

        self.progress_questions = 0
        self.text_queue = ""
        self.text_answer = ""
        self.conversation_tracker = []
        self.conversation_number = 2


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    app = App()
    app.resizable(True, True)
    app.mainloop()






