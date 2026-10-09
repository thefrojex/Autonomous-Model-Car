import sys
sys.path.append('/usr/lib/python3/dist-packages')
import libcamera  # Now it should work
import asyncio
import websockets
import base64
import numpy as np
import cv2
from picamera2 import Picamera2
import pigpio
# import keyboard
import time
import os

SERVER_URI = os.environ.get("SERVER_URI")
if not SERVER_URI:
    raise SystemExit("Set SERVER_URI to the laptop WebSocket address, e.g. ws://<laptop-ip>:8000/ws (see .env.example)")


# Pin configuration for L298N Motor Driver
IN1, IN2, EN_A = 23, 24, 25
IN3, IN4, EN_B = 27, 22, 17

# Pin configuration for Servo Motor
SERVO_PIN = 18

# Initialize pigpio
pi = pigpio.pi()
if not pi.connected:
    print("Could not connect to pigpio daemon. Exiting.")
    exit(1)

# Set GPIO modes
pi.set_mode(IN1, pigpio.OUTPUT)
pi.set_mode(IN2, pigpio.OUTPUT)
pi.set_mode(IN3, pigpio.OUTPUT)
pi.set_mode(IN4, pigpio.OUTPUT)
pi.set_PWM_range(EN_A, 255)
pi.set_PWM_range(EN_B, 255)
pi.set_PWM_frequency(EN_A, 100)
pi.set_PWM_frequency(EN_B, 100)

# Function to control servo angle
def set_servo_angle(angle):
    if 40 < angle < 140:
        duty = 500 + (angle * 2000 // 180)
        pi.set_servo_pulsewidth(SERVO_PIN, duty)
        time.sleep(0.1)

# Functions to control motors
def control_motor1(speed, direction):
    pi.write(IN1, direction == "forward")
    pi.write(IN2, direction == "backward")
    pi.set_PWM_dutycycle(EN_A, int(speed * 2.55))

def control_motor2(speed, direction):
    pi.write(IN3, direction == "forward")
    pi.write(IN4, direction == "backward")
    pi.set_PWM_dutycycle(EN_B, int(speed * 2.55))

def motor_control(speed, angle):
    right_speed = speed * ((140 - angle) / 100)
    left_speed = speed * ((angle - 40) / 100)
    control_motor1(right_speed, "forward")
    control_motor2(left_speed, "forward")
    time.sleep(0.1)


picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)}))
picam2.start()

uri = SERVER_URI

async def send_image():
    async with websockets.connect(uri) as websocket:
        while True:
            img = picam2.capture_array()
            img = img[360:, :, :]  # Crop the top 360 pixels

            _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            img_base64 = base64.b64encode(buffer).decode('utf-8')

            await websocket.send(img_base64)
            response = await websocket.recv()

            steering, speed = map(float, response.split(","))
            print(f"Received: Steering={steering}, Speed={speed}")
            set_servo_angle(steering)
            motor_control(speed, steering)
try:
    asyncio.run(send_image())   

finally:
    picam2.stop()
    pi.set_PWM_dutycycle(EN_A, 0)
    pi.set_PWM_dutycycle(EN_B, 0)
    pi.set_servo_pulsewidth(SERVO_PIN, 0)
    pi.stop()