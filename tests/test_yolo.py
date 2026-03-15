"""
Test script for YOLO object detection
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import time
import torch
from ultralytics import YOLO
from config.settings import YOLO_MODEL_PATH, SUSPICIOUS_OBJECTS

def test_yolo_loading():
    """Test YOLO model loading"""
    print("\n=== Testing YOLO Model Loading ===")
    
    # Check if CUDA is available
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device}")
    
    # Load model
    print(f"Loading model from {YOLO_MODEL_PATH}...")
    start_time = time.time()
    
    try:
        model = YOLO(YOLO_MODEL_PATH)
        load_time = time.time() - start_time
        print(f"Model loaded in {load_time:.2f} seconds")
        
        # Model info
        print(f"Model type: {type(model)}")
        print(f"Model names: {model.names}")
        
        return True
    except Exception as e:
        print(f"Error loading model: {e}")
        return False

def test_yolo_inference():
    """Test YOLO inference"""
    print("\n=== Testing YOLO Inference ===")
    
    # Load model
    model = YOLO(YOLO_MODEL_PATH)
    
    # Create test image
    print("Creating test image...")
    test_image = cv2.imread("test_capture.jpg")
    if test_image is None:
        # Create a dummy image
        test_image = cv2.imread("test_capture.jpg")
        if test_image is None:
            test_image = 255 * np.ones((480, 640, 3), dtype=np.uint8)
            cv2.putText(test_image, "Test Image", (200, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    
    # Run inference
    print("Running inference...")
    start_time = time.time()
    
    results = model(test_image)
    
    inference_time = time.time() - start_time
    print(f"Inference completed in {inference_time:.3f} seconds")
    
    # Process results
    result = results[0]
    
    if result.boxes is not None:
        boxes = result.boxes.xyxy.cpu().numpy()
        confidences = result.boxes.conf.cpu().numpy()
        class_ids = result.boxes.cls.cpu().numpy().astype(int)
        
        print(f"Detected {len(boxes)} objects:")
        
        suspicious_detected = []
        for i, (box, conf, class_id) in enumerate(zip(boxes, confidences, class_ids)):
            class_name = result.names[class_id]
            print(f"  {i+1}. {class_name}: {conf:.2f} at {box.astype(int)}")
            
            if class_name in SUSPICIOUS_OBJECTS:
                suspicious_detected.append(class_name)
        
        if suspicious_detected:
            print(f"\nSUSPICIOUS OBJECTS DETECTED: {suspicious_detected}")
    else:
        print("No objects detected")
    
    # Annotate and save
    annotated = result.plot()
    cv2.imwrite("test_yolo_result.jpg", annotated)
    print("Saved annotated image to test_yolo_result.jpg")
    
    return True

def test_real_time_detection():
    """Test real-time object detection with camera"""
    print("\n=== Testing Real-time YOLO Detection ===")
    
    from modules.video.capture import VideoCapture
    
    capture = VideoCapture()
    model = YOLO(YOLO_MODEL_PATH)
    
    capture.start()
    
    print("Starting real-time detection. Press 'q' to quit.")
    print("Suspicious objects will be highlighted in RED")
    
    frame_count = 0
    fps_start = time.time()
    
    try:
        while True:
            frame = capture.get_frame()
            if frame is not None:
                frame_count += 1
                
                # Run inference every 2 frames for speed
                if frame_count % 2 == 0:
                    results = model(frame, verbose=False)[0]
                    
                    # Annotate frame
                    annotated = results.plot()
                    
                    # Check for suspicious objects
                    if results.boxes is not None:
                        class_ids = results.boxes.cls.cpu().numpy().astype(int)
                        class_names = [results.names[id] for id in class_ids]
                        
                        suspicious = [name for name in class_names if name in SUSPICIOUS_OBJECTS]
                        if suspicious:
                            cv2.putText(annotated, f"SUSPICIOUS: {suspicious}", 
                                      (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                                      0.7, (0, 0, 255), 2)
                    
                    # Calculate FPS
                    if frame_count % 30 == 0:
                        fps = frame_count / (time.time() - fps_start)
                        cv2.putText(annotated, f"FPS: {fps:.1f}", 
                                  (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                                  0.5, (255, 255, 255), 1)
                    
                    cv2.imshow('YOLO Real-time Detection', annotated)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    except KeyboardInterrupt:
        print("\nTest interrupted")
    
    capture.stop()
    cv2.destroyAllWindows()
    return True

if __name__ == "__main__":
    print("YOLO Module Tests")
    print("=" * 50)
    
    import numpy as np
    
    tests = [
        test_yolo_loading,
        test_yolo_inference,
        # test_real_time_detection  # Uncomment to test with camera
    ]
    
    for test in tests:
        success = test()
        if not success:
            print(f"Test failed: {test.__name__}")
            break
    
    print("\nAll YOLO tests completed!")