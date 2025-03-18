import smbus
import time

bus = smbus.SMBus(1)
ACCEL_ADDR = 0x19
Y_DROP_THRESHOLD = -2000  # Lowered threshold for detecting falls
CONFIRMATION_CHECKS = 2  # Number of consecutive checks to confirm fall
CHECK_INTERVAL = 0.1  # Interval between confirmation checks

# Velocity calculation parameters
VELOCITY_THRESHOLD = 4.0  # Minimum velocity to confirm a real fall
time_step = 0.1  # Time interval for velocity calculation (100ms)

# Movement threshold when stationary (e.g., ignoring small fluctuations)
STATIONARY_THRESHOLD = 500  # This value is a threshold to detect if the user is moving or stationary

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
    x = read_word_2c(ACCEL_ADDR, 0x28 | 0x80)
    y = read_word_2c(ACCEL_ADDR, 0x2A | 0x80)
    z = read_word_2c(ACCEL_ADDR, 0x2C | 0x80)
    return x, y, z

# Initialize accelerometer
time.sleep(2)
try:
    bus.write_byte_data(ACCEL_ADDR, 0x20, 0x27)
    time.sleep(1)
    print("Accelerometer initialized successfully!")
except OSError as e:
    print(f"Error writing to accelerometer: {e}")
    exit()

try:
    who_am_i = bus.read_byte_data(ACCEL_ADDR, 0x0F)
    print(f"WHO_AM_I: 0x{who_am_i:X}")
except OSError as e:
    print(f"Error reading WHO_AM_I: {e}")

# Initial Y-axis value and variables for moving average
_, prev_y, _ = read_accelerometer()
prev_velocity = 0.0
y_values = []  # List to store Y-axis readings for averaging
window_size = 3  # Shortened window size for more responsive smoothing
print(f"Initial Y-axis reading: {prev_y}")

while True:
    time.sleep(time_step)  # Adjust sampling rate (100ms)
    _, curr_y, _ = read_accelerometer()
    
    # Apply moving average to the Y-axis readings
    y_values.append(curr_y)
    smoothed_y = moving_average(y_values, window_size)
    
    delta_y = smoothed_y - prev_y  # Change in Y-axis value
    velocity = delta_y / time_step  # Compute velocity in m/s
    velocity_change = velocity - prev_velocity
    
    print(f"Smoothed Y-axis: {smoothed_y}, Y change: {delta_y}")
    print(f"Velocity change: {velocity_change:.2f} m/s")
    
    # Check if user is stationary and avoid detecting falls when stationary
    if abs(delta_y) < STATIONARY_THRESHOLD and abs(velocity_change) < VELOCITY_THRESHOLD:
        print("User is stationary. Ignoring small movements.")
        prev_y = smoothed_y  # Update for next iteration
        prev_velocity = velocity
        continue  # Skip fall detection checks if stationary
    
    # Check for sudden drop indicating a fall
    if delta_y < Y_DROP_THRESHOLD and abs(velocity_change) > VELOCITY_THRESHOLD:
        print("Possible fall detected. Checking...")
        fall_confirmed = True
        
        for _ in range(CONFIRMATION_CHECKS):  # Check multiple times to confirm
            time.sleep(CHECK_INTERVAL)
            _, check_y, _ = read_accelerometer()
            smoothed_check_y = moving_average(y_values, window_size)
            if abs(smoothed_check_y - smoothed_y) > 1000:  # If Y stabilizes, cancel fall alert
                fall_confirmed = False
                break
        
        if fall_confirmed:
            print("Fall confirmed! Emergency alert!")
            #put the beep beep here
            time.sleep(5)
        else:
            print("False alarm. Just a sudden movement.")
    
    prev_y = smoothed_y  # Update for next iteration
    prev_velocity = velocity
