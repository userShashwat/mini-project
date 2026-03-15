"""
Main entry point for Proctoring AI System
"""
import sys
import os
import time
import threading
import argparse
from datetime import datetime
import cv2

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.video.capture import VideoCapture
from modules.video.face_detector import FaceDetector
from modules.video.object_detector import ObjectDetector
from modules.audio.recorder import AudioRecorder
from modules.audio.analyzer import AudioAnalyzer
from modules.core.decision_engine import DecisionEngine
from modules.core.alert_system import AlertSystem
from utils.logger import ProctorLogger
from utils.database import ProctorDatabase
from utils.visualizer import ProctorVisualizer
from config.settings import *

class ProctoringSystem:
    def __init__(self, headless=False):
        """
        Initialize complete proctoring system
        
        Args:
            headless: Run without GUI (for server deployment)
        """
        self.headless = headless
        self.is_running = False
        
        # Initialize components
        self.logger = ProctorLogger()
        self.db = ProctorDatabase()
        self.visualizer = ProctorVisualizer() if not headless else None
        
        # Create session
        self.session_id = self.db.create_session()
        self.logger.info(f"Session started: {self.session_id}")
        
        # Initialize modules
        self.video_capture = VideoCapture()
        self.face_detector = FaceDetector()
        self.object_detector = ObjectDetector()
        self.audio_recorder = AudioRecorder()
        self.audio_analyzer = AudioAnalyzer()
        self.alert_system = AlertSystem()
        self.decision_engine = DecisionEngine(self.alert_system)
        
        # Connect alert system to logger
        self.alert_system.add_callback(self.logger.log_alert)
        self.alert_system.add_callback(self.db.add_alert_callback(self.session_id))
        
        # Threading
        self.threads = []
        self.stop_event = threading.Event()
        
        self.logger.info("Proctoring System initialized")
    
    def start(self):
        """Start all modules"""
        self.logger.info("Starting proctoring system...")
        self.is_running = True
        
        # Start modules
        self.video_capture.start()
        self.audio_recorder.start_recording()
        self.alert_system.start()
        self.decision_engine.start()
        
        # Start processing threads
        self._start_processing_threads()
        
        self.logger.info("All modules started")
    
    def _start_processing_threads(self):
        """Start processing threads for each module"""
        
        # Face detection thread
        def face_processing():
            while not self.stop_event.is_set():
                frame = self.video_capture.get_frame()
                if frame is not None:
                    # Detect faces
                    annotated = self.face_detector.detect_faces(frame)
                    
                    # Update decision engine
                    self.decision_engine.update_face_data(
                        self.face_detector.get_face_info()
                    )
                    
                    # Store frame for display (optional)
                    if hasattr(self, 'current_frame'):
                        self.current_frame = annotated
                
                time.sleep(0.03)  # ~30 FPS
        
        # Object detection thread (slower)
        def object_processing():
            while not self.stop_event.is_set():
                frame = self.video_capture.get_frame()
                if frame is not None:
                    # Detect objects
                    annotated = self.object_detector.detect_objects(frame)
                    
                    # Update decision engine
                    self.decision_engine.update_object_data(
                        self.object_detector.get_detection_info()
                    )
                
                time.sleep(0.1)  # 10 FPS
        
        # Audio processing thread
        def audio_processing():
            while not self.stop_event.is_set():
                chunk = self.audio_recorder.get_audio_chunk(2)  # 2 second chunks
                if chunk is not None:
                    # Analyze audio
                    analysis = self.audio_analyzer.analyze_audio(chunk)
                    
                    # Update decision engine
                    self.decision_engine.update_audio_data(analysis)
                    
                    # Store for later if needed
                    self.audio_recorder.recorded_chunks.append(chunk)
                
                time.sleep(1)
        
        # Start threads
        threads = [
            threading.Thread(target=face_processing, daemon=True),
            threading.Thread(target=object_processing, daemon=True),
            threading.Thread(target=audio_processing, daemon=True)
        ]
        
        for t in threads:
            t.start()
            self.threads.append(t)
        
        self.logger.info(f"Started {len(threads)} processing threads")
    
    def run_gui(self):
        """Run with GUI display"""
        if self.headless:
            self.logger.warning("Running in headless mode, GUI not available")
            return
        
        self.logger.info("Starting GUI")
        
        try:
            while self.is_running:
                # Get current frame
                if hasattr(self, 'current_frame'):
                    frame = self.current_frame
                else:
                    frame = self.video_capture.get_frame()
                
                if frame is not None:
                    # Get current state
                    state = self.decision_engine.get_current_state()
                    
                    # Get recent alerts
                    alerts = self.alert_system.get_alerts(5)
                    
                    # Create overlay
                    display = self.visualizer.create_overlay(frame, state, alerts)
                    
                    # Show frame
                    cv2.imshow('Proctoring AI System', display)
                    
                    # Check for key press
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        self.logger.info("Quit requested")
                        break
                    elif key == ord('s'):
                        # Save screenshot
                        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        cv2.imwrite(filename, display)
                        self.logger.info(f"Screenshot saved: {filename}")
                
                time.sleep(0.03)
        
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        finally:
            cv2.destroyAllWindows()
    
    def run_headless(self):
        """Run without GUI"""
        self.logger.info("Running in headless mode")
        
        try:
            while self.is_running:
                # Just log status every minute
                time.sleep(60)
                state = self.decision_engine.get_current_state()
                self.logger.info(f"Current suspicious score: {state['score']:.2f}")
                self.logger.info(f"Recent alerts: {len(state['events'])}")
        
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
    
    def stop(self):
        """Stop all modules"""
        self.logger.info("Stopping proctoring system...")
        self.is_running = False
        self.stop_event.set()
        
        # Stop modules
        self.video_capture.stop()
        self.audio_recorder.stop_recording()
        self.face_detector.stop()
        self.object_detector.stop()
        self.audio_analyzer.stop()
        self.decision_engine.stop()
        self.alert_system.stop()
        
        # Wait for threads
        for t in self.threads:
            t.join(timeout=2.0)
        
        # End session
        self.db.end_session(self.session_id)
        
        # Save audio recording if any
        audio_file = self.audio_recorder.save_recording()
        if audio_file:
            self.db.add_snapshot(self.session_id, audio_file, "Audio recording")
            self.logger.info(f"Audio saved: {audio_file}")
        
        # Export summary
        summary_file = self.logger.export_summary()
        self.db.add_snapshot(self.session_id, summary_file, "Session summary")
        
        # Close connections
        self.db.close()
        self.logger.close()
        
        if self.visualizer:
            self.visualizer.close()
        
        print("\n" + "="*50)
        print("Proctoring session ended")
        print(f"Session ID: {self.session_id}")
        print(f"Log file: {self.logger.log_file}")
        print("="*50)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Proctoring AI System')
    parser.add_argument('--headless', action='store_true', 
                       help='Run without GUI')
    parser.add_argument('--test', action='store_true',
                       help='Run in test mode')
    
    args = parser.parse_args()
    
    if args.test:
        # Run tests
        print("Running in test mode")
        import tests.test_audio
        import tests.test_camera
        import tests.test_yolo
        
        tests.test_audio.test_audio_recording()
        tests.test_audio.test_audio_analysis()
        tests.test_camera.test_camera_capture()
        tests.test_yolo.test_yolo_loading()
        tests.test_yolo.test_yolo_inference()
        
        return
    
    # Run main system
    system = ProctoringSystem(headless=args.headless)
    
    try:
        system.start()
        
        if args.headless:
            system.run_headless()
        else:
            system.run_gui()
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    
    finally:
        system.stop()

if __name__ == "__main__":
    main()