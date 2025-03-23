import cv2
from ultralytics import YOLO
import threading
import time


class YOLODetector:
    def __init__(self, model_path="/home/qunzhen/try/models/best.pt", conf_threshold=0.5, min_area=2000):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.min_area = min_area
        self.is_running = False
        self.detection_thread = None
        self.stop_flag = False

        # For display purposes (optional)
        self.current_frame = None
        self.annotated_frame = None

    def process_frame(self, frame):
        """Process a single frame with the YOLO model and return the annotated frame"""
        if frame is None:
            return None

        # Perform object detection
        results = self.model.predict(frame, conf=self.conf_threshold)

        # Store the raw results for potential further processing
        self.latest_results = results

        # Filter out tiny detections
        filtered_boxes = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0]  # Bounding box coordinates
            area = (x2 - x1) * (y2 - y1)

            if area >= self.min_area:
                filtered_boxes.append((int(x1), int(y1), int(x2), int(y2), box.conf[0], int(box.cls[0])))
                # Draw this box on the frame
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)

        # Get the annotated frame from YOLO
        annotated_frame = results[0].plot()

        return annotated_frame, filtered_boxes

    def start_detection(self, cap, display=False):
        """Start detection in a separate thread"""
        if self.is_running:
            return

        self.stop_flag = False
        self.is_running = True
        self.detection_thread = threading.Thread(
            target=self._detection_loop,
            args=(cap, display),
            daemon=True
        )
        self.detection_thread.start()

    def stop_detection(self):
        """Stop the detection thread"""
        self.stop_flag = True
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=2)
        self.is_running = False

    def _detection_loop(self, cap, display=False):
        """Main detection loop running in a separate thread"""
        try:
            while not self.stop_flag:
                ret, frame = cap.read()
                if not ret:
                    print("Failed to grab frame in YOLO detection")
                    time.sleep(0.1)
                    continue

                # Process the frame with YOLO
                self.current_frame = frame.copy()
                self.annotated_frame, detections = self.process_frame(frame)

                # Debug information about detections
                if detections:
                    print(f"Detected {len(detections)} objects")

                # Display the result if requested
                if display and self.annotated_frame is not None:
                    cv2.imshow('YOLOv8 Detection', self.annotated_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

        except Exception as e:
            print(f"Error in YOLO detection thread: {e}")
        finally:
            self.is_running = False
            if display:
                cv2.destroyAllWindows()
            print("YOLO detection stopped")

    def get_latest_frame(self):
        """Get the latest annotated frame"""
        return self.annotated_frame if self.annotated_frame is not None else self.current_frame


# For standalone testing
if __name__ == "__main__":
    # Initialize video capture
    cap = cv2.VideoCapture(0)

    # Check if the webcam is accessible
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        exit()

    # Create the detector
    detector = YOLODetector()

    # Start detection with display
    detector.start_detection(cap, display=True)

    try:
        # Keep the main thread running
        while detector.is_running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        # Clean up
        detector.stop_detection()
        cap.release()
        cv2.destroyAllWindows()
