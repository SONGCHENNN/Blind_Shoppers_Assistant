# Blind_Shoppers_Assistant (Group 12 Documentation)
## Overview

The Blind Shopper Assistance System is an innovative assistive technology designed to help visually impaired individuals navigate shopping environments. The system integrates multiple sensors and detection systems to provide real-time audio feedback about the environment, obstacles, packages, and potential hazards.

The folders are separated into edge_pi which are codes that are used in raspberry pi and dashboard which is implemented using the Flask framework. For raspberry pi main.py is the main code that is needed to run the program, the rest of the python files will be imported to the main python file. 
1. Hardware components and justifications
   
| Hardware           | Justifications|
| ---- | ---- |
| Ultrasonic sensor  | Enables real-time obstacle detection for safe movement  |
| Accelerometer      | Detects falls through motion pattern analysis and send alert to dashboard. | 
| Speaker            | Speak out necessary notification such as objects detected and action required.   | 
| Webcam and mic     | Carry out speech recognition, products detection and text reading.  | 


2. AI Models and justifications
   
| AI Models | Justifications|
| ------------- | ------------- |
| YOLO | Lightweight object detection model used to classify and identify the grocery products in the supermarket. |
| PaddleOCR | Retrieves text information such as expiry date and brand. | 

4. Communication Protocol and Justification
   
| Communication Protocol | Justifications|
| ------------- | ------------- |
| MQTT  | Transmit data for fall detection message and obstacle detection sensor reading. |
| HTTP  | Upload recorded video toflask server. | 
| SMTP | Send email alert to family members in the event the fall is detected  | 

   


## System Architecture

### Core Components

1. **Video Processing**
   - Camera capture and recording
   - Object detection using YOLO
   - OCR for package label scanning

2. **Sensor Integration**
   - Accelerometer for fall detection
   - Ultrasonic sensors for obstacle detection

3. **Communication Systems**
   - MQTT for inter-device communication
   - HTTP for video upload to remote server

4. **User Interface**
   - Voice command recognition
   - Prioritized audio feedback system

## Technical Implementation Details

### Multi-threading Architecture

The system employs a sophisticated multi-threading architecture to handle multiple operations simultaneously without blocking:

- **Main Thread**: Manages the application lifecycle and interfaces with the user
- **Recording Thread**: Handles continuous video capture and annotation
- **YOLO Detection Thread**: Processes frames for object detection
- **Ultrasonic Sensor Thread**: Continuously monitors distances to obstacles
- **Accelerometer Thread**: Monitors motion for fall detection
- **Audio Queue Thread**: Manages and processes prioritized audio messages
- **MQTT Thread**: Listens for fall detection and sensor alerts
- **Command Thread**: Listens for voice commands

This multi-threaded design ensures that critical safety features like obstacle detection and fall alerts operate without interruption while resource-intensive tasks like video processing continue in parallel.

### Priority Queue System

A key innovation in this system is the prioritized audio feedback system implemented using Python's `queue.PriorityQueue`:

- **Priority Levels**:
  - Level 1: Critical safety alerts (fall detection, close obstacles)
  - Level 2: System status updates (start/stop recording)
  - Level 3: Environmental information (object detection)
  - Levels 4-5: Lower priority notifications

- **Queue Management**:
  - Thread-safe implementation ensures messages are properly sequenced
  - Secondary timestamp sorting maintains FIFO order within priority levels
  - Non-blocking queue processing prevents system lockups

### Sensor Integration

#### Ultrasonic Sensor
- Continuously monitors distances to obstacles ahead
- Publishes distance data to MQTT topic
- Triggers high-priority audio alerts when obstacles are within 30cm

#### Accelerometer
- Runs in a daemon thread for continuous monitoring
- Detects falls through motion pattern analysis
- Communicates via MQTT to trigger emergency notifications

### Computer Vision Systems

#### YOLO Object Detection
- Uses a custom-trained YOLO model optimized for package detection
- Provides real-time object identification from camera feed
- Maintains cooldown periods to prevent redundant announcements

#### Optical Character Recognition (OCR)
- Triggered when packages are detected for 20 seconds.
- Scans package labels for relevant information such as brand with context keywords such as produced by: xxx and expiry dates.
- Adds extracted text to audio queue for user notification through the speaker if dates and context keywords are present.

### Communication Protocols

#### MQTT Integration
- Lightweight publish/subscribe messaging system
- Used for inter-device communication about sensor data
- Subscribes to fall detection alerts from external devices

#### HTTP File Transfer
- Uploads recorded video to remote Flask server
- Provides status updates on transfer success/failure

### Voice Control Interface

- Speech recognition using Google's speech-to-text service
- Command vocabulary includes "start" and "stop"
- Audio feedback confirms command recognition

## System Workflow

1. System initializes and announces readiness through a welcome message 
2. User activates recording with voice command "start"
3. Multiple detection systems run in parallel:
   - Object detection identifies items and announces them
   - OCR scans package labels for 20 seconds when YOLO detects label "packages"
   - Ultrasonic sensor monitors for obstacles
   - Accelerometer monitors for falls
4. Audio feedback is prioritized and delivered through the audio queue
5. User can stop the system with voice command "stop"
6. Recorded video is transmitted to a remote server for further analysis

## Error Handling and Robustness

- Thread monitoring ensures critical systems remain operational
- Daemon threads prevent resource leaks on system exit
- Exception handling prevents cascading failures
- Audio feedback informs users of system status and errors

## Future Enhancements

- GPS integration for location-based assistance
- Additional sensor types for more comprehensive environmental awareness
- Machine learning improvements for more accurate object recognition
- Enhanced OCR capabilities for reading diverse package formats

## LiveOCRDetector Documentation

### Overview

The `LiveOCRDetector` is a specialized component of the Blind Shopper Assistance System that provides real-time Optical Character Recognition (OCR) capabilities. It is designed to extract relevant textual information from package labels, focusing on brand information and expiration dates. The component integrates with the system's audio feedback mechanism to provide spoken information about detected packages.

### Key Features

- **Real-time OCR Processing**: Processes video frames to extract text using PaddleOCR
- **Brand Detection**: Uses context keyword analysis to identify brand information
- **Date Recognition**: Employs comprehensive pattern matching to detect various date formats
- **Resource-Efficient Processing**: Implements frame skipping to optimize CPU usage
- **Threaded Operation**: Runs in separate threads to maintain system responsiveness
- **Audio Queue Integration**: Delivers detected information to users through prioritized audio feedback


#### Core Methods

##### Text Processing

The detector includes several methods for processing detected text:

**Keyword-based Text Extraction**
- Identifies and extracts text segments containing brand-related keywords
- Returns extracted brand information or "Unknown Brand" if none found

**Comprehensive Date Filtering**
- Implements multiple regex patterns to identify various date formats
- Supports MM/DD/YYYY, MM-DD-YYYY, YYYY-MM-DD, and expiration date variants
- Returns a list of all detected dates

**OCR Text Processing**
- Coordinates the text extraction workflow
- Combines brand extraction and date filtering
- Returns processed results only when meaningful information is found

##### Frame Processing

The single frame processing method:
- Resizes input frame for optimal OCR performance
- Runs PaddleOCR detection on the frame
- Processes detected text for brand and date information
- Adds new findings to the audio queue for user notification
- Tracks previously detected information to avoid redundant announcements

##### Continuous Detection

The detector supports continuous OCR detection through several methods:

**Continuous Detection Initialization**
- Initiates the continuous OCR detection process
- Takes a frame provider function parameter to source frames
- Launches a daemon thread for background processing

**Detection Loop**
- Implements the main detection loop
- Controls the detection duration (default: 20 seconds)
- Enforces frame rate control to optimize performance
- Handles exceptions and ensures proper state cleanup

**Detection Trigger**
- Provides a public API to initiate OCR detection
- Supports both single-frame and continuous detection modes
- Creates threads for non-blocking operation

### Technical Implementation Details

#### Multi-threading Architecture

The LiveOCRDetector employs a threading approach to ensure OCR operations don't block the main application:

- **Detection Thread**: Runs OCR processing in the background
- **Daemon Thread Design**: Ensures threads terminate properly when the application exits
- **Thread Safety**: Properly handles state variables accessed from multiple threads

#### Resource Optimization

Several techniques are employed to optimize performance:

- **Frame selection**: Only processes every 20th frame
- **Image Resizing**: Reduces image size to 40% of original for faster processing
- **Time-Limited Processing**: Automatically stops detection after a specified duration


#### Pattern Recognition

The system uses sophisticated pattern recognition techniques:

- **Context-Based Brand Detection**: Identifies brand information based on proximity to context keywords
- **Multi-Format Date Recognition**: Recognizes dates in various formats through comprehensive regex patterns
- **Duplicate Detection Prevention**: Tracks previously detected information to avoid redundant announcements

### Integration with Audio System

The detector integrates with the system's audio feedback mechanism:

- Detected information is sent to the audio queue with priority level 3
- Information is formatted in a user-friendly way (e.g., "Package detected. Brand: X. Dates: Y")
- New detections are tracked to prevent redundant announcements

### Usage Examples


#### Continuous Detection

For continuous detection, a frame provider function is defined that returns the current frame from the camera. The continuous detection is then triggered using this frame provider.

### Performance Considerations

- OCR processing is computationally intensive
- Frame rate control is essential for maintaining system responsiveness
- Detection duration should be balanced based on system capabilities
- Consider the impact on battery life for portable implementations

### Experiments

![Quantized ONNX model](/resources/experiment1.png)

Objectness and class logits needed sigmoid activation when calling predictions from the quantized ONNX model.
After applying sigmoid manually, we observed that the model still produced low-confidence (everything is around 0.2500xxx), dense, and inaccurate predictions — with bounding boxes all over the places.
This indicated that the model is likely broken during the ONNX conversion process.
As a result, we reverted to using the original .pt model for reliable detection.


## Step-by-Step Guide in running Flask dashboard interface

```
git clone https://github.com/SONGCHENNN/Blind_Shoppers_Assistant.git
```

```
cd edge_dashboard
```

```
python3 -m venv venv
```

For windows Command Prompt:

```
venv\Scripts\activate
```

```
pip install -r requirements.txt
```
Change this line to your raspberry pi broker IP address
![http_setup](/resources/image2.jpg)
```
python3 app.py
```

## Step-by-Step Guide in running Raspberry pi code
Firstly set up virtual environment for the project in raspberry pi 400
```
sudo apt install python3-venv
python3 -m venv bsaproject
source bsaproject/bin/activate
```
```
git clone https://github.com/SONGCHENNN/Blind_Shoppers_Assistant.git
```

```
cd edge_dashboard
```
Install library for the audio for mic 
```
sudo apt install portaudio19-dev
```
   
Install other libraries from raspberry pi 400
```
pip install -r requirements.txt
```
Set Up MQTT
Install Mosquitto Broker
```
sudo apt install mosquitto
```
Make sure Mosquitto configuration file have this 
```
listener 1883
allow_anonymous true    
```
Start and enable mosquitto by running this command
```
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```
After all the libraries are installed and mosquitto is set up.
Remember to change the code in main.py to your credential: <laptop_ip> to your laptop ip address. This is used to send video file to the dashboard interface running on your laptop IP address. <raspberry_pi_ip> refers to MQTT broker ip address of your raspberry pi to establish a connection to MQTT. 
Change this line to your laptop ip address

![http_setup](/resources/image1.jpg)

Change this line to your raspberry pi broker IP address

![http_setup](/resources/image2.jpg)

To run the main code(the program will be started after this python file is called): 
```
python3 main_final.py
```


