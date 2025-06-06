import cv2
import numpy as np
import time
import re
import threading
import queue
from paddleocr import PaddleOCR


class LiveOCRDetector:
    def __init__(self, audio_queue=None):
        """
        Initialize Live OCR Detector

        :param audio_queue: Queue for passing detected text to audio output
        """
        # Context Keywords for Brand Detection
        self.BRAND_CONTEXT_KEYWORDS = [
            'brand', 'company', 'product', 'manufactured',
            'made by', 'produced', 'trademark'
        ]

        # Initialize PaddleOCR
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            show_log=False
        )

        # Audio queue for text-to-speech
        self.audio_queue = audio_queue

        # OCR detection state
        self.is_detecting = False
        self.detection_start_time = None
        self.detection_duration = 20  # 20 seconds of detection

        # Frame processing rate - process every 20th frame
        self.frame_counter = 0
        self.process_frame_rate = 20

        # Keep track of detected brands and dates to avoid repetition
        self.detected_brands = set()
        self.detected_dates = set()

    def keyword_based_text_extraction(self, text):
        """
        Extract full text segments containing context keywords
        """
        lower_text = text.lower()

        found_segments = []

        for keyword in self.BRAND_CONTEXT_KEYWORDS:
            if keyword in lower_text:
                lines = text.split('\n')

                keyword_lines = [
                    line for line in lines
                    if keyword in line.lower()
                ]

                found_segments.extend(keyword_lines)

        if found_segments:
            return "\n".join(found_segments)

        return "Unknown Brand"

    def comprehensive_date_filter(self, text):
        """
        Comprehensive date extraction with multiple formats
        """
        date_patterns = [
            r'\b\d{2}/\d{2}/\d{4}\b',  # MM/DD/YYYY
            r'\b\d{2}-\d{2}-\d{4}\b',  # MM-DD-YYYY
            r'\bEXP(?:IRATION)?:?\s*\d{2}/\d{2}/\d{4}\b',  # Expiration formats
            r'\b(?:EXP|EXPIRES?):\s*\d{1,2}[/.-]\d{1,2}[/.-]\d{4}\b',  # More expiration variations
            r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
        ]

        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)

        return dates if dates else []

    def process_ocr_text(self, text):
        """
        Process OCR text with comprehensive extraction and date filtering
        """
        print(f"Processing OCR text: {text}")  # Debug print

        if not text.strip():
            print("No text detected")  # Debug print
            return None, []

        try:
            # Extract text based on context keywords
            extracted_text = self.keyword_based_text_extraction(text)

            # Extract dates
            detected_dates = self.comprehensive_date_filter(text)

            print(f"Extracted Text: {extracted_text}")  # Debug print
            print(f"Detected Dates: {detected_dates}")  # Debug print

            # Only return results if text and dates are meaningful
            if extracted_text != "Unknown Brand" and detected_dates:
                return extracted_text, detected_dates

            return None, []

        except Exception as e:
            print(f"Error in process_ocr_text: {e}")  # Debug print
            return None, []

    def process_single_frame(self, frame):
        """Process a single frame for OCR"""
        print("Processing single frame for OCR...")  # Debug print

        # Resize for performance
        scale_percent = 40
        width = int(frame.shape[1] * scale_percent / 100)
        height = int(frame.shape[0] * scale_percent / 100)
        resized_frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

        # Run OCR
        results = self.ocr.ocr(resized_frame, cls=True)

        # Collect detected text
        detected_text = ""
        if results and results[0]:
            for result in results[0]:
                detected_text += result[1][0] + "\n"

        # Process text
        extracted_text, detected_dates = self.process_ocr_text(detected_text.strip())

        # If meaningful text is detected, add to audio queue
        if extracted_text and detected_dates:
            # Add new brands and dates to our tracking sets
            is_new_brand = extracted_text not in self.detected_brands
            new_dates = [date for date in detected_dates if date not in self.detected_dates]

            if is_new_brand or new_dates:
                self.detected_brands.add(extracted_text)
                self.detected_dates.update(detected_dates)

                full_text = f"Package detected. Brand: {extracted_text}. Dates: {', '.join(detected_dates)}"
                print(f"OCR Detection Result: {full_text}")  # Debug print

                # Put text in audio queue if available
                if self.audio_queue:
                    self.audio_queue.put((3, time.time(), full_text))

        return extracted_text, detected_dates

    def start_continuous_detection(self, frame_provider):
        """
        Start continuous OCR detection for a certain duration

        :param frame_provider: Function that returns the current frame when called
        """
        if self.is_detecting:
            print("OCR detection already in progress")
            return

        self.is_detecting = True
        self.detection_start_time = time.time()
        self.frame_counter = 0
        self.detected_brands = set()
        self.detected_dates = set()

        print(f"Starting continuous OCR detection for {self.detection_duration} seconds")
        detection_thread = threading.Thread(target=lambda: self._continuous_detection_loop(frame_provider))
        detection_thread.daemon = True
        detection_thread.start()

    def _continuous_detection_loop(self, frame_provider):
        """
        Continuously process frames for OCR for the specified duration

        :param frame_provider: Function that returns the current frame when called
        """
        try:
            while self.is_detecting:
                # Check if we've reached the time limit
                current_time = time.time()
                elapsed_time = current_time - self.detection_start_time

                if elapsed_time >= self.detection_duration:
                    print(f"OCR detection completed after {elapsed_time:.2f} seconds")
                    self.is_detecting = False
                    break

                # Get the current frame from the provider function
                frame = frame_provider()
                if frame is None:
                    print("No frame available for OCR processing")
                    time.sleep(0.1)
                    continue

                # Increment frame counter
                self.frame_counter += 1

                # Only process every Nth frame to save resources
                if self.frame_counter % self.process_frame_rate == 0:
                    print(f"Processing frame {self.frame_counter} (elapsed time: {elapsed_time:.2f}s)")
                    self.process_single_frame(frame)

                # Small delay to prevent CPU overuse
                time.sleep(0.01)

        except Exception as e:
            print(f"Error in continuous OCR detection: {e}")
        finally:
            self.is_detecting = False
            print("OCR detection stopped")

    def trigger_ocr_detection(self, frame=None, frame_provider=None):
        """
        Trigger OCR detection - either process a single frame or start continuous detection

        :param frame: Single frame to process (for backward compatibility)
        :param frame_provider: Function to get frames for continuous detection
        """
        print("Trigger OCR detection called")  # Debug print

        if frame_provider:
            # Start continuous detection
            self.start_continuous_detection(frame_provider)
        elif frame is not None:
            # Process just a single frame (old behavior)
            print("Processing provided single frame")
            detection_thread = threading.Thread(target=lambda: self.process_single_frame(frame))
            detection_thread.daemon = True
            detection_thread.start()
        else:
            print("Error: No frame or frame provider specified for OCR detection")
