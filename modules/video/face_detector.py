"""
Face detection and tracking module
"""
import cv2
import numpy as np
import face_recognition
import threading
import time
from datetime import datetime
from collections import deque
from config.settings import FACE_DETECTION_INTERVAL, MULTIPLE_FACES_THRESHOLD

class FaceDetector:
    def __init__(self):
        """
        Initialize face detector
        """
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.reference_encodings = []  # Known student faces
        self.reference_names = []
        
        self.frame_count = 0
        self.detection_interval = FACE_DETECTION_INTERVAL
        
        # Tracking variables
        self.look_away_start = None
        self.look_away_duration = 0
        self.multiple_faces_detected = False
        self.face_not_visible = False
        self.face_not_visible_start = None
        
        # History for smoothing
        self.face_count_history = deque(maxlen=10)
        self.last_detection_time = 0
        
        # Threading
        self.lock = threading.Lock()
        self.is_running = True
        
        # Load face detection model (HOG is faster, CNN more accurate)
        self.model = 'hog'  # or 'cnn' for GPU
        
        print("[FaceDetector] Initialized")
    
    def add_reference_face(self, image, name):
        """
        Add a reference face for recognition
        
        Args:
            image: Image containing face
            name: Person's name
        """
        if isinstance(image, str):
            # Load from file
            image = face_recognition.load_image_file(image)
        
        # Get face encoding
        encodings = face_recognition.face_encodings(image)
        if encodings:
            self.reference_encodings.append(encodings[0])
            self.reference_names.append(name)
            print(f"[FaceDetector] Added reference face for {name}")
            return True
        return False
    
    def detect_faces(self, frame):
        """
        Detect faces in frame
        
        Args:
            frame: BGR image
            
        Returns:
            frame with annotations
        """
        self.frame_count += 1
        
        # Only run detection every N frames for performance
        if self.frame_count % self.detection_interval != 0:
            return frame
        
        # Convert BGR to RGB (face_recognition uses RGB)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        start_time = time.time()
        face_locations = face_recognition.face_locations(rgb_frame, model=self.model)
        detection_time = time.time() - start_time
        
        with self.lock:
            self.face_locations = face_locations
            self.face_count_history.append(len(face_locations))
            
            # Detect if face is visible (using smoothed count)
            avg_face_count = sum(self.face_count_history) / max(len(self.face_count_history), 1)
            face_visible = avg_face_count > 0
            
            # Track look away
            current_time = time.time()
            if not face_visible:
                if self.face_not_visible_start is None:
                    self.face_not_visible_start = current_time
                self.face_not_visible = True
                self.face_not_visible_duration = current_time - self.face_not_visible_start
            else:
                self.face_not_visible_start = None
                self.face_not_visible = False
                self.face_not_visible_duration = 0
            
            # Check for multiple faces
            self.multiple_faces_detected = len(face_locations) > MULTIPLE_FACES_THRESHOLD
            
            # If we have reference faces, do recognition
            if self.reference_encodings and face_locations:
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                self.face_names = []
                
                for face_encoding in face_encodings:
                    # Check if this face matches any reference
                    matches = face_recognition.compare_faces(self.reference_encodings, face_encoding)
                    name = "Unknown"
                    
                    if True in matches:
                        first_match_index = matches.index(True)
                        name = self.reference_names[first_match_index]
                    
                    self.face_names.append(name)
            else:
                self.face_names = []
            
            self.last_detection_time = detection_time
        
        # Annotate frame
        return self._annotate_frame(frame)
    
    def _annotate_frame(self, frame):
        """Add face annotations to frame"""
        with self.lock:
            # Draw rectangles around faces
            for (top, right, bottom, left) in self.face_locations:
                # Draw rectangle
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                
                # Draw label
                if self.face_names and len(self.face_names) > len(self.face_locations):
                    # Something went wrong with matching
                    label = "Face"
                elif self.face_names:
                    idx = list(self.face_locations).index((top, right, bottom, left))
                    label = self.face_names[idx] if idx < len(self.face_names) else "Face"
                else:
                    label = "Face"
                
                # Put label above rectangle
                cv2.putText(frame, label, (left, top-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Add status text
            status_y = 30
            status_color = (0, 255, 0) if not self.multiple_faces_detected else (0, 0, 255)
            cv2.putText(frame, f"Faces: {len(self.face_locations)}", 
                       (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
            
            if self.face_not_visible and self.face_not_visible_duration > 5:
                cv2.putText(frame, f"WARNING: Face not visible for {self.face_not_visible_duration:.1f}s", 
                           (10, status_y+25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            if self.multiple_faces_detected:
                cv2.putText(frame, "WARNING: Multiple faces detected!", 
                           (10, status_y+50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        return frame
    
    def get_face_info(self):
        """Get current face detection information"""
        with self.lock:
            return {
                'face_count': len(self.face_locations),
                'face_locations': self.face_locations.copy(),
                'face_names': self.face_names.copy(),
                'multiple_faces': self.multiple_faces_detected,
                'face_not_visible': self.face_not_visible,
                'face_not_visible_duration': getattr(self, 'face_not_visible_duration', 0),
                'detection_time': self.last_detection_time
            }
    
    def stop(self):
        """Stop face detector"""
        self.is_running = False
        print("[FaceDetector] Stopped")

# Test function
if __name__ == "__main__":
    from capture import VideoCapture
    
    # Test face detection
    capture = VideoCapture()
    detector = FaceDetector()
    
    # Add a reference face if available
    # detector.add_reference_face("path/to/student_face.jpg", "Student Name")
    
    capture.start()
    
    try:
        while True:
            frame = capture.get_frame()
            if frame is not None:
                # Detect faces
                annotated_frame = detector.detect_faces(frame)
                
                # Show info
                info = detector.get_face_info()
                print(f"Faces: {info['face_count']}, Multiple: {info['multiple_faces']}", end='\r')
                
                cv2.imshow('Face Detection Test', annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    finally:
        capture.stop()
        detector.stop()
        cv2.destroyAllWindows()