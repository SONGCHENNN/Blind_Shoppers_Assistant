import os
import subprocess
from flask import Flask, render_template, request, send_file
from flask import render_template_string
import atexit
import shutil
import matplotlib.pyplot as plt
import io
import base64

#email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

#accelerometer
import threading
import paho.mqtt.client as mqtt
import json

#ultrasonic
ultrasonic_data = {"distance": None}
distances = []  # List to store historical distances for plotting
timestamps = []  # List to store timestamps for x-axis
max_data_points = 50  # Maximum number of data points to store

# Global variable to store recipient email
recipient_email = "chinqz042@gmail.com"  # Replace with a dynamic value

# Store accelerometer data
#accel_data = {"x": 0, "y": 0, "z": 0}
# Store the latest ultrasonic sensor data
ultrasonic_data = {"distance": None}
distances = []  # List to store historical distances for plotting

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
VIDEO_PATH = os.path.join(UPLOAD_FOLDER, "latest_video.mp4")
FIXED_VIDEO_PATH = os.path.join(UPLOAD_FOLDER, "latest_video_fixed.mp4")  # New fixed file
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
MQTT_BROKER = "<pi_ip>"  # Use your MQTT broker
MQTT_PORT = 1883
MQTT_TOPIC_FALL = "fall_detection/status"
MQTT_TOPIC_ULTRASONIC = "sensor/ultrasonic/distance"  # Topic for ultrasonic sensor

# MQTT Client Setup
mqtt_client = mqtt.Client()


def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    client.subscribe(MQTT_TOPIC_FALL)
    client.subscribe(MQTT_TOPIC_ULTRASONIC)  # Subscribe to ultrasonic data
    print(f"Subscribed to {MQTT_TOPIC_FALL} and {MQTT_TOPIC_ULTRASONIC}")


# MQTT Callback - When a message is received
def on_message(client, userdata, message):
    global ultrasonic_data, distances, timestamps

    topic = message.topic
    payload = message.payload.decode()
    print(f"Received message: {payload} on topic {topic}")

    if topic == MQTT_TOPIC_FALL:
        send_fall_alert_email(recipient_email)

    elif topic == MQTT_TOPIC_ULTRASONIC:
        try:
            # Process ultrasonic sensor data
            distance_value = float(payload)
            ultrasonic_data["distance"] = distance_value

            # Store historical data for plotting
            import time
            current_time = time.strftime("%H:%M:%S")

            # Add new data point
            distances.append(distance_value)
            timestamps.append(current_time)

            # Limit the number of data points
            if len(distances) > max_data_points:
                distances.pop(0)
                timestamps.pop(0)

            print(f"Updated ultrasonic data: {distance_value} cm")
        except ValueError as e:
            print(f"Error processing ultrasonic data: {e}")


mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)


# Start MQTT in a separate thread
def run_mqtt():
    mqtt_client.loop_forever()


mqtt_thread = threading.Thread(target=run_mqtt)
mqtt_thread.daemon = True
mqtt_thread.start()
# end of mqtt

# SMTP Configuration
SMTP_SERVER = "smtp.gmail.com"  # Change for other providers
SMTP_PORT = 587
EMAIL_ADDRESS = "viaidashboard@gmail.com"
EMAIL_PASSWORD = ""

@app.route('/')
def index():
    return render_template("index.html", video_url="/static/uploads/latest_video_fixed.mp4")  # Use fixed video

@app.route('/upload_video', methods=['POST'])
def upload_video():
    video = request.files.get("video")
    if video:
        # Save the uploaded file temporarily
        video.save(VIDEO_PATH)

        # Convert the video using FFmpeg
        convert_video(VIDEO_PATH, FIXED_VIDEO_PATH)

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
@app.route('/send_email', methods=['POST'])
def send_email():
    recipient_email = request.form.get("email")
    subject = "Fall alert"
    body = "Your visually impaired family member might have fall down while doing grocery shopping based on our data. Please check on them."

    if not recipient_email:
        return "Recipient email is required", 400

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
        return f"Email sent to {recipient_email}", 200
    except Exception as e:
        return f"Error sending email: {str(e)}", 500


# Flask Route to Get the Latest Data
@app.route('/ultrasonic', methods=['GET'])
def get_ultrasonic_data():
    return jsonify(ultrasonic_data)


# Flask Route to Plot the Graph
@app.route('/plot', methods=['GET'])
def plot_graph():
    global distances, timestamps
    if len(distances) == 0:
        return "No data to plot"

    # Plot the ultrasonic distance data
    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, distances, marker='o', linestyle='-', color='b')
    plt.title("Ultrasonic Sensor Distance Over Time")
    plt.xlabel("Time")
    plt.ylabel("Distance (cm)")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Convert plot to a PNG image in memory
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png')
    img_io.seek(0)
    img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')  # Convert to base64 string
    plt.close()

    # Embed the image in an HTML page
    html = render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ultrasonic Sensor Data</title>
            <meta http-equiv="refresh" content="5">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    text-align: center;
                }
                .container {
                    max-width: 1000px;
                    margin: 0 auto;
                }
                .current-reading {
                    font-size: 24px;
                    margin: 20px 0;
                    padding: 10px;
                    background-color: #f0f0f0;
                    border-radius: 5px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Ultrasonic Sensor Data Monitor</h1>

                <div class="current-reading">
                    Current Distance: <strong>{{ current_distance }}</strong> cm
                </div>

                <div class="plot">
                    <img src="data:image/png;base64,{{ img_base64 }}" alt="Ultrasonic Data Plot" width="100%"/>
                </div>

                <p><small>This page refreshes automatically every 5 seconds</small></p>
            </div>
        </body>
        </html>
    ''', img_base64=img_base64, current_distance=ultrasonic_data["distance"])

    return html
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
