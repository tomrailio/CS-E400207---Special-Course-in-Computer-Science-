from hugchat import hugchat
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

questions = pd.read_csv('QuestionSurvey.csv')
starting_question = questions.loc[0]['Question']
number_questions = len(questions.index)

url = "https://app.coqui.ai/api/v2/speakers"
url = "https://app.coqui.ai/api/v2/samples/from-prompt/"

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer DZflHJcnJrWjVaHHpAc6CkyVG3JM7mM9tcBla0pYaJmlDpEX2vQEQV8rZ9R2iEnP"
}

model_name = TTS.list_models()[8]

tts = TTS(model_name=model_name, progress_bar=False, gpu=False)

customtkinter.set_appearance_mode("dark")  # Modes: system (default), light, dark
customtkinter.set_default_color_theme("dark-blue")  # Themes: blue (default), dark-blue, green

print('Initializing')
recording_folder = 'OutputRecordings'
transcription_folder = 'OutputTranscription'
trust_scores_folder = 'OutputTrustScores'
recording_in_folder = 'InputRecordings'

if not os.path.exists(recording_folder):
   os.makedirs(recording_folder)

if not os.path.exists(transcription_folder):
   os.makedirs(transcription_folder)

if not os.path.exists(trust_scores_folder):
   os.makedirs(trust_scores_folder)

if not os.path.exists(recording_in_folder):
   os.makedirs(recording_in_folder)

model = whisper.load_model("base")
chatbot = hugchat.ChatBot(cookie_path="cookies.json")

# Possible Mic - Run when you run the programm the first time to select the right microphone
available_mics = sr.Microphone.list_microphone_names()
mic_index = 1

debug = False

r = sr.Recognizer()
mic = sr.Microphone(device_index=mic_index)
audio_file = 'output.wav'

conversation_list = []
path = "conversation_summary.txt"
if os.path.isfile(path):
    with open(path) as f:
        prior_conversation = f.readlines()


class App(customtkinter.CTk):

    frames = {"frame1": None, "frame2": None}

    def stop_event(self):
        exit()

    def frame1_selector(self):
        App.frames["frame2"].pack_forget()
        App.frames["frame1"].pack(in_=self.main_container, side=tkinter.TOP, fill=tkinter.BOTH, expand=True,
                                  padx=0, pady=0)

    def frame2_selector(self):
        self.title("Voice Assistant Example")
        self.geometry(f"{1300}x{1000}")
        self.create_study_frame()
        App.frames["frame1"].pack_forget()
        App.frames["frame2"].pack(in_=self.main_container, side=tkinter.TOP, fill=tkinter.BOTH, expand=True,
                                  padx=0, pady=0)

    def stop_event(self):
        self.stop = 1

    def prior_conversations_event(self, new_appearance_mode: str):
        id_conv = 2
        text_queue = 2
        text_answer = chatbot.chat(f"This was our prior conversation: {prior_conversation}")

        conversation_list.append(text_queue + text_answer)
        if id_conv == 2:
            conversation = ' '.join(conversation_list)
            text_answer = chatbot.chat(f'Summarize this text: {text_queue}')

            with open("conversation_summary.txt", "w") as f:
                f.write(text_answer)

    def recording_event(self):

        self.talk_button.configure(state="disabled")
        self.talk_button.configure(text="Listening...")
        self.progressbar_talking.grid(row=0, column=1, columnspan=1, padx=(20, 10), pady=(10, 10), sticky="ew")
        self.progressbar_talking.start()

        text_queue = self.recognize()
        
        self.progressbar_talking.stop()
        print(f'This is what I heard: {text_queue}')
        self.text_queue = text_queue
        text_answer = chatbot.chat(text_queue)
        print(f'This is my answer: {text_answer}')

        self.conversation_tracker.append(text_queue)
        self.conversation_tracker.append(text_answer)

        self.textbox.delete("0.0", "end")
        self.textbox.insert("0.0", text=text_answer)
        filename = 'output_response.wav'
        self.textbox_SR.delete("0.0", "end")
        self.textbox_SR.insert("0.0", text=text_queue)
        tts.tts_to_file(text=text_answer, file_path='output_response.wav')
        data, fs = sf.read(filename, dtype='float32')
        sd.play(data, fs)
        self.conversation_tracker.append(text_queue)
        self.conversation_tracker.append(text_answer)
        self.talk_button.configure(text="Talk to the Virtual Assistant")
        self.talk_button.configure(state="normal")

    def submit_event(self):
        self.progress_questions += 1
        self.logo_label.configure(text=questions.loc[self.progress_questions]['Question'])
        self.progressbar_1.set(self.progress_questions / number_questions)

        if not debug:
            with open("OutputTranscription/conversation_summary.txt", "w") as f:
                for lines in self.conversation_tracker:
                    f.write(lines)

            with open("OutputTrustScores/TrustScores.txt", "w") as f:
                f.write(f"{questions.loc[self.progress_questions]['Question'], self.radio_var}")

        id = chatbot.new_conversation()
        chatbot.change_conversation(id)
        self.conversation_tracker = []

    def back_event(self):
        self.progress_questions -= 1
        if self.progress_questions >= 0:
            self.logo_label.configure(text=questions.loc[self.progress_questions]['Question'])
            self.progressbar_1.set(self.progress_questions / number_questions)

    def recognize(self):

        with mic as source:
            print("Listening....")
            #r.adjust_for_ambient_noise(mic, duration=1)
            audio_data = r.listen(source)

        output_file = os.path.join(recording_folder, f"output{self.progress_questions}.wav")
        with open(output_file, "wb") as file:
            file.write(audio_data.get_wav_data())

        audio = whisper.load_audio(output_file)
        audio = whisper.pad_or_trim(audio)

        # make log-Mel spectrogram and move to the same device as the model
        mel = whisper.log_mel_spectrogram(audio).to(model.device)

        # decode the audio
        options = whisper.DecodingOptions(fp16=False, language="en")
        result = whisper.decode(model, mel, options)

        return result.text

    def create_study_frame(self):
        # Confidence Label
        radio_button_size = 15
        progress_questions = 0
        App.frames["frame2"] = customtkinter.CTkFrame(self, corner_radius=0, width=1300, height=1000)

        App.frames["frame2"].grid_rowconfigure((0, 1), weight=1)
        App.frames["frame2"].grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        frame = App.frames["frame2"]
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

        self.textbox = customtkinter.CTkTextbox(assistant_answer, width=250)
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

        entry = customtkinter.CTkEntry(user_frame, placeholder_text="Type your final answer here")
        entry.grid(row=1, column=0, columnspan=2, padx=(20, 20), pady=(10, 10), sticky="nsew")

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
                                              command=threading.Thread(target=self.recording_event).start)

        self.talk_button.grid(row=1, column=1, rowspan=1, padx=(20, 20), pady=(20, 20), sticky="nsew")

        # Recording in Progree Bar
        self.progressbar_talking = customtkinter.CTkProgressBar(frame, mode="indeterminate")

        # Recognized Answer
        recognized_speech = customtkinter.CTkFrame(frame)
        recognized_speech.grid(row=2, column=1, rowspan=3, sticky="nsew")
        recognized_speech.grid_rowconfigure(2, weight=1)
        recognized_speech.grid_columnconfigure(0, weight=1)

        voicelabel = customtkinter.CTkLabel(recognized_speech,
                                            text="This is what the Voice Assistant understood \n and the whole conversation:",
                                            font=customtkinter.CTkFont(size=15, weight="bold"))
        voicelabel.grid(row=0, column=1, padx=20, pady=(10, 10), sticky='nw')

        self.textbox_SR = customtkinter.CTkTextbox(recognized_speech, width=50)
        self.textbox_SR.grid(row=1, column=1, padx=(20, 20), pady=(20, 0), sticky="nsew")

        # set default values
        self.progressbar_1.set(progress_questions / number_questions)
        self.textbox.insert("0.0", "This is where your voice assistant's answer will be \n\n")
        self.textbox_SR.insert("0.0", "Here will be what I understood.")

    def __init__(self):
        super().__init__()
        self.num_of_frames = 2
        self.stop = 0
        self.radio_var = tkinter.IntVar(value=2)
        self.title("Voice Assistant")
        self.geometry("1300x1000")

        # contains everything
        self.main_container = customtkinter.CTkFrame(self, width=1300, height=1000)
        self.main_container.pack(fill=None, expand=True, padx=10, pady=10)

        #panel = customtkinter.CTkFrame(main_container, corner_radius=0, fg_color="grey")
        #panel.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True, padx=0, pady=0)

        # buttons to select the frames
        bt_frame1 = customtkinter.CTkButton(self.main_container, text="Just have a conversation \n with HuggingChat", command=self.frame1_selector, width=150, height=128, font=customtkinter.CTkFont(size=20, weight="bold"))
        bt_frame1.place(relx=0.3, rely=0.5, anchor=tkinter.CENTER)

        bt_frame2 = customtkinter.CTkButton(self.main_container, text="Start Study Experiment", command=self.frame2_selector, width=150, height=128, font=customtkinter.CTkFont(size=20, weight="bold"))
        bt_frame2.place(relx=0.7, rely=0.5, anchor=tkinter.CENTER)

        App.frames['frame1'] = customtkinter.CTkFrame(self)
        bt_from_frame1 = customtkinter.CTkButton(App.frames['frame1'], text="Test 1", command=lambda: print("test 1"))
        bt_from_frame1.place(relx=0.5, rely=0.5, anchor=tkinter.CENTER)

        App.frames['frame2'] = self.create_study_frame()

        self.progress_questions = 0
        self.text_queue = ""
        self.text_answer = ""
        self.conversation_tracker = []


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    app = App()
    app.resizable(True, True)
    app.mainloop()






