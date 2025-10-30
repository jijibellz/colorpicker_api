from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
import cv2
import numpy as np
import os
from sklearn.cluster import KMeans
import webcolors

# === FastAPI setup ===
app = FastAPI(title="🎨 YOLO Color Picker API")

# === CORS setup ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # local dev
        "https://colorpickerjiji.onrender.com",  # deployed frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Load YOLO model ===
try:
    model = YOLO("yolov8n.pt")
    print("✅ YOLOv8 model loaded successfully.")
except Exception as e:
    print(f"⚠️ Error loading YOLO model: {e}")
    model = None


# === Helper functions ===
def rgb_to_name(rgb_tuple):
    """Convert RGB to nearest web color name."""
    try:
        return webcolors.rgb_to_name(rgb_tuple)
    except ValueError:
        min_colors = {}
        for name, hex_code in webcolors.HTML4_NAMES_TO_HEX.items():
            r_c, g_c, b_c = webcolors.hex_to_rgb(hex_code)
            rd = (r_c - rgb_tuple[0]) ** 2
            gd = (g_c - rgb_tuple[1]) ** 2
            bd = (b_c - rgb_tuple[2]) ** 2
            min_colors[(rd + gd + bd)] = name
        return min_colors[min(min_colors.keys())]


def get_top_colors(roi, n_colors=3):
    """Return top N dominant colors in region using KMeans."""
    roi = cv2.resize(roi, (100, 100))
    roi = roi.reshape((-1, 3))
    kmeans = KMeans(n_clusters=n_colors, n_init=5, random_state=0)
    kmeans.fit(roi)
    colors = kmeans.cluster_centers_.astype(int)
    return [tuple(map(int, color[::-1])) for color in colors]  # BGR → RGB


# === API routes ===
@app.get("/")
def root():
    return {"message": "🎨 YOLO Color Picker (Snapshot Mode) is live!"}


@app.post("/analyze")
async def analyze_frame(file: UploadFile = File(...)):
    """
    Accepts one image frame, analyzes colors + objects, and returns JSON.
    """
    try:
        contents = await file.read()
        np_arr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # Scene-wide color detection
        scene_colors = get_top_colors(frame, 3)
        color_info = [
            {
                "rgb": color,
                "hex": f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}",
                "name": rgb_to_name(color),
            }
            for color in scene_colors
        ]

        # Object detection
        objects = []
        if model:
            results = model(frame, verbose=False)
            detections = results[0].boxes.data
            for box in detections:
                x1, y1, x2, y2, conf, cls = box.tolist()
                x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
                roi = frame[y1:y2, x1:x2]
                if roi.size == 0:
                    continue
                top_colors = get_top_colors(roi, 3)
                main_color = top_colors[0]
                label = results[0].names[int(cls)]
                objects.append({
                    "object": label,
                    "confidence": round(float(conf), 2),
                    "main_color": {
                        "rgb": main_color,
                        "hex": f"#{main_color[0]:02x}{main_color[1]:02x}{main_color[2]:02x}",
                        "name": rgb_to_name(main_color)
                    },
                })

        return {"scene_colors": color_info, "objects": objects}

    except Exception as e:
        return {"error": str(e)}
