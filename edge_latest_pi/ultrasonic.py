import RPi.GPIO as GPIO
import time
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play

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


def speak_obstacle_warning():
    """ Convert text to speech and play it using pydub. """
    # Convert text to speech
    tts = gTTS(text="Obstacle detected ahead!", lang='en')
    # Save the audio to a temporary file
    tts.save("/tmp/obstacle_warning.mp3")

    # Load the mp3 file with pydub
    sound = AudioSegment.from_mp3("/tmp/obstacle_warning.mp3")

    # Play the sound
    play(sound)


if __name__ == "__main__":
    try:
        while True:
            distance = detect_obstacle()
            print(f"Distance: {distance} cm")

            if distance < 30:  # Threshold in cm
                speak_obstacle_warning()  # Play warning sound
            time.sleep(1)  # Delay between measurements

    except KeyboardInterrupt:
        print("Program interrupted. Exiting...")
        GPIO.cleanup()

