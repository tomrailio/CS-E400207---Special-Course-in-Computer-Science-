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

customtkinter.set_appearance_mode("System")  # Modes: system (default), light, dark
customtkinter.set_default_color_theme("dark-blue")  # Themes: blue (default), dark-blue, green

print('Initializing')
recording_folder = 'Output Recordings'
transcription_folder = 'Output Transcription'
if not os.path.exists(recording_folder):
   # Create a new directory because it does not exist
   os.makedirs(recording_folder)

if not os.path.exists(transcription_folder):
   # Create a new directory because it does not exist
   os.makedirs(transcription_folder)


model = whisper.load_model("base")
chatbot = hugchat.ChatBot(cookie_path="cookies.json")
r = sr.Recognizer()
mic = sr.Microphone(device_index=2)
audio_file = 'output.wav'

# Possible Setup
available_mics = sr.Microphone.list_microphone_names()

conversation_list = []
path = "conversation_summary.txt"
if os.path.isfile(path):
    with open(path) as f:
        prior_conversation = f.readlines()


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.progress_questions = 0
        self.text_queue = ""
        self.text_answer = ""
        # configure window
        self.title("Voice Assistant Example")
        self.geometry(f"{1300}x{1000}")

        # configure grid layout (2x5)
        self.grid_columnconfigure((0, 1), weight=0)
        self.grid_rowconfigure((0, 1, 2, 3, 4, 5), weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        # Progress Bar
        self.progressbar_1 = customtkinter.CTkProgressBar(self)
        self.progressbar_1.grid(row=0, column=0, columnspan=1, padx=(20, 10), pady=(10, 10), sticky="ew")

        # Question
        self.logo_label = customtkinter.CTkLabel(self, text=starting_question, font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=1, column=0, padx=20, pady=(20, 10), sticky='w')

        # Voice Assistant Answer
        self.assistant_answer = customtkinter.CTkFrame(self)
        self.assistant_answer.grid(row=2, column=0, rowspan=1, sticky="nsew")
        self.assistant_answer.grid_rowconfigure(2, weight=1)
        self.assistant_answer.grid_columnconfigure(0, weight=1)

        self.voicelabel = customtkinter.CTkLabel(self.assistant_answer, text="Voice Assistant Answer:", font=customtkinter.CTkFont(size=15, weight="bold"))
        self.voicelabel.grid(row=1, column=0, padx=20, pady=(10, 10), sticky='w')

        self.textbox = customtkinter.CTkTextbox(self.assistant_answer, width=250)
        self.textbox.grid(row=2, column=0, padx=(20, 20), pady=(20, 20), sticky="nsew")

        # create radiobutton frame
        self.radiobutton_frame = customtkinter.CTkFrame(self)
        self.radiobutton_frame.grid(row=3, column=0, padx=(20, 20), pady=(20, 0), sticky="nsew")
        self.radio_var = tkinter.IntVar(value=2)

        self.label_radio_group = customtkinter.CTkLabel(master=self.radiobutton_frame, text="How confident are you in the response of the assistant?")
        self.label_radio_group.grid(row=0, column=0, columnspan=5, padx=10, pady=10, sticky="w")

        self.label_radio_confidenceHigh = customtkinter.CTkLabel(master=self.radiobutton_frame,
                                                        text="High Confidence")
        self.label_radio_confidenceHigh.grid(row=1, column=6, columnspan=1, padx=10, pady=10, sticky="w")

        self.label_radio_confidenceLow = customtkinter.CTkLabel(master=self.radiobutton_frame,
                                                        text="No confidence")
        self.label_radio_confidenceLow.grid(row=1, column=0, columnspan=1, padx=10, pady=10, sticky="e")

        # Confidence Label
        radio_button_size = 15

        self.radio_button_1 = customtkinter.CTkRadioButton(master=self.radiobutton_frame, variable=self.radio_var, value=0, text='', radiobutton_width=radio_button_size, radiobutton_height=radio_button_size)
        self.radio_button_1.grid(row=1, column=1, pady=5, padx=10, sticky="")

        self.radio_button_2 = customtkinter.CTkRadioButton(master=self.radiobutton_frame, variable=self.radio_var,
                                                           value=1, text='', radiobutton_width=radio_button_size, radiobutton_height=radio_button_size)
        self.radio_button_2.grid(row=1, column=2, pady=5, padx=10, sticky="")

        self.radio_button_3 = customtkinter.CTkRadioButton(master=self.radiobutton_frame, variable=self.radio_var,
                                                           value=2, text='', radiobutton_width=radio_button_size,
                                                           radiobutton_height=radio_button_size)
        self.radio_button_3.grid(row=1, column=3, pady=5, padx=10, sticky="")

        self.radio_button_4 = customtkinter.CTkRadioButton(master=self.radiobutton_frame, variable=self.radio_var,
                                                           value=3, text='', radiobutton_width=radio_button_size, radiobutton_height=radio_button_size)
        self.radio_button_4.grid(row=1, column=4, pady=5, padx=10, sticky="")

        self.radio_button_5 = customtkinter.CTkRadioButton(master=self.radiobutton_frame, variable=self.radio_var,
                                                           value=4, text='', radiobutton_width=radio_button_size, radiobutton_height=radio_button_size)
        self.radio_button_5.grid(row=1, column=5, pady=5, padx=10, sticky="")

        # User Answer
        self.user_frame = customtkinter.CTkFrame(self)
        self.user_frame.grid(row=4, column=0, padx=(0, 0), pady=(0, 0), sticky="nsew")
        self.user_frame.grid_rowconfigure(2, weight=1)
        self.user_frame.grid_columnconfigure(0, weight=1)

        self.yourAnswer = customtkinter.CTkLabel(self.user_frame, text="Your Answer", font=customtkinter.CTkFont(size=15, weight="bold"))
        self.yourAnswer.grid(row=0, column=0, pady=(20, 20), sticky='w')

        self.entry = customtkinter.CTkEntry(self.user_frame, placeholder_text="Type your final answer here")
        self.entry.grid(row=1, column=0, columnspan=2, pady=(20, 20), sticky="nsew")

        # Submission Button
        self.submit_button = customtkinter.CTkButton(text="Submit", master=self, border_width=2, command=self.submit_event)
        self.submit_button.grid(row=5, column=0, padx=(20, 20), pady=(20, 20), sticky="e")

        # Back Button
        self.back_button = customtkinter.CTkButton(text="Back", master=self, fg_color="transparent", border_width=2, command=self.back_event)
        self.back_button.grid(row=5, column=0, padx=(20, 20), pady=(20, 20), sticky="w")

        # Stop Button
        self.stop_button = customtkinter.CTkButton(text="Stop", master=self, fg_color="red", border_width=2,
                                                   command=self.back_event)
        self.stop_button.grid(row=5, column=1, padx=(20, 20), pady=(20, 20), sticky="e")

        # Recording Button
        image_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_images")
        self.mic_image = customtkinter.CTkImage(Image.open(os.path.join(image_path, "microphone.png")),
                                                 size=(26, 26))

        self.talk_button = customtkinter.CTkButton(self, text="Talk to the Virtual Assistant", image=self.mic_image, font=customtkinter.CTkFont(size=15, weight="bold"), command=self.recording_event)
        self.talk_button.grid(row=0, column=1, rowspan=1, padx=(20, 0), pady=(20, 0), sticky="nsew")

        # Recognized Answer
        self.recognized_speech = customtkinter.CTkFrame(self)
        self.recognized_speech.grid(row=2, column=1, rowspan=1, sticky="nsew")
        self.recognized_speech.grid_rowconfigure(2, weight=1)
        self.recognized_speech.grid_columnconfigure(0, weight=1)

        self.voicelabel = customtkinter.CTkLabel(self.recognized_speech, text="This is what I understood:",
                                                 font=customtkinter.CTkFont(size=15, weight="bold"))
        self.voicelabel.grid(row=0, column=0, padx=20, pady=(10, 10), sticky='nw')

        self.textbox_SR = customtkinter.CTkTextbox(self.recognized_speech, width=50)
        self.textbox_SR.grid(row=1, column=0, padx=(20, 20), pady=(20, 0), sticky="nsew")

        # set default values
        self.progressbar_1.set(self.progress_questions/number_questions)
        self.textbox.insert("0.0", "This is where your voice assistant's answer will be \n\n")
        self.textbox_SR.insert("0.0", "Here will be what I understood.")
    def stop_event(self):
        dialog = customtkinter.CTkInputDialog(text="Type in a number:", title="CTkInputDialog")

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

        text_queue = self.recognize()
        print(f'This is what I heard: {text_queue}')
        self.text_queue = text_queue
        text_answer = chatbot.chat(text_queue)
        print(f'This is my answer: {text_answer}')
        self.textbox.delete("0.0", "end")
        self.textbox.insert("0.0", text=text_answer)
        filename = 'output_response.wav'
        self.textbox_SR.insert("0.0", text=text_queue)
        tts.tts_to_file(text=text_answer, file_path='output_response.wav')
        data, fs = sf.read(filename, dtype='float32')
        sd.play(data, fs)

    def submit_event(self):
        self.progress_questions += 1
        self.logo_label.configure(text=questions.loc[self.progress_questions]['Question'])
        self.progressbar_1.set(self.progress_questions / number_questions)

        with open("conversation_summary.txt", "w") as f:
            f.write(self.text_answer)

    def back_event(self):
        self.progress_questions -= 1
        if self.progress_questions > 0:
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

        # detect the spoken language
        _, probs = model.detect_language(mel)
        print(f"Detected language: {max(probs, key=probs.get)}")

        # decode the audio
        options = whisper.DecodingOptions(fp16=False)
        result = whisper.decode(model, mel, options)

        return result.text


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    app = App()
    app.mainloop()






