# main.py
import cv2
import numpy as np
import asyncio
import os
import json
import webcolors
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from ultralytics import YOLO
from sklearn.cluster import KMeans
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaBlackhole
from av import VideoFrame

# === FastAPI setup ===
app = FastAPI(title="🎨 YOLO + Color Picker (WebRTC Edition)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175", "https://colorpickerjiji.onrender.com"],
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


# === Color Utilities ===
def rgb_to_name(rgb_tuple):
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
    roi = cv2.resize(roi, (100, 100))
    roi = roi.reshape((-1, 3))
    kmeans = KMeans(n_clusters=n_colors, n_init=5, random_state=0)
    kmeans.fit(roi)
    colors = kmeans.cluster_centers_.astype(int)
    return [tuple(map(int, color[::-1])) for color in colors]  # BGR → RGB


def draw_color_palette(frame, colors, start_x, start_y):
    for i, color in enumerate(colors):
        r, g, b = color
        hex_code = f"#{r:02x}{g:02x}{b:02x}"
        name = rgb_to_name((r, g, b))
        y_pos = start_y + i * 25

        cv2.rectangle(frame, (start_x, y_pos), (start_x + 20, y_pos + 20), (b, g, r), -1)
        cv2.putText(frame, f"{name} {hex_code}", (start_x + 30, y_pos + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)


# === WebRTC Video Processing ===
class VideoProcessor(VideoStreamTrack):
    """Processes each video frame for YOLO + color detection."""

    def __init__(self, track):
        super().__init__()
        self.track = track

    async def recv(self):
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")

        # Scene color detection
        scene_colors = get_top_colors(img, 3)
        cv2.putText(img, "Scene Colors:", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        draw_color_palette(img, scene_colors, 10, 40)

        # Object detection
        if model:
            results = model(img, verbose=False)
            detections = results[0].boxes.data
            for box in detections:
                x1, y1, x2, y2, conf, cls = box.tolist()
                x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
                roi = img[y1:y2, x1:x2]
                if roi.size == 0:
                    continue

                top_colors = get_top_colors(roi, 3)
                label = results[0].names[int(cls)]
                main_color = top_colors[0]
                bgr = (main_color[2], main_color[1], main_color[0])

                cv2.rectangle(img, (x1, y1), (x2, y2), bgr, 2)
                cv2.putText(img, f"{label}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, bgr, 2)
                draw_color_palette(img, top_colors, x2 + 10, y1)

        new_frame = VideoFrame.from_ndarray(img, format="bgr24")
        new_frame.pts = frame.pts
        new_frame.time_base = frame.time_base
        return new_frame


# === WebRTC Signaling Routes ===
pcs = set()


@app.post("/offer")
async def offer(request: Request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pcs.add(pc)
    print("📡 New WebRTC connection")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("🔄 Connection state:", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track):
        print("🎥 Track received:", track.kind)
        if track.kind == "video":
            local_video = VideoProcessor(track)
            pc.addTrack(local_video)
        else:
            pc.addTrack(MediaBlackhole())

    # Set remote description and create answer
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return JSONResponse(
        {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    )


@app.get("/")
def home():
    return {"message": "🎨 YOLO + Color Picker WebRTC backend is running!"}


# === Run Cleanup ===
@app.on_event("shutdown")
async def on_shutdown():
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()
