# Blind_Shoppers_Assistant (Group 12 Documentation)
The folders are separated into edge_pi which are codes that are used in raspberry pi and dashboard which is implemented using the Flask framework. For raspberry pi main.py is the main code that is needed to run the program, the rest of the python files will be imported to the main python file. 
1. Hardware components and justifications
   
| Hardware           | Justifications|
| ---- | ---- |
| Ultrasonic sensor  | Content Cell  |
| Accelerometer      | Content Cell  | 
| Speaker            | Content Cell  | 
| Webcam and mic     | Content Cell  | 


2. AI Models and justifications
   
| AI Models | Justifications|
| ------------- | ------------- |
| YOLO | Content Cell  |
| PaddleOCR | Content Cell  | 

4. Communication Protocol and Justification
   
| Communication Protocol | Justifications|
| ------------- | ------------- |
| MQTT  | Content Cell  |
| HTTP  | Content Cell  | 

   
5. Software components and justification
6. Step-by-Step Guide in running Flask dashboard interface

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

```
python3 app.py
```

7. Step-by-Step Guide in running Raspberry pi code
Firstly set up virtual environment for the project in raspberry pi 400
```
sudo apt install python3-venv
python3 -m venv bsaproject
source bsaproject/bin/activate
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

To run the main code(the program will be started after this python file is called): 
```
python3 main.py
```


