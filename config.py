"""
SmartTrafficAI — Configuration
Edit this file to match your camera setup, zones, and signal timing.
"""

# ─── VIDEO SOURCE ──────────────────────────────────────────────────────────────
VIDEO_SOURCE = r"C:\PRASAD\SKIILS\yolo ml model\Smarttraffic_ai\14552311-hd_1920_1080_50fps.mp4"          # 0 = webcam | "path/to/video.mp4" | "rtsp://..."
FRAME_WIDTH  = 1280
FRAME_HEIGHT = 720
FPS_TARGET   = 30

# ─── YOLO MODEL ────────────────────────────────────────────────────────────────
YOLO_MODEL      = "yolov8n.pt"   # yolov8n (fast) | yolov8s | yolov8m (accurate)
YOLO_CONFIDENCE = 0.45
YOLO_IOU        = 0.45

# COCO class IDs we care about
VEHICLE_CLASSES = {
    2:  "car",
    3:  "motorcycle",
    5:  "bus",
    7:  "truck",
    0:  "person",       # pedestrian
}

EMERGENCY_CLASSES = [2, 5, 7]   # classes that could be emergency vehicles
# A simple heuristic: if bounding box aspect ratio is ~ambulance & high speed → preempt

# ─── LANE / ZONE DEFINITIONS ───────────────────────────────────────────────────
# Each zone is a list of (x, y) polygon vertices in pixel coordinates.
# Adjust these to match your camera's perspective.
# Example: 4-arm intersection, one zone per approach lane.

LANE_ZONES = {
    "North": [(160, 50),  (520, 50),  (520, 340), (160, 340)],
    "South": [(160, 380), (520, 380), (520, 670), (160, 670)],
    "East":  [(560, 180), (880, 180), (880, 540), (560, 540)],
    "West":  [(880, 180), (1200, 180),(1200, 540),(880, 540)],
}

# Counting lines (y-coordinate for horizontal line, x for vertical) per lane
# Format: {"lane_name": ("horizontal"|"vertical", pixel_value)}
COUNT_LINES = {
    "North": ("horizontal", 300),
    "South": ("horizontal", 420),
    "East":  ("vertical",   600),
    "West":  ("vertical",   880),
}

# ─── SPEED ESTIMATION ──────────────────────────────────────────────────────────
# Distance in real-world meters between two reference lines in the camera view
SPEED_CALIB_DISTANCE_M = 10.0    # metres between the two calibration lines
SPEED_CALIB_LINE_1_Y   = 250     # top calibration line (pixels)
SPEED_CALIB_LINE_2_Y   = 450     # bottom calibration line (pixels)
SPEED_LIMIT_KMPH       = 50      # alert threshold

# ─── SIGNAL TIMING ─────────────────────────────────────────────────────────────
MIN_GREEN_SECONDS = 10    # minimum green time (safety lock)
MAX_GREEN_SECONDS = 60    # maximum green time
DEFAULT_GREEN     = 20    # default green time
YELLOW_SECONDS    = 3     # yellow duration
ALL_RED_SECONDS   = 2     # all-red clearance between phases

# Density thresholds for adaptive timing (vehicles per zone)
DENSITY_THRESHOLDS = {
    "low":    (0,  5),    # → min green
    "medium": (5,  15),   # → proportional
    "high":   (15, 999),  # → max green
}

# ─── ANALYTICS & EXPORT ────────────────────────────────────────────────────────
ANALYTICS_INTERVAL_SEC = 60     # compute & save KPIs every N seconds
CSV_OUTPUT_DIR         = "data/logs"
HEATMAP_ALPHA          = 0.4    # overlay transparency

# Level of Service (LOS) thresholds — average delay seconds per vehicle (HCM)
LOS_THRESHOLDS = {
    "A": (0,   10),
    "B": (10,  20),
    "C": (20,  35),
    "D": (35,  55),
    "E": (55,  80),
    "F": (80,  9999),
}

# ─── DASHBOARD ─────────────────────────────────────────────────────────────────
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000
DASHBOARD_DEBUG = False
