import speech_recognition as sr
import time
import os
import cv2
import requests
import threading
import paho.mqtt.client as mqtt
import accelerometer_new as accelerometer
import ultrasonic
import yolo_detect_new as yolo_detect
import queue

from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play

from p_ocr import LiveOCRDetector

# Flask server URL
flask_server_url = "http://<laptop_ip>:5000/upload_video"

# Video filename
mp4_filename = "/home/qunzhen/video.mp4"

# Initialize the camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 24)

# Initialize the Recognizer class for speech recognition
r = sr.Recognizer()

# State variables
is_recording = False
video_writer = None
accelerometer_thread = None
ultrasonic_thread = None
stop_accel = False
stop_ultrasonic = False
yolo_detector = None

# Create a priority queue for audio messages
# Priority levels: 1 = highest priority, 5 = lowest priority
audio_queue = queue.PriorityQueue()
audio_thread = None
stop_audio_thread = False
last_announced_objects = set()  # Keep track of previously announced objects
announcement_cooldown = 5  # Seconds between announcing the same object again

ocr_detector = LiveOCRDetector(audio_queue)

# MQTT topic
mqtt_topic = "fall_detection/status"


# MQTT message handler
def on_message(client, userdata, message):
    if message.topic == mqtt_topic:
        msg = message.payload.decode()
        if "Fall detected" in msg:
            add_to_audio_queue("Someone fell down please go to help them", priority=1)


def add_to_audio_queue(text, priority=3):
    """Add text to be spoken to the queue with priority (1=highest, 5=lowest)"""
    # Use current timestamp as secondary sort key to maintain FIFO order within same priority
    audio_queue.put((priority, time.time(), text))
    print(f"Added to audio queue (priority {priority}): {text}")


def process_audio_queue():
    """Process and speak items in the audio queue"""
    global stop_audio_thread

    print("Audio queue processor started")
    while not stop_audio_thread:
        try:
            # Try to get an item from the queue, but don't block indefinitely
            try:
                priority, _, text = audio_queue.get(block=True, timeout=1.0)

                # Speak the text using ultrasonic module's speak function
                print(f"Speaking (priority {priority}): {text}")
                speak_text(text)

                # Mark the task as done
                audio_queue.task_done()

                # Small delay after speaking
                time.sleep(0.5)
            except queue.Empty:
                # Queue is empty, continue checking
                pass
        except Exception as e:
            print(f"Error in audio queue processor: {e}")

    print("Audio queue processor stopped")


def speak_text(text):
    # Convert text to speech
    tts = gTTS(text=text, lang='en')
    # Save the audio to a temporary file
    tts.save("/tmp/speech_output.mp3")

    # Load the mp3 file with pydub
    sound = AudioSegment.from_mp3("/tmp/speech_output.mp3")

    # Play the sound
    play(sound)


def start_recording():
    global is_recording, video_writer, accelerometer_thread, ultrasonic_thread, stop_accel, stop_ultrasonic, yolo_detector, audio_thread, stop_audio_thread
    print("Recording video...")
    is_recording = True

    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Try mp4v instead of H264
    video_writer = cv2.VideoWriter(mp4_filename, fourcc, 24, (640, 480))
    if not video_writer.isOpened():
        print("Error: VideoWriter failed to open")
        is_recording = False
        return

    # Initialize YOLO detector if not already done
    if yolo_detector is None:
        yolo_detector = yolo_detect.YOLODetector(model_path="/home/qunzhen/try/models/best_packages.pt")

    # Start audio queue processor if not already running
    if audio_thread is None or not audio_thread.is_alive():
        stop_audio_thread = False
        audio_thread = threading.Thread(target=process_audio_queue, daemon=True)
        audio_thread.start()
        print("Audio queue processor started.")

    # Add initial announcement to queue
    add_to_audio_queue("Starting recording and object detection", priority=2)

    # Start YOLO detection
    # Change to True if you want to see the camera interface
    yolo_detector.start_detection(cap, display=True)
    print("YOLO detection started.")

    # Start a thread to monitor YOLO detections and announce them
    yolo_announce_thread = threading.Thread(target=announce_yolo_detections, daemon=True)
    yolo_announce_thread.start()
    print("YOLO announcements started.")

    # Start accelerometer in a separate thread
    stop_accel = False
    accelerometer_thread = threading.Thread(
        target=run_accelerometer_wrapper,
        daemon=True
    )
    accelerometer_thread.start()
    print("Accelerometer started.")

    # Start ultrasonic sensor in a separate thread
    stop_ultrasonic = False
    ultrasonic_thread = threading.Thread(
        target=run_ultrasonic_sensor,
        daemon=True
    )
    ultrasonic_thread.start()
    print("Ultrasonic sensor started.")

    # Record video with YOLO annotations
    recording_thread = threading.Thread(target=record_video_loop, daemon=True)
    recording_thread.start()


def announce_yolo_detections():
    """Thread function to announce YOLO detections"""
    global is_recording, yolo_detector, ocr_detector

    last_announced_classes = {}  # Track last announced object classes

    while is_recording:
        if yolo_detector is None:
            time.sleep(1)
            continue

        # Get current detections
        current_detections = yolo_detector.get_latest_detections()
        if current_detections:
            current_time = time.time()

            # Process each detection
            for obj_class, count in current_detections.items():
                # Check if this is a new object class or if the last announcement was more than cooldown ago
                if (obj_class not in last_announced_classes or
                        (current_time - last_announced_classes[obj_class]['time'] > announcement_cooldown)):
                    if count != 0:
                        message = f"Detected {count} {obj_class}s"
                        if obj_class == 'packages':
                            print("hi")
                            # ocr_detector.trigger_ocr_detection()
                            current_frame = yolo_detector.get_latest_frame()
                            if current_frame is not None:
                                # Process the frame with OCR
                                ocr_detector.trigger_ocr_detection(frame=current_frame)
                        else:
                            add_to_audio_queue(message, priority=3)

                    # Update last announced info
                    last_announced_classes[obj_class] = {
                        'time': current_time,
                        'count': count
                    }

        time.sleep(1)  # Check for new detections every second


def record_video_loop():
    global is_recording, video_writer, yolo_detector

    while is_recording:
        if not video_writer.isOpened():
            print("VideoWriter not open during recording loop")
            break

        # Get the latest annotated frame from YOLO detector
        frame = yolo_detector.get_latest_frame()
        if frame is not None:
            video_writer.write(frame)
        else:
            # Fallback to direct camera capture if YOLO hasn't processed a frame yet
            ret, frame = cap.read()
            if ret:
                video_writer.write(frame)
            else:
                print("Failed to grab frame")
                time.sleep(0.01)  # Small delay to prevent CPU hogging

        time.sleep(0.01)  # Small delay to prevent CPU hogging


# Function to run ultrasonic sensor and publish distance data
def run_ultrasonic_sensor():
    global stop_ultrasonic
    ultrasonic_topic = "sensor/ultrasonic/distance"

    print("Ultrasonic sensor monitoring started")
    try:
        while not stop_ultrasonic:
            # Get distance from ultrasonic module
            distance = ultrasonic.detect_obstacle()
            print(f"Distance: {distance} cm")

            # Publish to MQTT
            mqtt_client.publish(ultrasonic_topic, str(distance))

            # Check if obstacle is too close and queue warning
            if distance < 30:  # Threshold in cm
                # Use priority 1 (highest) for obstacle warnings
                add_to_audio_queue(f"Obstacle detected ahead! {distance} centimeters away", priority=1)

            time.sleep(1)  # Delay between measurements
    except Exception as e:
        print(f"Error in ultrasonic thread: {e}")
    finally:
        print("Ultrasonic sensor monitoring stopped")


# Wrapper function to run accelerometer with stop check
def run_accelerometer_wrapper():
    # Make sure logs directory exists
    os.makedirs(os.path.expanduser("~/logs"), exist_ok=True)

    # Start the actual accelerometer function
    try:
        # We can't directly modify the accelerometer's main loop,
        # so we'll run it in a separate thread that we can terminate
        accel_exec_thread = threading.Thread(
            target=lambda: accelerometer.run_accelerometer(verbose=False),
            daemon=True
        )
        accel_exec_thread.start()

        # Check the stop flag periodically
        while not stop_accel:
            time.sleep(0.5)  # Check every half second

        print("Accelerometer stopping...")
        # Thread will be automatically terminated since it's a daemon thread

    except Exception as e:
        print(f"Error in accelerometer wrapper: {e}")


def stop_recording():
    global is_recording, stop_accel, stop_ultrasonic, yolo_detector, video_writer, stop_audio_thread
    if is_recording:
        print("Recording stopped.")
        is_recording = False

        # Add stop announcement to queue with priority 2
        add_to_audio_queue("Stopping recording", priority=2)

        # Stop YOLO detection
        if yolo_detector is not None:
            yolo_detector.stop_detection()
            print("YOLO detection stopped.")

        # Signal the accelerometer to stop
        stop_accel = True
        print("Stopping accelerometer...")

        # Signal the ultrasonic sensor to stop
        stop_ultrasonic = True
        print("Stopping ultrasonic sensor...")

        # Make sure to release the video writer properly
        if video_writer is not None and video_writer.isOpened():
            video_writer.release()
            print("Video writer released.")

        # Wait for file to be completely written
        time.sleep(2)  # Give more time for file operations to complete

        # Send the MP4 file to Flask
        send_video_to_flask()

        # Give some time for final announcements
        time.sleep(3)

        # Signal the audio thread to stop
        stop_audio_thread = True


def send_video_to_flask():
    # Check if file exists and has content
    if not os.path.exists(mp4_filename) or os.path.getsize(mp4_filename) == 0:
        print(f"Error: Video file {mp4_filename} doesn't exist or is empty")
        add_to_audio_queue("Error: Video file is empty or doesn't exist", priority=1)
        return

    print(f"Sending video file (size: {os.path.getsize(mp4_filename)} bytes)")
    add_to_audio_queue("Sending video file to server", priority=2)

    try:
        with open(mp4_filename, "rb") as video_file:
            files = {"video": video_file}
            response = requests.post(flask_server_url, files=files)
            if response.status_code == 200:
                print("Video successfully sent.")
                add_to_audio_queue("Video successfully sent to server", priority=2)
            else:
                print(f"Error sending video: {response.status_code}, {response.text}")
                add_to_audio_queue("Error sending video to server", priority=1)
    except Exception as e:
        print(f"Failed to send video: {e}")
        add_to_audio_queue("Failed to send video to server", priority=1)


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
                elif "start" not in command and not is_recording:
                    speak_text("Unrecognized command. Please say 'start' to begin recording.")
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


# MQTT setup to listen for fall detection alerts
mqtt_broker = "<pi_ip>"  # Changed from empty string
mqtt_port = 1883
mqtt_client = mqtt.Client()
try:
    mqtt_client.connect("<pi_ip>", mqtt_port, 60)
    mqtt_client.subscribe(mqtt_topic)
    mqtt_client.on_message = on_message
except Exception as e:
    print(f"Failed to connect to MQTT broker: {e}")

# Start listening for commands
command_thread = threading.Thread(target=listen_for_commands)
command_thread.start()
speak_text("Welcome to Blind Shopper Assistance. Say 'start' to begin recording.")
# Start MQTT loop in a separate thread
try:
    mqtt_thread = threading.Thread(target=mqtt_client.loop_forever)
    mqtt_thread.daemon = True  # Make it a daemon thread
    mqtt_thread.start()
except Exception as e:
    print(f"Failed to start MQTT thread: {e}")

# Cleanup on exit
try:
    command_thread.join()
    # Don't join the MQTT thread as it's a daemon thread and will be terminated when the program exits
except KeyboardInterrupt:
    print("Program interrupted by user")
    if is_recording:
        stop_recording()
finally:
    # Final cleanup
    if cap.isOpened():
        cap.release()
    cv2.destroyAllWindows()
