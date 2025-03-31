import os
import subprocess
from flask import Flask, render_template, request, send_file, jsonify
from flask import render_template_string
import atexit
import shutil
import matplotlib.pyplot as plt
import io
import base64
import time
from datetime import datetime, timedelta

# Email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# MQTT
import threading
import paho.mqtt.client as mqtt
import json

# Ultrasonic data storage
ultrasonic_data = {"distance": None, "last_update": None}
distances = []  # List to store historical distances
timestamps = []  # List to store timestamps
max_data_points = 120  # Maximum number of data points (1 hour at 1 point per minute)
last_data_time = None  # Track the last time we recorded a data point
graph_image = None  # Store the latest graph image

# Global variable to store recipient email
recipient_email = "chinqz042@gmail.com"  # Replace with a dynamic value

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
VIDEO_PATH = os.path.join(UPLOAD_FOLDER, "latest_video.mp4")
FIXED_VIDEO_PATH = os.path.join(UPLOAD_FOLDER, "latest_video_fixed.mp4")
GRAPH_PATH = os.path.join(UPLOAD_FOLDER, "ultrasonic_graph.png")


def cleanup_uploads():
    """Empty the uploads folder when the program terminates."""
    if os.path.exists(UPLOAD_FOLDER):
        # Remove all files in the upload folder
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Error while deleting {file_path}: {e}")


# Register the cleanup function to run when the app shuts down
atexit.register(cleanup_uploads)

# MQTT Configuration
MQTT_BROKER = ""  # Use your MQTT broker
MQTT_PORT = 1883
MQTT_TOPIC_FALL = "fall_detection/status"
MQTT_TOPIC_ULTRASONIC = "sensor/ultrasonic/distance"  # Topic for ultrasonic sensor

# MQTT Client Setup
mqtt_client = mqtt.Client()


def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    # Clear existing subscriptions to prevent duplicates
    client.unsubscribe(MQTT_TOPIC_FALL)
    client.unsubscribe(MQTT_TOPIC_ULTRASONIC)
    # Subscribe to topics
    client.subscribe(MQTT_TOPIC_FALL)
    client.subscribe(MQTT_TOPIC_ULTRASONIC)
    print(f"Subscribed to {MQTT_TOPIC_FALL} and {MQTT_TOPIC_ULTRASONIC}")


# MQTT Callback - When a message is received
def on_message(client, userdata, message):
    global ultrasonic_data, distances, timestamps, last_data_time, graph_image

    topic = message.topic
    payload = message.payload.decode()
    print(f"Received message: {payload} on topic {topic}")

    if topic == MQTT_TOPIC_FALL:
        send_fall_alert_email(recipient_email)

    elif topic == MQTT_TOPIC_ULTRASONIC:
        try:
            # Process ultrasonic sensor data
            distance_value = float(payload)
            current_time = datetime.now()
            ultrasonic_data["distance"] = distance_value
            ultrasonic_data["last_update"] = current_time.strftime("%H:%M:%S")

            # Only record data once per minute
            if last_data_time is None or current_time >= last_data_time + timedelta(minutes=1):
                # Update the last data time
                last_data_time = current_time
                time_str = current_time.strftime("%H:%M")

                # Add new data point
                distances.append(distance_value)
                timestamps.append(time_str)

                # Limit the number of data points
                if len(distances) > max_data_points:
                    distances.pop(0)
                    timestamps.pop(0)

                # Generate new graph
                #generate_graph()

                print(f"Recorded new data point: {distance_value} cm at {time_str}")

        except ValueError as e:
            print(f"Error processing ultrasonic data: {e}")


def generate_graph():
    """Generate a graph from the collected ultrasonic data and save it"""
    global graph_image, distances, timestamps

    if len(distances) == 0:
        return None

    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, distances, marker='o', linestyle='-', color='b')
    plt.title("Ultrasonic Sensor Distance Over Time (1 data point per minute)")
    plt.xlabel("Time")
    plt.ylabel("Distance (cm)")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save to file
    plt.savefig(GRAPH_PATH)

    # Convert plot to a PNG image in memory for API endpoint
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png')
    img_io.seek(0)
    graph_image = base64.b64encode(img_io.getvalue()).decode('utf-8')
    plt.close()

    return graph_image


mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message


# Start MQTT in a separate thread
def run_mqtt():
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_forever()
    except Exception as e:
        print(f"MQTT connection error: {e}")
        time.sleep(5)  # Wait before trying to reconnect


mqtt_thread = threading.Thread(target=run_mqtt)
mqtt_thread.daemon = True
mqtt_thread.start()

# SMTP Configuration
SMTP_SERVER = "smtp.gmail.com"  # Change for other providers
SMTP_PORT = 587
EMAIL_ADDRESS = "viaidashboard@gmail.com"
EMAIL_PASSWORD = ""


@app.route('/')
def index():
    # Check if graph exists
    graph_exists = os.path.exists(GRAPH_PATH)
    graph_url = "/static/uploads/ultrasonic_graph.png" if graph_exists else None

    # Check if video exists
    video_exists = os.path.exists(FIXED_VIDEO_PATH)
    video_url = "/static/uploads/latest_video_fixed.mp4" if video_exists else None

    # Get current distance
    current_distance = ultrasonic_data.get("distance")
    last_update = ultrasonic_data.get("last_update")

    return render_template("index.html",
                           video_url=video_url,
                           graph_url=graph_url,
                           current_distance=current_distance,
                           last_update=last_update)


@app.route('/upload_video', methods=['POST'])
def upload_video():
    video = request.files.get("video")
    if video:
        # Save the uploaded file temporarily
        video.save(VIDEO_PATH)

        # Convert the video using FFmpeg
        convert_video(VIDEO_PATH, FIXED_VIDEO_PATH)

        # Generate the latest graph to ensure it's up to date with the video
        generate_graph()

        return "Video uploaded and converted successfully", 200

    return "No video received", 400


def convert_video(input_path, output_path):
    """Convert video to browser-compatible format using FFmpeg."""
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-vf", "fps=30",
            "-vcodec", "libx264",
            "-acodec", "aac",
            output_path
        ], check=True)
        print("✅ Video conversion successful!")
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error: {e}")


@app.route('/video')
def serve_video():
    if os.path.exists(FIXED_VIDEO_PATH):
        return send_file(FIXED_VIDEO_PATH, mimetype="video/mp4")
    return "No video available", 404


def send_fall_alert_email(recipient_email):
    """Sends an email alert when a fall is detected."""
    subject = "Fall Alert Detected!"
    body = "Your visually impaired family member may have fallen. Please check on them immediately."

    try:
        # Create Email
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Connect to SMTP server and send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, recipient_email, msg.as_string())
        server.quit()

        print(f"Email sent to {recipient_email}")
    except Exception as e:
        print(f"Error sending email: {str(e)}")


# Flask Route to Get the Latest Data
@app.route('/ultrasonic', methods=['GET'])
def get_ultrasonic_data():
    return jsonify(ultrasonic_data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)