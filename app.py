from flask import Flask, request, jsonify, Response, send_file, make_response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import pigpio
import requests
import RPi.GPIO as GPIO
import time
import io
import os
from picamera2 import Picamera2, Preview
from libcamera import Transform
import cv2
import logging
import json
from threading import Lock
from random import random
from datetime import datetime
from subprocess import run
import base64

thread = None
thread_lock = Lock()

app = Flask(__name__)
CORS(app, resources={r"*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")


@app.route('/api/test', methods=['GET'])
def test_endpoint():
    response_data = {'message': 'This is a test endpoint.'}
    return jsonify(response_data)

# ----------------------    MOTOR CONTROL     ------------------------------

class MotorControl:
    # Constants for motor pins
    RIGHT_MOTOR_PINS = (6, 5)  # IN1, IN2
    LEFT_MOTOR_PINS = (23, 24)  # IN3, IN4
    
    PWM_FREQ = 50
    PWM_RANGE = 4095
        
    def __init__(self):
        self.motor_servo = pigpio.pi()
        # Set up motor pins
        for pin in self.LEFT_MOTOR_PINS + self.RIGHT_MOTOR_PINS:
            self.motor_servo.set_mode(pin, pigpio.OUTPUT)
            self.motor_servo.set_PWM_frequency(pin, self.PWM_FREQ)
            self.motor_servo.set_PWM_range(pin, self.PWM_RANGE)
            
    def turn_left(self, duty):
        self.motor_servo.set_PWM_dutycycle(self.LEFT_MOTOR_PINS[0], 0)
        self.motor_servo.set_PWM_dutycycle(self.LEFT_MOTOR_PINS[1], duty)
        
        self.motor_servo.set_PWM_dutycycle(self.RIGHT_MOTOR_PINS[0],abs(duty))
        self.motor_servo.set_PWM_dutycycle(self.RIGHT_MOTOR_PINS[1],0)
        
    def turn_right(self, duty):
        self.motor_servo.set_PWM_dutycycle(self.LEFT_MOTOR_PINS[0], abs(duty))
        self.motor_servo.set_PWM_dutycycle(self.LEFT_MOTOR_PINS[1], 0)
        
        self.motor_servo.set_PWM_dutycycle(self.RIGHT_MOTOR_PINS[0],0)
        self.motor_servo.set_PWM_dutycycle(self.RIGHT_MOTOR_PINS[1],duty)
        
    def run_backward(self, duty):
        self.motor_servo.set_PWM_dutycycle(self.LEFT_MOTOR_PINS[0],0)
        self.motor_servo.set_PWM_dutycycle(self.LEFT_MOTOR_PINS[1],duty)
            
        self.motor_servo.set_PWM_dutycycle(self.RIGHT_MOTOR_PINS[0],0)
        self.motor_servo.set_PWM_dutycycle(self.RIGHT_MOTOR_PINS[1],duty) 
    
    def run_forward(self, duty):
        self.motor_servo.set_PWM_dutycycle(self.LEFT_MOTOR_PINS[0],abs(duty))
        self.motor_servo.set_PWM_dutycycle(self.LEFT_MOTOR_PINS[1],0)
            
        self.motor_servo.set_PWM_dutycycle(self.RIGHT_MOTOR_PINS[0], abs(duty))
        self.motor_servo.set_PWM_dutycycle(self.RIGHT_MOTOR_PINS[1], 0)
        
    def stop_motors(self):
        for pin in self.LEFT_MOTOR_PINS + self.RIGHT_MOTOR_PINS:
            self.motor_servo.set_PWM_dutycycle(pin, 0)
            
    def __del__(self):
        # Clean up pigpio resources
        self.stop_motors()
        self.motor_servo.stop()

motor_controller = MotorControl()

@app.route('/api/motor-control', methods=['POST'])
def motor_control():
    action = request.json.get('action', '')
    duty_cycle = 2000

    if action == 'forward':
        motor_controller.run_forward(duty_cycle)
    elif action == 'backward':
        motor_controller.run_backward(duty_cycle)
    elif action == 'left':
        motor_controller.turn_left(duty_cycle)
    elif action == 'right':
        motor_controller.turn_right(duty_cycle)
    elif action == 'stop':
        motor_controller.stop_motors()
    else:
        return jsonify({'error': 'Invalid action'}), 400

    # time.sleep(0.1)
    # motor_controller.stop_motors()
    
    return jsonify({'result': 'success'})


# --------------------  CLAW CONTROLLER   ------------------------------------
            
            
class ClawControl:
    # Constants for motor pins
    CLAW_PIN1 = 7
    CLAW_PIN2 = 8
    CLAW_PIN3 = 25
    
    PWM_FREQ = 50
    PWM_RANGE = 4000
    
    CLAW_HANDLER_MAX_VALUE = 140
    CLAW_HANDLER_MIN_VALUE = 90
    
    CLAW_MAX_VALUE = 150
    CLAW_MIN_VALUE = 90
        
    def __init__(self):
        self.claw_servo = pigpio.pi()
        
        self.claw_servo.set_mode(self.CLAW_PIN1, pigpio.OUTPUT)
        self.claw_servo.set_mode(self.CLAW_PIN2, pigpio.OUTPUT)
        self.claw_servo.set_mode(self.CLAW_PIN3, pigpio.OUTPUT)
        
        self.claw_servo.set_PWM_frequency(self.CLAW_PIN1, self.PWM_FREQ)
        self.claw_servo.set_PWM_frequency(self.CLAW_PIN2, self.PWM_FREQ)
        self.claw_servo.set_PWM_frequency(self.CLAW_PIN3, self.PWM_FREQ)
        
        self.claw_servo.set_PWM_range(self.CLAW_PIN1, self.PWM_RANGE)
        self.claw_servo.set_PWM_range(self.CLAW_PIN2, self.PWM_RANGE)
        self.claw_servo.set_PWM_range(self.CLAW_PIN3, self.PWM_RANGE)
        
        self.initClaw()
        
    def angle_range(self, channel, init_angle):
        if channel=='0':
            if init_angle<90 :
                init_angle=90
            elif init_angle>150 :
                init_angle=150
            else:
                init_angle=init_angle
        elif channel=='1':
            if init_angle<90 :
                init_angle=90
            elif init_angle>150 :
                init_angle=150
            else:
                init_angle=init_angle
        elif channel=='2':
            if init_angle<0 :
                init_angle=0
            elif init_angle>180 :
                init_angle=180
            else:
                init_angle=init_angle
        return init_angle
    
    def setServoPwm(self,channel,angle):
        if channel=='0':
            angle=int(self.angle_range('0',angle))
            self.claw_servo.set_PWM_dutycycle(self.CLAW_PIN1,80+(400/180)*angle)
        elif channel=='1':
            angle=int(self.angle_range('1',angle))
            self.claw_servo.set_PWM_dutycycle(self.CLAW_PIN2,80+(400/180)*angle)
        elif channel=='2':
            angle=int(self.angle_range('2',angle))
            self.claw_servo.set_PWM_dutycycle(self.CLAW_PIN3,80+(400/180)*angle)
            
    def raiseClaw(self):
        if (self.currentClawHandlerValue >= self.CLAW_HANDLER_MAX_VALUE):
            self.currentClawHandlerValue = self.CLAW_HANDLER_MAX_VALUE
            return
        
        self.currentClawHandlerValue+=1
        self.setServoPwm('1', self.currentClawHandlerValue)
    
    def lowerClaw(self):
        if (self.currentClawHandlerValue <= self.CLAW_HANDLER_MIN_VALUE):
            self.currentClawHandlerValue = self.CLAW_HANDLER_MIN_VALUE
            return
        
        self.currentClawHandlerValue-=1
        self.setServoPwm('1', self.currentClawHandlerValue)
    
    def squeezeClaw(self):
        if (self.currentClawValue <= self.CLAW_MIN_VALUE):
            self.currentClawValue = self.CLAW_MIN_VALUE
            return
        
        self.currentClawValue-=1
        self.setServoPwm('0', self.currentClawValue)
    
    def unsqueezeClaw(self):
        if (self.currentClawValue >= self.CLAW_MAX_VALUE):
            self.currentClawValue = self.CLAW_MAX_VALUE
            return
        
        self.currentClawValue+=1
        self.setServoPwm('0', self.currentClawValue)
            
    def initClaw(self):
        self.setServoPwm('1',self.CLAW_HANDLER_MAX_VALUE)
        time.sleep(0.01)
            
        self.setServoPwm('0', self.CLAW_MAX_VALUE)
        time.sleep(0.01)
            
        self.currentClawHandlerValue = self.CLAW_HANDLER_MAX_VALUE
        self.currentClawValue = self.CLAW_MAX_VALUE
            
    def __del__(self):
        # Clean up pigpio resources
        self.initClaw()
        
claw_controller = ClawControl()     

@app.route('/api/claw-control', methods=['GET'])
def init_claw():
    claw_controller.initClaw()
    data = {
        "clawMaxValue": claw_controller.CLAW_MAX_VALUE, 
        "clawMinValue": claw_controller.CLAW_MIN_VALUE,
        "clawCurrentValue": claw_controller.currentClawValue,
        "clawHandlerMaxValue": claw_controller.CLAW_HANDLER_MAX_VALUE,
        "clawHandlerMinValue": claw_controller.CLAW_HANDLER_MIN_VALUE,
        "clawHandlerCurrentValue": claw_controller.currentClawHandlerValue
        }
    
    return jsonify({'result': 'success', 'data' : data})


@app.route('/api/claw-control', methods=['POST'])
def claw_control():
    data = request.get_json()
    model = data['model']
    clawCurrentValue = model['clawCurrentValue']
    clawHandlerCurrentValue = model['clawHandlerCurrentValue']
    
    if clawHandlerCurrentValue is not None and clawHandlerCurrentValue != claw_controller.currentClawHandlerValue:
        step = 1 if clawHandlerCurrentValue > claw_controller.currentClawHandlerValue else -1
        for i in range(claw_controller.currentClawHandlerValue, clawHandlerCurrentValue, step):
            claw_controller.setServoPwm('1', i)
            time.sleep(0.01)
        claw_controller.currentClawHandlerValue = clawHandlerCurrentValue
        
    if clawCurrentValue is not None and clawCurrentValue != claw_controller.currentClawValue:
        step = 1 if clawCurrentValue > claw_controller.currentClawValue else -1
        for i in range(claw_controller.currentClawValue, clawCurrentValue, step):
            claw_controller.setServoPwm('0', i)
            time.sleep(0.01)
        claw_controller.currentClawValue = clawCurrentValue
    
    return jsonify({'result': 'success', 'data' : model})
       

# ------------------- DISTANCE CONTROL ---------------------------------

class UltrasonicSensorControl:
    
    TRIGGER_PIN = 27
    ECHO_PIN = 22
    MAX_DISTANCE = 300  # define the maximum measuring distance, unit: cm
    
    def __init__(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.TRIGGER_PIN, GPIO.OUT)
        GPIO.setup(self.ECHO_PIN, GPIO.IN)
        
        self.timeOut = self.MAX_DISTANCE*60 
        
    def pulseIn(self, pin, level, timeOut): # obtain pulse time of a pin under timeOut
        t0 = time.time()
        while(GPIO.input(pin) != level):
            if((time.time() - t0) > timeOut*0.000001):
                return 0;
        t0 = time.time()
        while(GPIO.input(pin) == level):
            if((time.time() - t0) > timeOut*0.000001):
                return 0;
        pulseTime = (time.time() - t0)*1000000
        return pulseTime
    
    def get_distance(self):     # get the measurement results of ultrasonic module,with unit: cm
        distance_cm2=[0.0,0.0,0.0,0.0,0.0]
        for i in range(5):
            GPIO.output(self.TRIGGER_PIN, GPIO.HIGH)      # make trigger_pin output 10us HIGH level 
            time.sleep(0.00001)     # 10us
            GPIO.output(self.TRIGGER_PIN,GPIO.LOW) # make trigger_pin output LOW level 
            pingTime = self.pulseIn(self.ECHO_PIN, GPIO.HIGH, self.timeOut)   # read plus time of echo_pin
            distance_cm2[i] = pingTime * 340.0 / 2.0 / 10000.0     # calculate distance with sound speed 340m/s
        
        distance_cm2=sorted(distance_cm2)
        
        return  distance_cm2[2]
    
    def get_distance_in_cm(self):
        return int(self.get_distance())
    
    
ultrasonic_sensor_controller = UltrasonicSensorControl()

# @socketio.on('connect')
# def handle_connect():
#     print('Client connected')
#     while True:
#         distance = ultrasonic_sensor_controller.get_distance_in_cm()
#         print(distance)
#         emit('distance_update', {'distance': distance})
#         time.sleep(0.5)

# ------------------- SOCKET io ---------------------------------


"""
Get current date time
"""
def get_current_datetime():
    now = datetime.now()
    return now.strftime("%m/%d/%Y %H:%M:%S")

"""
Send the current distance data
"""
def distance_collector_thread():
    while True:
        distance = ultrasonic_sensor_controller.get_distance_in_cm()
        #print(distance)
        socketio.emit("distance_update",{'distance':distance})
        socketio.sleep(1)

@socketio.on("connect")
def connected():
    global thread
    print('Client connected')

    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(distance_collector_thread)

@socketio.on("disconnect")
def disconnected():
    """event listener when client disconnects to the server"""
    print("user disconnected")
    

# ------------------- AUTONOMOUS DRIVING ---------------------------------

# class AutomaticDriverController(Thread):
    
#     DUTY_CYCLE = 2000
#     DETECTED_OBJECT_DISTANCE_THRESHOLD_CM = 14
        
#     def __init__(self, claw_controller: Type[ClawControl], motor_controller: Type[MotorControl], ultrasonic_sensor_controller: Type[UltrasonicSensorControl]):
#         super().__init__()
#         self.task_running = False
#         self.claw_controller = claw_controller
#         self.motor_controller = motor_controller
#         self.ultrasonic_sensor_controller = ultrasonic_sensor_controller
    
#     def run(self):
#         self.task_running = True
#         # Do some work for 1 minute or until task_running is False
#         if not self.task_running:
#                 print('Task stopped')
#                 return
            
#         self.bypass_object()
            
#         for i in range(60):
#             motor_controller.run_forward(self.DUTY_CYCLE)
#             if (self.ultrasonic_sensor_controller.get_distance_in_cm() <= self.DETECTED_OBJECT_DISTANCE_THRESHOLD_CM):
#                 self.bypass_object()
                
#             time.sleep(0.5)

#         # Set the task_running variable to False to indicate that the task has completed
#         self.task_running = False
#         print('Task complete!')
        
#     def bypass_object(self):
#         detected_object_distance_cm = self.ultrasonic_sensor_controller.get_distance_in_cm()
#         while (detected_object_distance_cm <= self.DETECTED_OBJECT_DISTANCE_THRESHOLD_CM):
#             self.motor_controller.run_backward(self.DUTY_CYCLE)
#             self.motor_controller.turn_right(self.DUTY_CYCLE)
#             time.sleep(0.5)
#             self.motor_controller.stop_motors()
#             time.sleep(0.5)
#             detected_object_distance_cm = self.ultrasonic_sensor_controller.get_distance_in_cm()
        

    
# automatic_driver_controller = AutomaticDriverController(claw_controller, motor_controller, ultrasonic_sensor_controller)

# @app.route('/api/auto-drive/start', methods=['GET'])
# def auto_drive_start():
#     if automatic_driver_controller.task_running:
#         return jsonify({'message': 'Task is already running'})

#     # Start the background task
#     automatic_driver_controller.start()

#     # Return a response to the client immediately
#     return jsonify({'message': 'Task started successfully'})
    
# @app.route('/api/auto-drive/stop', methods=['GET'])
# def auto_drive_stop():
#     if not automatic_driver_controller.task_running:
#         return jsonify({'message': 'Task is not currently running'})

#     # Stop the background task
#     automatic_driver_controller.task_running = False

#     # Return a response to the client immediately
#     return jsonify({'message': 'Task stopped successfully'})
# ------------------- VIDEO CONTROL ---------------------------------

@app.route('/video')
def video_feed():
    # Initialize the camera and set up the video stream
    camera = cv2.VideoCapture(0)
    stream = camera.read()

    # Define the MIME type of the video stream
    response = Response(
        stream,
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

    # Set the frame rate of the video stream
    response.headers['X-Content-Duration'] = str(1.0 / 30.0)
    return response

# -------------------   CAMERA CONTROL --------------------------------------

images_folder = 'new_images'
"""
Captures image and save it to the `images` folder
"""
@app.route('/api/image', methods=['GET'])
def capture_image():
    # Check if the directory exists
    if not os.path.exists(images_folder):
        # If it doesn't exist, create it
        os.makedirs(images_folder)
    
    # Generate a unique filename for the image
    i = 1
    while os.path.exists(f"{images_folder}/{i}.jpg"):
        i += 1
    filename = f"{i}.jpg"
    file_path = f"{images_folder}/{filename}"

    # Initialize the camera
    picam2 = Picamera2()
    camera_config = picam2.create_still_configuration(main={"size": (256, 256)}, lores={"size": (256, 256)}, display="lores", transform=Transform(hflip=1, vflip=1))
    picam2.configure(camera_config)
    picam2.start()

    time.sleep(0.5)
    # Capture the image
    metadata = picam2.capture_file(file_path)
    print(metadata)

    # Clean up
    picam2.close()

    # Send the image file to the client app
    image_path = os.path.join(os.getcwd(), file_path)
    
     # Encode the image as base64
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    # Return the image data and filename
    post_data = {
        'imageData': image_data,
        'fileName': filename
    }

    # Send the POST request to the API
    # response = requests.post('http://localhost:7200/detect', json=post_data)

    # # Check the response from the API
    # if response.status_code == 200:
    #     print('Image sent successfully.')
    # else:
    #     print('Failed to send image.')

    # Return the image data and filename
    return post_data
    
    # Set the cache-control header to prevent caching
    # response = make_response(send_file(image_path, mimetype="image/jpeg"))
    # response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    # response.headers["Pragma"] = "no-cache"
    # response.headers["Expires"] = "0"

    # return response, {'fileName': filename}
    # return send_file(image_path, mimetype='image/jpg', attachment_filename=filename)

@app.route('/api/detect/yolov5', methods=['POST'])
def detect_object_yolov():
    detected_img_result_folder_path = "result_detect"
    # Get image filename from request
    data = request.get_json()
    image_name = data.get('fileName')

    image_path = f'{images_folder}/{image_name}'
    print(image_path)
    if not os.path.exists(image_path):
        return jsonify({'error': f'Image {image_name} not found'}), 404

    # Check if result_detect/ directory exists and delete it if it does
    if os.path.exists(f'{detected_img_result_folder_path}/'):
        os.system(f'rm -r {detected_img_result_folder_path}/')

    # Run detection command
    command = f"python neural_networks/yolov5/detect.py --weights best.pt --source {image_path} --conf 0.4 --project result_detect/"
    os.system(command)

    # Return detected image to client
    detected_image_path = f'{detected_img_result_folder_path}/exp/' + image_name
    
    # Encode the image as base64
    with open(detected_image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    # Return the image data and filename
    return {
        'imageData': image_data,
        'fileName': image_name
    }
    
    # response = send_file(detected_image_path, mimetype='image/jpeg')
    # response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    # return response
# --------------------------------------------------------
            
if __name__ == '__main__':
    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    finally:
        del motor_controller
        del claw_controller
