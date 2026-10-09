from fastapi import FastAPI, WebSocket
import numpy as np
import cv2
import base64
import tensorflow as tf
from keras.models import Sequential, load_model
import uvicorn
import keyboard
import os
import time
from pathlib import Path

def img_preprocess(img):
    # img = img[360:,:,:]
    img = cv2.cvtColor(img, cv2.COLOR_RGB2YUV)
    img = cv2.GaussianBlur(img,  (3, 3), 0)
    img = cv2.resize(img, (200, 66))
    img = img/255
    # print(img.shape)
    return img
MODEL_PATH = os.environ.get(
    "MODEL_PATH", str(Path(__file__).resolve().parent / "Models" / "new_kaggle_model3.keras")
)
model = load_model(MODEL_PATH)
app = FastAPI()
frame = 0
preprocessed_image =0
test_image = 0
speed = 0

def keyboard_control(speed):
    # while True:
    if keyboard.is_pressed('up') and speed < 100:
        speed += 5
        print(f"Speed increased: {speed}")
    
    if keyboard.is_pressed('down') and speed >= 10:
        speed -= 10
        print(f"Speed decreased: {speed}")
    time.sleep(0.01)
    return speed


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected")

    try:
        while True:
            data = await websocket.receive_text()  # Receive Base64 image
            img_data = base64.b64decode(data)  # Decode the image

            # Convert to OpenCV format
            np_arr = np.frombuffer(img_data, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            original_image = frame
            preprocessed_image = img_preprocess(original_image)

            input_data = np.expand_dims(preprocessed_image, axis=0)

            prediction = model.predict(input_data)

            angle_mapping = [-30, -20, -10, 0, 10, 20, 30, 40]
            predicted_index = np.argmax(prediction)
            predicted_angle = angle_mapping[predicted_index]
            # predicted_angle = prediction[0][0]
            # predicted_angle = predicted_angle * 40


            global speed
            speed = keyboard_control(speed)
            steering_angle = predicted_angle  # Replace with model prediction
            # speed = 0.5  # Replace with dynamic speed

            # Send control data
            await websocket.send_text(f"{steering_angle},{speed}")
            print(f"Sent: Steering={steering_angle}, Speed={speed}")


    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Client disconnected")
        if frame is not None:
            # cv2.imwrite('output_image6.jpg', frame)
            # cv2.imwrite('output_image6.1.jpg', preprocessed_image)
            # cv2.imwrite("Received Image", original_image)
            # cv2.imwrite("Received Image1", preprocessed_image)
            cv2.waitKey(1)  # Required to update OpenCV window

if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8000)
