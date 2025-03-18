import time
from sensors.ultrasonic import detect_obstacle
from sensors.accelerometer import detect_fall
from sensors.camera import capture_frame
from models.ocr import run_ocr
from models.food_freshness import check_freshness
from utils.alert import send_alert
from utils.database import log_event

def main():
    print("Starting system...")

    while True:
        print("\n--- Running Sensor & AI Tasks ---")

        # 1️⃣ Check Fall Detection
        if detect_fall():
            send_alert("⚠️ Fall detected! Alerting family...")
            log_event("Fall detected", "critical")

        # 2️⃣ Check Obstacle Detection (Ultrasonic Sensor)
        distance = detect_obstacle()
        if distance < 30:  # Threshold in cm
            send_alert("🚧 Obstacle detected ahead!")

        # 3️⃣ Capture Image from Camera
        frame = capture_frame()
        if frame is not None:
            print("📷 Image Captured! Processing...")

            # 4️⃣ Process Image with AI Models
            is_packaged = True  # Example logic to differentiate food types
            if is_packaged:
                text = run_ocr(frame)
                print(f"📝 OCR Detected Text: {text}")
                log_event(f"OCR Text: {text}")
            else:
                freshness_score = check_freshness(frame)
                print(f"🥗 Food Freshness Score: {freshness_score}")
                log_event(f"Food Freshness Score: {freshness_score}")

        # 5️⃣ Wait before next iteration (avoid CPU overload)
        time.sleep(2)

if __name__ == "__main__":
    main()
