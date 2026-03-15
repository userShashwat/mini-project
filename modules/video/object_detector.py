"""
Object detection module using YOLO
"""
import cv2
import numpy as np
import torch
from ultralytics import YOLO
import threading
import time
from config.settings import YOLO_MODEL_PATH, OBJECT_DETECTION_INTERVAL, SUSPICIOUS_OBJECTS

class ObjectDetector:
    def __init__(self, model_path=YOLO_MODEL_PATH):
        """
        Initialize YOLO object detector
        
        Args:
            model_path: Path to YOLO model
        """
        self.model_path = model_path
        self.model = None
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        self.frame_count = 0
        self.detection_interval = OBJECT_DETECTION_INTERVAL
        
        # Detection results
        self.detections = []
        self.suspicious_objects = []
        self.suspicious_objects_detected = False
        
        # Suspicious objects list
        self.suspicious_classes = SUSPICIOUS_OBJECTS
        
        # Threading
        self.lock = threading.Lock()
        self.is_running = True
        self.last_detection_time = 0
        
        # Load model
        self._load_model()
        
        # COCO class names (YOLO default)
        self.class_names = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
            'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
            'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
            'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
            'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
            'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
            'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair',
            'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
            'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator',
            'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
        ]
        
        print(f"[ObjectDetector] Initialized on {self.device}")
    
    def _load_model(self):
        """Load YOLO model"""
        try:
            # Try to load from path, if not found download
            self.model = YOLO(self.model_path)
            print(f"[ObjectDetector] Model loaded from {self.model_path}")
        except Exception as e:
            print(f"[ObjectDetector] Failed to load model from {self.model_path}: {e}")
            print("[ObjectDetector] Downloading default YOLOv8n model...")
            self.model = YOLO('yolov8n.pt')
    
    def detect_objects(self, frame):
        """
        Detect objects in frame
        
        Args:
            frame: BGR image
            
        Returns:
            frame with annotations
        """
        self.frame_count += 1
        
        # Only run detection every N frames for performance
        if self.frame_count % self.detection_interval != 0:
            return frame
        
        # Run inference
        start_time = time.time()
        results = self.model(frame, verbose=False)[0]
        inference_time = time.time() - start_time
        
        # Parse results
        detections = []
        suspicious_objects = []
        suspicious_detected = False
        
        if results.boxes is not None:
            boxes = results.boxes.xyxy.cpu().numpy()
            confidences = results.boxes.conf.cpu().numpy()
            class_ids = results.boxes.cls.cpu().numpy().astype(int)
            
            for i, (box, conf, class_id) in enumerate(zip(boxes, confidences, class_ids)):
                class_name = self.class_names[class_id] if class_id < len(self.class_names) else f"class_{class_id}"
                
                detection = {
                    'bbox': box.tolist(),
                    'confidence': float(conf),
                    'class_id': int(class_id),
                    'class_name': class_name
                }
                detections.append(detection)
                
                # Check if suspicious
                if class_name in self.suspicious_classes and conf > 0.5:
                    suspicious_objects.append(detection)
                    suspicious_detected = True
        
        with self.lock:
            self.detections = detections
            self.suspicious_objects = suspicious_objects
            self.suspicious_objects_detected = suspicious_detected
            self.last_detection_time = inference_time
        
        # Annotate frame
        return self._annotate_frame(frame)
    
    def _annotate_frame(self, frame):
        """Add object detection annotations"""
        with self.lock:
            for detection in self.detections:
                bbox = detection['bbox']
                conf = detection['confidence']
                class_name = detection['class_name']
                
                x1, y1, x2, y2 = map(int, bbox)
                
                # Choose color based on suspiciousness
                if class_name in self.suspicious_classes:
                    color = (0, 0, 255)  # Red for suspicious
                    label = f"{class_name} ({conf:.2f}) SUSPICIOUS"
                else:
                    color = (255, 0, 0)  # Blue for normal
                    label = f"{class_name} ({conf:.2f})"
                
                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Draw label background
                (label_width, label_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(frame, (x1, y1 - label_height - 10), (x1 + label_width, y1), color, -1)
                
                # Draw label text
                cv2.putText(frame, label, (x1, y1 - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            # Add status text
            if self.suspicious_objects_detected:
                cv2.putText(frame, "WARNING: Suspicious objects detected!", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # List suspicious objects
                y_offset = 60
                for obj in self.suspicious_objects[:3]:  # Show top 3
                    cv2.putText(frame, f"- {obj['class_name']}", 
                               (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
                    y_offset += 25
        
        return frame
    
    def get_detection_info(self):
        """Get current detection information"""
        with self.lock:
            return {
                'detections': self.detections.copy(),
                'suspicious_objects': self.suspicious_objects.copy(),
                'suspicious_detected': self.suspicious_objects_detected,
                'detection_count': len(self.detections),
                'detection_time': self.last_detection_time
            }
    
    def stop(self):
        """Stop object detector"""
        self.is_running = False
        print("[ObjectDetector] Stopped")

# Test function
if __name__ == "__main__":
    from capture import VideoCapture
    
    # Test object detection
    capture = VideoCapture()
    detector = ObjectDetector()
    
    capture.start()
    
    try:
        while True:
            frame = capture.get_frame()
            if frame is not None:
                # Detect objects
                annotated_frame = detector.detect_objects(frame)
                
                # Show info
                info = detector.get_detection_info()
                print(f"Objects: {info['detection_count']}, Suspicious: {info['suspicious_detected']}", end='\r')
                
                cv2.imshow('Object Detection Test', annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    finally:
        capture.stop()
        detector.stop()
        cv2.destroyAllWindows()