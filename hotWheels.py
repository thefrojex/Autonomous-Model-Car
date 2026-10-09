import pigpio
import os
import time
import curses
from picamera2 import Picamera2
from datetime import datetime
from multiprocessing import Process, Value


# Folder to store images
IMAGE_FOLDER = "road_data/"
ANGLE_LOG = "steering_angles.csv"

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

# Capture images process
def capture_images(angle):
    print("inside the capture image function")
    # num = 0
    camera = Picamera2()
    camera.configure(camera.create_still_configuration())
    camera.start()
    try:
        while True:
            anglo = angle.value
            print("inside capture loop")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{IMAGE_FOLDER}img_{timestamp}_angle_{anglo}.jpg"
            print(filename)
            camera.capture_file(filename)
            print('captured')
            with open(ANGLE_LOG, "a") as log_file:
                log_file.write(f"{timestamp},{angle.value}\n")
            time.sleep(0.5)
            print("Image_captured")
    except KeyboardInterrupt:
        pass
    finally:
        camera.stop()

# Motor control process
def motor_control(speed, angle):
    while True:
        right_speed = speed.value * ((140 - angle.value) / 100)
        left_speed = speed.value * ((angle.value - 40) / 100)
        control_motor1(right_speed, "forward")
        control_motor2(left_speed, "forward")
        time.sleep(0.1)

# Keyboard control process
def keyboard_control(speed, angle):
    def main(stdscr):
        curses.curs_set(0)
        stdscr.nodelay(1)
        stdscr.timeout(100)

        set_servo_angle(angle.value)
        while True:
            key = stdscr.getch()
            if key == curses.KEY_UP and speed.value < 100:
                speed.value += 5
            if key == curses.KEY_DOWN and speed.value >= 10:
                speed.value -= 10
            if key == curses.KEY_RIGHT and angle.value < 140:
                angle.value += 10
                set_servo_angle(angle.value)
            if key == curses.KEY_LEFT and angle.value > 40:
                angle.value -= 10
                set_servo_angle(angle.value)
            

    curses.wrapper(main)

if __name__ == "__main__":
    os.makedirs(IMAGE_FOLDER, exist_ok=True)
    speed = Value("i", 0)
    angle = Value("i", 90)

    image_process = Process(target=capture_images, args=(angle,))
    motor_process = Process(target=motor_control, args=(speed, angle))
    keyboard_process = Process(target=keyboard_control, args=(speed, angle))

    try:
        image_process.start()
        motor_process.start()
        keyboard_process.start()

        keyboard_process.join()
    except KeyboardInterrupt:
        print("Exiting program.")
    finally:
        image_process.terminate()
        motor_process.terminate()
        keyboard_process.terminate()
        pi.set_PWM_dutycycle(EN_A, 0)
        pi.set_PWM_dutycycle(EN_B, 0)
        pi.set_servo_pulsewidth(SERVO_PIN, 0)
        pi.stop()


