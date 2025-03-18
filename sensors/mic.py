import cv2
import time
import requests
import speech_recognition as sr
import threading

def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for 'start' or 'stop' command...")
        recognizer.adjust_for_ambient_noise(source)  # Reduce noise
        try:
            audio = recognizer.listen(source)  # No timeout
            command = recognizer.recognize_google(audio).lower()
            print(f"Recognized: {command}")
            return command
        except sr.UnknownValueError:
            print("Could not understand audio")
        except sr.RequestError:
            print("Could not request results from Google Speech Recognition")
    return None

def listen_for_stop():
    global stop_recording
    while not stop_recording:
        command = recognize_speech()
        if command == "stop":
            stop_recording = True

def start_recording():
    global stop_recording
    stop_recording = False

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 24)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(mp4_filename, fourcc, 24, (640, 480))

    print("Recording started. Say 'stop' to stop recording.")

    # Start a separate thread to listen for "stop"
    stop_thread = threading.Thread(target=listen_for_stop)
    stop_thread.start()

    while not stop_recording:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        out.write(frame)

    cap.release()
    out.release()
    print("Recording complete.")
