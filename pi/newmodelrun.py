import sys
sys.path.append("./tensorflow-env/lib/python3.11/site-packages")
import cv2
import numpy as np
import tensorflow as tf
import multiprocessing as mp
import time
import pigpio
import keyboard  # For detecting arrow key presses
from picamera2 import Picamera2
from multiprocessing import shared_memory

# Servo and motor setup
SERVO_PIN = 18
IN1, IN2, EN_A = 23, 24, 25
IN3, IN4, EN_B = 27, 22, 17

pi = pigpio.pi()
pi.set_mode(SERVO_PIN, pigpio.OUTPUT)
pi.set_mode(IN1, pigpio.OUTPUT)
pi.set_mode(IN2, pigpio.OUTPUT)
pi.set_mode(EN_A, pigpio.OUTPUT)
pi.set_mode(IN3, pigpio.OUTPUT)
pi.set_mode(IN4, pigpio.OUTPUT)
pi.set_mode(EN_B, pigpio.OUTPUT)

# Load trained model
model = tf.keras.models.load_model("my_model.keras")

# Image preprocessing function
def img_preprocess(img):
    img = img[360:, :, :]  # Crop
    img = cv2.cvtColor(img, cv2.COLOR_RGB2YUV)
    img = cv2.GaussianBlur(img, (3, 3), 0)
    img = cv2.resize(img, (200, 66))
    img = img / 255.0
    return img

def capture_images(shared_mem_name, lock):
    """Continuously capture images and store them in shared memory."""
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"format": "RGB888", "size": (480,640)}))
    picam2.start()
    shm = shared_memory.SharedMemory(name=shared_mem_name)
    shared_frame = np.ndarray((640, 480, 3), dtype=np.uint8, buffer=shm.buf)
    
    while True:
        img = picam2.capture_array()
        with lock:
            np.copyto(shared_frame, img)
        time.sleep(0.1)

def preprocess_images(shared_mem_name, shared_processed_name, lock):
    """Preprocess images and store them in shared memory."""
    shm_raw = shared_memory.SharedMemory(name=shared_mem_name)
    shared_frame = np.ndarray((640, 480, 3), dtype=np.uint8, buffer=shm_raw.buf)
    shm_processed = shared_memory.SharedMemory(name=shared_processed_name)
    shared_processed_frame = np.ndarray((66, 200, 3), dtype=np.float32, buffer=shm_processed.buf)
    
    while True:
        with lock:
            processed_img = img_preprocess(shared_frame.copy())
        with lock:
            np.copyto(shared_processed_frame, processed_img)

def predict_steering_angle(shared_processed_name, shared_angle, lock):
    """Predict the steering angle based on shared processed frame."""
    shm_processed = shared_memory.SharedMemory(name=shared_processed_name)
    shared_processed_frame = np.ndarray((66, 200, 3), dtype=np.float32, buffer=shm_processed.buf)
    print('predicting value')
    while True:
        with lock:
            img = np.expand_dims(shared_processed_frame.copy(), axis=0)
        angle = model.predict(img)
        print(angle)
        with lock:
            shared_angle.value = angle
        print('value predicted')

def control_servo_and_motors(shared_angle, speed, lock):
    """Controls the servo and motors based on predicted steering angle."""
    while True:
        if keyboard.is_pressed("up"):
            speed.value = min(speed.value + 5, 100)  # Increase speed
        elif keyboard.is_pressed("down"):
            speed.value = max(speed.value - 5, 0)  # Decrease speed

        with lock:
            steering_angle = shared_angle.value
        print(f"Steering Angle: {steering_angle}, Speed: {speed.value}")

        servo_angle = int(1000 + (steering_angle * 400))  # Scales between 1100 to 1900
        servo_angle = max(1100, min(1900, servo_angle))  # Limit range
        
        pi.set_servo_pulsewidth(SERVO_PIN, servo_angle)  # Send to servo
        print('angle value sent :)')

        right_speed = speed.value * ((140 - steering_angle) / 100)
        left_speed = speed.value * ((steering_angle - 40) / 100)

        control_motor1(right_speed, "forward")
        control_motor2(left_speed, "forward")
        
        time.sleep(0.1)

def control_motor1(speed, direction):
    pi.write(IN1, direction == "forward")
    pi.write(IN2, direction == "backward")
    pi.set_PWM_dutycycle(EN_A, int(speed * 2.55))

def control_motor2(speed, direction):
    pi.write(IN3, direction == "forward")
    pi.write(IN4, direction == "backward")
    pi.set_PWM_dutycycle(EN_B, int(speed * 2.55))

def main():
    """Starts all processes."""
    print("Inside main function")
    shm_frame = shared_memory.SharedMemory(create=True, size=640*480*3, name="shm_frame")
    shm_processed = shared_memory.SharedMemory(create=True, size=66*200*3*4, name="shm_processed")
    shared_angle = mp.Value("d", 0.0)  # Shared steering angle
    speed = mp.Value("i", 20)  # Initial speed at 50
    lock = mp.Lock()

    processes = [
        mp.Process(target=capture_images, args=("shm_frame", lock), daemon=True),
        mp.Process(target=preprocess_images, args=("shm_frame", "shm_processed", lock), daemon=True),
        mp.Process(target=predict_steering_angle, args=("shm_processed", shared_angle, lock), daemon=True),
       # mp.Process(target=control_servo_and_motors, args=(shared_angle, speed, lock), daemon=True),
    ]

    for process in processes:
        process.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pi.set_servo_pulsewidth(SERVO_PIN, 1500)  # Reset servo
        pi.stop()
        shm_frame.close()
        shm_frame.unlink()
        shm_processed.close()
        shm_processed.unlink()
        print("Stopped.")

if __name__ == "__main__":
    main()

