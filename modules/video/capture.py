"""
Video capture module for handling camera input
"""
import cv2
import numpy as np
import threading
import time
from datetime import datetime
from config.settings import CAMERA_ID, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS

class VideoCapture:
    def __init__(self, camera_id=CAMERA_ID):
        """
        Initialize video capture
        
        Args:
            camera_id: Camera device ID (default from settings)
        """
        self.camera_id = camera_id
        self.cap = None
        self.is_running = False
        self.frame = None
        self.fps = CAMERA_FPS
        self.width = CAMERA_WIDTH
        self.height = CAMERA_HEIGHT
        self.frame_count = 0
        self.lock = threading.Lock()
        self.thread = None
        
    def start(self):
        """Start video capture thread"""
        if self.is_running:
            return
        
        self.cap = cv2.VideoCapture(self.camera_id)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera {self.camera_id}")
        
        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        # Get actual properties
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        self.is_running = True
        self.thread = threading.Thread(target=self._update_frame, daemon=True)
        self.thread.start()
        print(f"[VideoCapture] Started camera {self.camera_id} at {self.width}x{self.height} @ {self.fps}fps")
        
    def _update_frame(self):
        """Continuously capture frames in background"""
        while self.is_running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
                    self.frame_count += 1
            else:
                print("[VideoCapture] Warning: Failed to capture frame")
                time.sleep(0.01)
    
    def get_frame(self):
        """Get the latest frame"""
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()
    
    def get_resized_frame(self, width, height):
        """Get resized frame"""
        frame = self.get_frame()
        if frame is not None:
            return cv2.resize(frame, (width, height))
        return None
    
    def save_frame(self, filename=None):
        """Save current frame to disk"""
        frame = self.get_frame()
        if frame is not None:
            if filename is None:
                filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(filename, frame)
            return filename
        return None
    
    def stop(self):
        """Stop video capture"""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
        print("[VideoCapture] Stopped")
    
    def get_info(self):
        """Get camera information"""
        return {
            'camera_id': self.camera_id,
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'frame_count': self.frame_count,
            'is_running': self.is_running
        }

# Test function
if __name__ == "__main__":
    # Quick test
    capture = VideoCapture()
    capture.start()
    
    try:
        while True:
            frame = capture.get_frame()
            if frame is not None:
                cv2.imshow('Camera Test', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    finally:
        capture.stop()
        cv2.destroyAllWindows()