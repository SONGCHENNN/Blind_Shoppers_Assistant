import speech_recognition as sr
import time
import os
import cv2
import requests
import threading
import paho.mqtt.client as mqtt
import accelerometer  # Import accelerometer (fall detection) script

# Flask server URL
flask_server_url = "http://<laptop_ip>:5000/upload_video"

# Video filename
mp4_filename = "/home/qunzhen/video.mp4"

# Initialize the camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 24)

# Video writer setup
fourcc = cv2.VideoWriter_fourcc(*'H264')
out = cv2.VideoWriter(mp4_filename, fourcc, 24, (640, 480))


# Initialize the Recognizer class for speech recognition
r = sr.Recognizer()

# State variable to track whether we are recording or not
is_recording = False

# Function to start recording video
def start_recording():
    global is_recording
    print("Recording video...")
    is_recording = True
    while is_recording:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        out.write(frame)

# Function to stop recording and send video to Flask server
def stop_recording():
    global is_recording
    if is_recording:
        print("Recording stopped.")
        cap.release()
        out.release()

        # Send the MP4 file to Flask
        with open(mp4_filename, "rb") as video_file:
            files = {"video": video_file}
            try:
                response = requests.post(flask_server_url, files=files)
                if response.status_code == 200:
                    print("Video successfully sent.")
                else:
                    print(f"Error sending video: {response.status_code}")
            except Exception as e:
                print(f"Failed to send video: {e}")
        is_recording = False

# Listen for speech commands (start/stop)
def listen_for_commands():
    global is_recording
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source)
        print("Say 'start' to begin recording or 'stop' to end.")

        while True:
            audio = r.listen(source)
            try:
                command = r.recognize_google(audio).lower()
                print(f"You said: {command}")

                if "start" in command and not is_recording:
                    print("Starting recording...")
                    start_recording_thread = threading.Thread(target=start_recording)
                    start_recording_thread.start()
                elif "stop" in command and is_recording:
                    print("Stopping recording...")
                    stop_recording()
                    break
                else:
                    print("Unrecognized command. Please say 'start' to begin recording or 'stop' to end recording.")
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand audio")
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service; {e}")

# MQTT Callback function for receiving fall alerts
def on_message(client, userdata, message):
    payload = message.payload.decode("utf-8")
    if payload == "Fall detected!":
        print("Fall detected! Stopping video recording...")
        stop_recording()

# MQTT setup to listen for fall detection alerts
mqtt_broker = "<raspberry_pi_ip>"
mqtt_port = 1883
mqtt_topic = "fall_detection_alert"
mqtt_client = mqtt.Client()
mqtt_client.connect(mqtt_broker, mqtt_port, 60)
mqtt_client.subscribe(mqtt_topic)
mqtt_client.on_message = on_message

# Start listening for commands
command_thread = threading.Thread(target=listen_for_commands)
command_thread.start()

# Start MQTT loop in a separate thread
mqtt_thread = threading.Thread(target=mqtt_client.loop_forever)
mqtt_thread.start()

# Start the accelerometer (fall detection) in a separate thread
accelerometer_thread = threading.Thread(target=accelerometer.run_accelerometer, daemon=True)
accelerometer_thread.start()

# Main thread will keep running
command_thread.join()
mqtt_thread.join()
accelerometer_thread.join()

#if __name__ == "__main__":
   # accelerometer.run_accelerometer()
#listen_for_commands()
