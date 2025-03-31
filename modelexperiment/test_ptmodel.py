import cv2
from ultralytics import YOLO

# Load YOLOv8 model
model = YOLO("best_fp16.pt")  # Replace with your actual path

# Initialize video capture (0 = Default Webcam)
cap = cv2.VideoCapture(0)

# Check if the webcam is accessible
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

# Main loop
while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to capture frame.")
        break

    # Perform object detection
    results = model.predict(frame, conf=0.5)
    print(results)
    # Post-process predictions to ignore tiny detections
    if results and results[0].boxes is not None:
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0]  # Bounding box coordinates
            area = (x2 - x1) * (y2 - y1)

            if area >= 2000:
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)

    # Draw bounding boxes and labels on the frame
    annotated_frame = results[0].plot()

    # Display the result
    cv2.imshow('YOLOv8 Real-Time Detection', annotated_frame)

    # Exit on 'Q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release webcam and close OpenCV window
cap.release()
cv2.destroyAllWindows()
