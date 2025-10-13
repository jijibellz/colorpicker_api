from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from ultralytics import YOLO
import cv2
import numpy as np
import os

app = FastAPI()
model = YOLO("yolov8n.pt")  # downloads YOLO pretrained model

def get_dominant_color(roi):
    roi = cv2.resize(roi, (50, 50))
    roi = roi.reshape((-1, 3))
    avg_color = np.mean(roi, axis=0)
    r, g, b = map(int, avg_color[::-1])  # convert from BGR → RGB
    return (r, g, b)

def generate_frames():
    # If deployed on Render, skip webcam
    if os.environ.get("RENDER", "false").lower() == "true":
        print("⚠️ Webcam not available in Render environment.")
        # You can later make this return a placeholder image or nothing
        while True:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "No Camera Available", (150, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    else:
        cap = cv2.VideoCapture(0)
        while True:
            success, frame = cap.read()
            if not success:
                break

            results = model(frame, verbose=False)
            detections = results[0].boxes.data

            for box in detections:
                x1, y1, x2, y2, conf, cls = box.tolist()
                x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
                roi = frame[y1:y2, x1:x2]

                if roi.size != 0:
                    color = get_dominant_color(roi)
                    label = results[0].names[int(cls)]
                    hex_color = '#%02x%02x%02x' % color

                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, f"{label} {hex_color}", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.get("/")
def root():
    return {"message": "sign to na maggana ung Colorpicker API. punta kayo /video para sa yolo x opencv sample haha"}

@app.get("/video")
def video_feed():
    return StreamingResponse(generate_frames(),
                             media_type="multipart/x-mixed-replace; boundary=frame")
