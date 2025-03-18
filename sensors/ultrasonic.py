import RPi.GPIO as GPIO
import time

# Define GPIO pins
TRIG_PIN = 23  # GPIO pin for Trigger
ECHO_PIN = 24  # GPIO pin for Echo

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

def detect_obstacle():
    """ Measures distance using the ultrasonic sensor. """
    
    # Send a pulse to trigger the sensor
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)  # 10 microseconds
    GPIO.output(TRIG_PIN, False)

    # Wait for Echo pin to go HIGH and measure time
    start_time = time.time()
    while GPIO.input(ECHO_PIN) == 0:
        start_time = time.time()
    
    while GPIO.input(ECHO_PIN) == 1:
        end_time = time.time()
    
    # Calculate distance (Speed of sound = 343m/s)
    time_elapsed = end_time - start_time
    distance_cm = (time_elapsed * 34300) / 2  # Convert to cm

    return round(distance_cm, 2)
