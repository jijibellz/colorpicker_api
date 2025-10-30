# === main.py ===
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("webrtc")
logger.setLevel(logging.DEBUG)

import cv2
import numpy as np
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from ultralytics import YOLO
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaBlackhole
from av import VideoFrame
import webcolors

# === FastAPI setup ===
app = FastAPI(title="🎨 YOLO + Color Picker (WebRTC Edition)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5175",
        "https://colorpickerjiji.onrender.com",
        "https://colorpickernijiji.onrender.com",
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
            min_colors[rd + gd + bd] = name
        return min_colors[min(min_colors.keys())]

def get_top_colors(roi, n_colors=3):
    try:
        if roi.size == 0:
            return [(255, 255, 255)] * n_colors
        roi_resized = cv2.resize(roi, (100, 100))
        pixels = roi_resized.reshape((-1, 3))
        unique, counts = np.unique(pixels, axis=0, return_counts=True)
        sorted_indices = np.argsort(-counts)
        colors = []
        for i in range(min(n_colors, len(sorted_indices))):
            b, g, r = unique[sorted_indices[i]]
            colors.append((int(r), int(g), int(b)))
        return colors
    except Exception:
        return [(255, 255, 255)] * n_colors

def draw_color_palette(frame, colors, start_x, start_y):
    for i, color in enumerate(colors):
        if color is None or len(color) != 3:
            continue
        r, g, b = [int(c) for c in color]
        hex_code = f"#{r:02x}{g:02x}{b:02x}"
        try:
            name = rgb_to_name((r, g, b))
        except Exception:
            name = "Unknown"
        y_pos = start_y + i * 25
        try:
            cv2.rectangle(frame, (start_x, y_pos), (start_x + 20, y_pos + 20), (b, g, r), -1)
            cv2.putText(frame, f"{name} {hex_code}", (start_x + 30, y_pos + 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        except Exception as e:
            print("⚠️ draw_color_palette error:", e)

# === Video Processor ===
class VideoProcessor(VideoStreamTrack):
    def __init__(self, track, skip_frames=2):
        super().__init__()
        self.track = track
        self.frame_count = 0
        self.skip_frames = skip_frames
        self.last_results = None

    async def recv(self):
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")
        self.frame_count += 1

        # Scene colors
        try:
            scene_colors = get_top_colors(img, 3)
            cv2.putText(img, "Scene Colors:", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            draw_color_palette(img, scene_colors, 10, 40)
        except Exception as e:
            print("⚠️ Scene color error:", e)

        # Object detection
        try:
            results = None
            if model and self.frame_count % self.skip_frames == 0:
                results = model(img, verbose=False)
                self.last_results = results[0].boxes.data

            if self.last_results is not None:
                for box in self.last_results:
                    x1, y1, x2, y2, conf, cls = box.tolist()
                    x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
                    roi = img[y1:y2, x1:x2]
                    if roi.size == 0:
                        continue
                    top_color = get_top_colors(roi, 1)[0]
                    bgr = (top_color[2], top_color[1], top_color[0])
                    label = results[0].names[int(cls)] if results else "Object"
                    cv2.rectangle(img, (x1, y1), (x2, y2), bgr, 2)
                    cv2.putText(img, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, bgr, 2)
        except Exception as e:
            print("⚠️ Object detection error:", e)

        new_frame = VideoFrame.from_ndarray(img, format="bgr24")
        new_frame.pts = frame.pts
        new_frame.time_base = frame.time_base
        return new_frame

# === WebRTC Signaling ===
pcs = set()

@app.post("/offer")
async def offer(request: Request):
    """Handle WebRTC POST offers."""
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    pc = RTCPeerConnection()
    pcs.add(pc)
    print("📡 New WebRTC connection")

    @pc.on("iceconnectionstatechange")
    async def on_ice_state_change():
        print("❄️ ICE connection state:", pc.iceConnectionState)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("🔄 Connection state:", pc.connectionState)
        if pc.connectionState in ["failed", "closed", "disconnected"]:
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track):
        print("🎥 Track received:", track.kind)
        if track.kind == "video":
            pc.addTrack(VideoProcessor(track))
        else:
            pc.addTrack(MediaBlackhole())

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    print("📨 SDP answer created successfully")
    return JSONResponse(
        {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    )

@app.get("/offer")
def offer_get():
    """Return a friendly message if someone does GET /offer"""
    return PlainTextResponse("🚀 Please POST a WebRTC offer to this endpoint.")

@app.get("/")
def home():
    return {"message": "🎨 YOLO + Color Picker WebRTC backend is running!"}

@app.on_event("shutdown")
async def on_shutdown():
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()
