import os
import subprocess
from flask import Flask, render_template, request, send_file
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
MQTT_BROKER = "<raspberry_pi_ip>"  # Use your MQTT broker
MQTT_PORT = 1883
MQTT_TOPIC = "fall_detection/status"

# MQTT Client Setup
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    client.subscribe(MQTT_TOPIC)


# MQTT Callback - When a message is received
def on_message(client, userdata, message):
    print(f"Received message: {message.payload.decode()} on topic {message.topic}")
    send_fall_alert_email(recipient_email)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)

# Start MQTT in a separate thread
def run_mqtt():
    mqtt_client.loop_forever()

mqtt_thread = threading.Thread(target=run_mqtt)
mqtt_thread.daemon = True
mqtt_thread.start()
#end of mqtt

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
    global distances
    if len(distances) == 0:
        return "No data to plot"

    # Plot the ultrasonic distance data
    plt.figure(figsize=(8, 4))
    plt.plot(distances, marker='o', linestyle='-', color='b')
    plt.title("Ultrasonic Sensor Distance Over Time")
    plt.xlabel("Time")
    plt.ylabel("Distance (cm)")
    plt.grid(True)

    # Convert plot to a PNG image in memory
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png')
    img_io.seek(0)
    img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')  # Convert to base64 string
    plt.close()

    # Embed the image in an HTML page
    html = render_template_string('''
        <html>
            <body>
                <h1>Ultrasonic Sensor Data Plot</h1>
                <img src="data:image/png;base64,{{ img_base64 }}" alt="Ultrasonic Data Plot"/>
            </body>
        </html>
    ''', img_base64=img_base64)

    return html
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
