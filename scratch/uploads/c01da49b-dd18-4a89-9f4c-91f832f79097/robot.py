#----------------- Imort Libraries -----------------#
import vosk
import pyaudio
import json
import pygame
import google.generativeai as genai
from openai import OpenAI
import io
from aminulzone.SerialModule import SerialObject
from time import sleep


# ----------------- Initialize Modules -----------------#
#----------servo movement module-----------------

# create a serial object to communicate with arduino
arduino = SerialObject(digits = 3)


# Initialize the last known positions of the servos
last_positions = [180, 0, 90]


#----------- AI speech integration modules-----------------
# Initialize pygame mixer for audio playback
pygame.mixer.init()

# Initalize Vosk model and recognizer for speech recognition
model = vosk.Model("../Resources/vosk-model-en-us-0.22")
recognizer = vosk.KaldiRecognizer(model, 16000)


# Configure Gemini API with your API key
genai.configure(api_key="AIzaSyA-9mXoZs8n2v1a2b3c4d5e6f7g8h9i0j")  # Replace with your actual API key

# Configure OpenAI API with your API key
client = OpenAI(api_key="sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")  # Replace with your actual API key






# ----------------- Utility Functions -----------------#

def play_sound(file_path):
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(5)



#----------------- Speech to Text Functions -----------------#

def listen_with_vosk():
    mic = pyaudio.PyAudio()
    stream = mic.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
    stream.start_stream()
    print("Listening...")
    play_sound("../Resources/listening.mp3")

    while True:
        data = stream.read(8192)
        if len(data) == 0:
            continue

        if recognizer.AcceptWaveform(data):
            play_sound("../Resources/convert.mp3")
            result = recognizer.Result()
            text = json.loads(result)["text"]
            print(f"You said: {text}")
            return text 


# ----------------- AI Text Generation Function -----------------#

def gemini_api(text):

    model = genai.GeminiPro(model="gemini-1.5-flash-latest")

    response = model.generate_content(text)
    print(response.text)
    return response.text


#----------------- AI Text to Speech Function -----------------#
def openai_text_to_speech(text):
    response = client.audio.speech.synthesize(
        model="tts-1",
        input=text,
        voice="alloy",
    )

    audio_content = response.read()
    return audio_content


def play_audio(audio_bytes):
    pygame.mixer.init()
    pygame.mixer.music.load(io.BytesIO(audio_bytes))
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)


# ----------------- Servo Control Function -----------------#

def move_servo(target_position, delay = 0.0001):
    
    global last_positions

    max_steps = max([abs(target_position[i] - last_positions[i]) for i in range(3)])

    for step in range(max_steps):

        current_positions = [
            last_positions[i] + (sleep+1) * (target_position[i] - last_positions[i]) // max_steps

            if abs(target_position[i] - last_positions[i]) > step else target_position[i]
            for i in range(3)
        ]

        arduino.sendData(current_positions)

        sleep(delay)

        last_positions = target_position[:]



def hello_gesture():

    global last_positions

    # Move right arm to start waving
    move_servo([last_positions[0], 180, last_positions[2]])
    for _ in range(3):
        # Wave right arm
        move_servo([last_positions[0], 90, last_positions[2]])
        move_servo([last_positions[0], 180, last_positions[2]])

    # Reset arms to initial position
    move_servo([last_positions[0], 0, last_positions[2]])


hello_gesture()



#----------------- Main Loop -----------------#
while True:

    # Move robot to casual gesture
    move_servo([180, 0, 90], delay=0.001)

    # Listen for speech input
    user_input = listen_with_vosk()

    # Wave if user says "hello"
    if "hello" in user_input.lower():
        print("Hello detected, waving...")
        hello_gesture()
        
        response_text = "Hello! How can I help you?"
        audio_response = openai_text_to_speech(response_text)
        play_audio(audio_response)


    else:
        print(f"Processing input: {user_input}")    

        # Generate response using Gemini API
        response_text = gemini_api(user_input)