import cv2
import time
import requests

# Flask server URL
flask_server_url = "http://<laptop_ip>:5000/upload_video"

# Video filename
mp4_filename = "/home/qunzhen/video.mp4"

# Initialize the camera
cap = cv2.VideoCapture(0)  # Use the default camera (Pi Camera)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 24)

# Video writer setup
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for MP4
out = cv2.VideoWriter(mp4_filename, fourcc, 24, (640, 480))

print("Recording video for 30 seconds...")
start_time = time.time()

while time.time() - start_time < 30:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break
# Release resources
cap.release()
out.release()
print("Recording complete.")

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

