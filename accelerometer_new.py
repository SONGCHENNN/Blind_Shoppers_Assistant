import smbus
import time
import paho.mqtt.client as mqtt
import logging
import os


# Configure logging
def setup_logging(log_level=logging.INFO):
    """Configure logging for the accelerometer module"""
    logger = logging.getLogger('accelerometer')
    logger.setLevel(log_level)

    # Create file handler that logs to a file
    log_dir = os.path.expanduser('~/logs')
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(f"{log_dir}/accelerometer.log")
    file_handler.setLevel(log_level)

    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)

    return logger


# MQTT Configuration
MQTT_BROKER = "<raspberry_pi_ip>"  # You can use your own broker address
MQTT_PORT = 1883  # Default MQTT port
MQTT_TOPIC = "fall_detection/status"  # Topic to publish fall status

# Create an MQTT client
mqtt_client = mqtt.Client()

# Accelerometer Configuration
bus = smbus.SMBus(1)
ACCEL_ADDR = 0x19
Y_DROP_THRESHOLD = -2000  # Lowered threshold for detecting falls
CONFIRMATION_CHECKS = 2  # Number of consecutive checks to confirm fall
CHECK_INTERVAL = 0.1  # Interval between confirmation checks

# Velocity calculation parameters
VELOCITY_THRESHOLD = 4.0  # Minimum velocity to confirm a real fall
time_step = 0.1  # Time interval for velocity calculation (100ms)


# Moving Average Filter
def moving_average(data, window_size=3):  # Shortened window size for faster response
    if len(data) < window_size:
        return sum(data) / len(data)
    return sum(data[-window_size:]) / window_size


def read_word_2c(addr, reg):
    """Read two bytes and convert to a signed 16-bit integer."""
    low = bus.read_byte_data(addr, reg)
    high = bus.read_byte_data(addr, reg + 1)
    val = (high << 8) + low
    return val if val < 32768 else val - 65536


def read_accelerometer():
    """Read X, Y, and Z axis data from accelerometer."""
    try:
        x = read_word_2c(ACCEL_ADDR, 0x28 | 0x80)
        y = read_word_2c(ACCEL_ADDR, 0x2A | 0x80)
        z = read_word_2c(ACCEL_ADDR, 0x2C | 0x80)
        return x, y, z
    except Exception as e:
        logger.error(f"Error reading accelerometer: {e}")
        return 0, 0, 0  # Return default values on error


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT Broker!")
    else:
        logger.error(f"Failed to connect, return code {rc}")


def send_mqtt_message(message):
    """Send a message to the MQTT broker."""
    try:
        if mqtt_client.is_connected():
            result = mqtt_client.publish(MQTT_TOPIC, message)
            status = result.rc  # Check the return code
            if status == 0:
                logger.info(f"Published message: {message}")
            else:
                logger.error(f"Failed to publish message: {message}, Return Code: {status}")
        else:
            logger.warning("MQTT client is not connected. Retrying connection...")
            mqtt_client.reconnect()
    except Exception as e:
        logger.error(f"Error publishing to MQTT: {e}")


def run_accelerometer(verbose=False):
    """Main function to run accelerometer fall detection."""
    # Set up logging based on verbosity
    global logger
    log_level = logging.DEBUG if verbose else logging.INFO
    logger = setup_logging(log_level)

    # Configure MQTT
    mqtt_client.on_connect = on_connect
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
    mqtt_client.loop_start()

    # Initialize accelerometer
    time.sleep(2)
    try:
        bus.write_byte_data(ACCEL_ADDR, 0x20, 0x27)
        time.sleep(1)
        logger.info("Accelerometer initialized successfully!")
    except OSError as e:
        logger.critical(f"Error writing to accelerometer: {e}")
        return

    try:
        who_am_i = bus.read_byte_data(ACCEL_ADDR, 0x0F)
        logger.info(f"WHO_AM_I: 0x{who_am_i:X}")
    except OSError as e:
        logger.error(f"Error reading WHO_AM_I: {e}")

    # Initial Y-axis value and variables for moving average
    _, prev_y, _ = read_accelerometer()
    prev_velocity = 0.0
    y_values = []  # List to store Y-axis readings for averaging
    window_size = 3  # Shortened window size for more responsive smoothing
    logger.info(f"Initial Y-axis reading: {prev_y}")

    while True:
        time.sleep(time_step)  # Adjust sampling rate (100ms)
        _, curr_y, _ = read_accelerometer()

        # Apply moving average to the Y-axis readings
        y_values.append(curr_y)
        smoothed_y = moving_average(y_values, window_size)

        delta_y = smoothed_y - prev_y  # Change in Y-axis value
        velocity = delta_y / time_step  # Compute velocity in m/s
        velocity_change = velocity - prev_velocity

        # Only log these if verbose is True
        logger.debug(f"Smoothed Y-axis: {smoothed_y}, Y change: {delta_y}")
        logger.debug(f"Velocity change: {velocity_change:.2f} m/s")

        # Check for sudden drop indicating a fall
        if delta_y < Y_DROP_THRESHOLD and abs(velocity_change) > VELOCITY_THRESHOLD:
            logger.info("Possible fall detected. Checking...")
            fall_confirmed = True

            for _ in range(CONFIRMATION_CHECKS):  # Check multiple times to confirm
                time.sleep(CHECK_INTERVAL)
                _, check_y, _ = read_accelerometer()
                smoothed_check_y = moving_average(y_values, window_size)
                if abs(smoothed_check_y - smoothed_y) > 1000:  # If Y stabilizes, cancel fall alert
                    fall_confirmed = False
                    break

            if fall_confirmed:
                logger.warning("Fall confirmed! Sending emergency alert!")
                send_mqtt_message("Fall detected!")
                time.sleep(5)  # Prevent spamming messages
            else:
                logger.info("False alarm. Just a sudden movement.")

        prev_y = smoothed_y  # Update for next iteration
        prev_velocity = velocity


# Only run if executed directly
if __name__ == "__main__":
    run_accelerometer(verbose=True)
