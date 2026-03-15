"""
Test script for camera and video modules
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import time
from modules.video.capture import VideoCapture
from modules.video.face_detector import FaceDetector
from modules.video.object_detector import ObjectDetector

def test_camera_capture():
    """Test camera capture"""
    print("\n=== Testing Camera Capture ===")
    
    capture = VideoCapture()
    capture.start()
    
    print("Capturing frames for 5 seconds...")
    
    frame_count = 0
    start_time = time.time()
    
    while time.time() - start_time < 5:
        frame = capture.get_frame()
        if frame is not None:
            frame_count += 1
            print(f"Frame {frame_count} captured", end='\r')
        time.sleep(0.01)
    
    fps = frame_count / 5
    print(f"\nCaptured {frame_count} frames at {fps:.1f} FPS")
    
    # Save a test frame
    filename = capture.save_frame("test_capture.jpg")
    print(f"Saved test frame: {filename}")
    
    info = capture.get_info()
    print(f"Camera info: {info}")
    
    capture.stop()
    return True

def test_face_detection():
    """Test face detection"""
    print("\n=== Testing Face Detection ===")
    
    capture = VideoCapture()
    detector = FaceDetector()
    
    capture.start()
    
    print("Running face detection. Press 'q' to quit.")
    print("Look at the camera and move around...")
    
    try:
        while True:
            frame = capture.get_frame()
            if frame is not None:
                # Detect faces
                annotated_frame = detector.detect_faces(frame)
                
                # Get info
                info = detector.get_face_info()
                
                # Display
                cv2.imshow('Face Detection Test', annotated_frame)
                
                # Print info occasionally
                if detector.frame_count % 30 == 0:
                    print(f"Faces: {info['face_count']}, "
                          f"Multiple: {info['multiple_faces']}, "
                          f"Not visible: {info['face_not_visible_duration']:.1f}s")
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    except KeyboardInterrupt:
        print("\nTest interrupted")
    
    capture.stop()
    detector.stop()
    cv2.destroyAllWindows()
    return True

def test_object_detection():
    """Test object detection"""
    print("\n=== Testing Object Detection ===")
    
    capture = VideoCapture()
    detector = ObjectDetector()
    
    capture.start()
    
    print("Running object detection. Press 'q' to quit.")
    print("Show different objects to the camera...")
    
    try:
        while True:
            frame = capture.get_frame()
            if frame is not None:
                # Detect objects
                annotated_frame = detector.detect_objects(frame)
                
                # Get info
                info = detector.get_detection_info()
                
                # Display
                cv2.imshow('Object Detection Test', annotated_frame)
                
                # Print info occasionally
                if detector.frame_count % 30 == 0:
                    print(f"Objects: {info['detection_count']}, "
                          f"Suspicious: {info['suspicious_detected']}")
                    if info['suspicious_objects']:
                        objects = [o['class_name'] for o in info['suspicious_objects']]
                        print(f"  Suspicious: {objects}")
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    except KeyboardInterrupt:
        print("\nTest interrupted")
    
    capture.stop()
    detector.stop()
    cv2.destroyAllWindows()
    return True

if __name__ == "__main__":
    print("Camera Module Tests")
    print("=" * 50)
    
    test_camera_capture()
    test_face_detection()
    test_object_detection()
    
    print("\nAll camera tests completed!")