"""
Configuration settings for the Proctoring AI System
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOGS_DIR = os.path.join(DATA_DIR, 'logs')
RECORDINGS_DIR = os.path.join(DATA_DIR, 'recordings')
MODELS_DIR = os.path.join(BASE_DIR, 'models')

# Create directories if they don't exist
for dir_path in [DATA_DIR, LOGS_DIR, RECORDINGS_DIR, MODELS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Camera settings
CAMERA_ID = 0  # Default camera
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

# Face detection settings
FACE_DETECTION_INTERVAL = 5  # frames
FACE_RECOGNITION_ENABLED = True
MULTIPLE_FACES_THRESHOLD = 1  # Alert if more than 1 face detected
FACE_LOOK_AWAY_THRESHOLD = 30  # seconds

# Object detection settings
OBJECT_DETECTION_INTERVAL = 10  # frames
YOLO_MODEL_PATH = os.path.join(MODELS_DIR, 'yolov8n.pt')
SUSPICIOUS_OBJECTS = ['cell phone', 'laptop', 'book', 'remote']

# Audio settings
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_DURATION = 5  # seconds per audio chunk
AUDIO_THRESHOLD = 0.1  # Voice activity threshold
MULTIPLE_VOICES_THRESHOLD = 2  # Alert if more than 2 voices detected

# Alert thresholds
ALERT_LEVELS = {
    'INFO': 1,
    'WARNING': 2,
    'CRITICAL': 3
}

# Decision engine settings
DECISION_INTERVAL = 2  # seconds
SUSPICIOUS_SCORE_THRESHOLD = 0.7
ALERT_COOLDOWN = 10  # seconds between same type alerts

# Database settings
DATABASE_PATH = os.path.join(DATA_DIR, 'proctoring.db')

# Web interface settings
WEB_HOST = '127.0.0.1'
WEB_PORT = 5000
WEB_DEBUG = False