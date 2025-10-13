from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from ultralytics import YOLO
import cv2
import numpy as np

app = FastAPI()
model = YOLO("yolov8n.pt")  # downloads YOLO pretrained model

def get_dominant_color(roi):
    roi = cv2.resize(roi, (50, 50))
    roi = roi.reshape((-1, 3))
    avg_color = np.mean(roi, axis=0)
    r, g, b = map(int, avg_color[::-1])  # convert from BGR → RGB
    return (r, g, b)

def generate_frames():
    cap = cv2.VideoCapture(0)  # 0 = webcam
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

                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                # Label position
                text_y = max(y1 - 10, 20)

                # Draw label text
                cv2.putText(frame, label, (x1, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # Draw color swatch rectangle beside label
                color_box_x1 = x1 + 80
                color_box_y1 = text_y - 15
                color_box_x2 = color_box_x1 + 30
                color_box_y2 = color_box_y1 + 20
                cv2.rectangle(frame, (color_box_x1, color_box_y1),
                              (color_box_x2, color_box_y2), color, -1)

                # Draw hex color text beside swatch
                cv2.putText(frame, hex_color, (color_box_x2 + 10, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # Encode the frame for streaming
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
