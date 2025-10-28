from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from ultralytics import YOLO
import cv2
import numpy as np
import os
from sklearn.cluster import KMeans
import webcolors

app = FastAPI()
model = YOLO("yolov8n.pt")  # YOLOv8 pretrained model

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:5173"] if you want stricter
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Utility functions ===

def rgb_to_name(rgb_tuple):
    try:
        # Try direct match (if the color is exact)
        return webcolors.rgb_to_name(rgb_tuple)
    except ValueError:
        # If not exact, find closest color
        min_colors = {}
        for name, hex_code in webcolors.HTML4_NAMES_TO_HEX.items():
            r_c, g_c, b_c = webcolors.hex_to_rgb(hex_code)
            rd = (r_c - rgb_tuple[0]) ** 2
            gd = (g_c - rgb_tuple[1]) ** 2
            bd = (b_c - rgb_tuple[2]) ** 2
            min_colors[(rd + gd + bd)] = name
        return min_colors[min(min_colors.keys())]



def get_top_colors(roi, n_colors=3):
    """Return top N dominant colors (RGB tuples) from a region using KMeans."""
    roi = cv2.resize(roi, (100, 100))
    roi = roi.reshape((-1, 3))

    kmeans = KMeans(n_clusters=n_colors, n_init=5, random_state=0)
    kmeans.fit(roi)
    colors = kmeans.cluster_centers_.astype(int)

    # Convert BGR → RGB for consistency
    return [tuple(map(int, color[::-1])) for color in colors]


def draw_color_palette(frame, colors, start_x, start_y):
    """Draw color swatches with hex + name beside object."""
    for i, color in enumerate(colors):
        r, g, b = color
        hex_code = '#%02x%02x%02x' % (r, g, b)
        name = rgb_to_name((r, g, b))
        box_y = start_y + i * 25

        # Draw colored rectangle
        cv2.rectangle(frame, (start_x, box_y), (start_x + 20, box_y + 20), (b, g, r), -1)
        # Write color name + hex
        cv2.putText(frame, f"{name} {hex_code}", (start_x + 30, box_y + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)


# === Streaming video generator ===

def generate_frames():
    # If deployed on Render (no webcam available)
    if os.environ.get("RENDER", "false").lower() == "true":
        print("⚠️ Webcam not available in Render environment.")
        while True:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "No Camera Available", (150, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    else:
        cap = cv2.VideoCapture(0)
        while True:
            success, frame = cap.read()
            if not success:
                break

            # === Global (scene) color detection ===
            scene_colors = get_top_colors(frame, 3)
            cv2.putText(frame, "Scene Colors:", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            draw_color_palette(frame, scene_colors, 10, 40)

            # === YOLO object detection ===
            results = model(frame, verbose=False)
            detections = results[0].boxes.data

            for box in detections:
                x1, y1, x2, y2, conf, cls = box.tolist()
                x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
                roi = frame[y1:y2, x1:x2]

                if roi.size == 0:
                    continue

                # Get top 3 colors for each detected object
                top_colors = get_top_colors(roi, 3)
                label = results[0].names[int(cls)]

                # Pick the most dominant color for the box outline
                main_color = top_colors[0]
                bgr_color = (main_color[2], main_color[1], main_color[0])

                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), bgr_color, 2)
                cv2.putText(frame, f"{label}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, bgr_color, 2)

                # Draw color swatches beside bounding box
                draw_color_palette(frame, top_colors, x2 + 10, y1)

            # Encode frame for streaming
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


# === FastAPI Routes ===

@app.get("/")
def root():
    return {
        "message": "🎨 YOLO Color Picker 2.0 is running! Visit /video to see live detection with color shades!"
    }


@app.get("/video")
def video_feed():
    return StreamingResponse(generate_frames(),
                             media_type="multipart/x-mixed-replace; boundary=frame")
