"""
Decision engine that correlates all modules and makes decisions
"""
import threading
import time
import queue
from datetime import datetime
from collections import deque
import numpy as np
from config.settings import SUSPICIOUS_SCORE_THRESHOLD, DECISION_INTERVAL

class DecisionEngine:
    def __init__(self, alert_system=None):
        """
        Initialize decision engine
        
        Args:
            alert_system: AlertSystem instance for sending alerts
        """
        self.alert_system = alert_system
        
        # Data queues from modules
        self.face_queue = queue.Queue()
        self.object_queue = queue.Queue()
        self.audio_queue = queue.Queue()
        
        # Current state
        self.current_state = {
            'face': {},
            'object': {},
            'audio': {},
            'timestamp': None
        }
        
        # Suspicious events
        self.suspicious_events = deque(maxlen=100)
        self.suspicious_score = 0.0
        
        # Alert cooldown tracking
        self.last_alert_time = {}
        
        # Threading
        self.is_running = False
        self.thread = None
        self.lock = threading.Lock()
        
        print("[DecisionEngine] Initialized")
    
    def update_face_data(self, face_info):
        """Update face detection data"""
        self.face_queue.put({
            'data': face_info,
            'timestamp': time.time()
        })
    
    def update_object_data(self, object_info):
        """Update object detection data"""
        self.object_queue.put({
            'data': object_info,
            'timestamp': time.time()
        })
    
    def update_audio_data(self, audio_info):
        """Update audio analysis data"""
        self.audio_queue.put({
            'data': audio_info,
            'timestamp': time.time()
        })
    
    def start(self):
        """Start decision engine"""
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        print("[DecisionEngine] Started")
    
    def _process_loop(self):
        """Main processing loop"""
        while self.is_running:
            try:
                # Get latest data from queues
                self._update_current_state()
                
                # Calculate suspicious score
                score = self._calculate_suspicious_score()
                
                with self.lock:
                    self.suspicious_score = score
                
                # Check if alert needed
                if score >= SUSPICIOUS_SCORE_THRESHOLD:
                    self._check_and_trigger_alerts()
                
                # Log event
                self._log_current_state()
                
                time.sleep(DECISION_INTERVAL)
                
            except Exception as e:
                print(f"[DecisionEngine] Error in process loop: {e}")
    
    def _update_current_state(self):
        """Update current state from queues"""
        # Get latest face data
        while not self.face_queue.empty():
            try:
                self.current_state['face'] = self.face_queue.get_nowait()
            except queue.Empty:
                break
        
        # Get latest object data
        while not self.object_queue.empty():
            try:
                self.current_state['object'] = self.object_queue.get_nowait()
            except queue.Empty:
                break
        
        # Get latest audio data
        while not self.audio_queue.empty():
            try:
                self.current_state['audio'] = self.audio_queue.get_nowait()
            except queue.Empty:
                break
        
        self.current_state['timestamp'] = time.time()
    
    def _calculate_suspicious_score(self):
        """
        Calculate overall suspicious score based on all modules
        
        Returns:
            float between 0 and 1
        """
        scores = []
        
        # Face-based score
        face_data = self.current_state['face'].get('data', {})
        if face_data:
            face_score = 0.0
            if face_data.get('multiple_faces', False):
                face_score += 0.8
            if face_data.get('face_not_visible', False):
                duration = face_data.get('face_not_visible_duration', 0)
                face_score += min(duration / 30, 0.7)  # Max 0.7 after 30 seconds
            scores.append(face_score)
        
        # Object-based score
        object_data = self.current_state['object'].get('data', {})
        if object_data:
            object_score = 0.0
            if object_data.get('suspicious_detected', False):
                object_score += 0.7
                # Add more for multiple suspicious objects
                suspicious_count = len(object_data.get('suspicious_objects', []))
                object_score += min(suspicious_count * 0.1, 0.3)
            scores.append(object_score)
        
        # Audio-based score
        audio_data = self.current_state['audio'].get('data', {})
        if audio_data:
            audio_score = 0.0
            if audio_data.get('multiple_voices', False):
                audio_score += 0.9
            elif audio_data.get('voice_activity', False):
                audio_score += 0.2  # Single voice is normal
            scores.append(audio_score)
        
        # Combine scores
        if scores:
            # Weighted average (can be customized)
            weights = [0.4, 0.4, 0.2]  # Face, Object, Audio
            weighted_scores = [s * w for s, w in zip(scores, weights[:len(scores)])]
            total_weight = sum(weights[:len(scores)])
            return sum(weighted_scores) / total_weight if total_weight > 0 else 0
        
        return 0.0
    
    def _check_and_trigger_alerts(self):
        """Check conditions and trigger alerts"""
        current_time = time.time()
        
        # Check each module for specific alerts
        face_data = self.current_state['face'].get('data', {})
        object_data = self.current_state['object'].get('data', {})
        audio_data = self.current_state['audio'].get('data', {})
        
        # Multiple faces alert
        if face_data.get('multiple_faces', False):
            self._trigger_alert('multiple_faces', 'Multiple faces detected in frame', 2)
        
        # Face not visible for too long
        face_duration = face_data.get('face_not_visible_duration', 0)
        if face_duration > 10:  # More than 10 seconds
            self._trigger_alert('face_not_visible', f'Face not visible for {face_duration:.1f} seconds', 
                              2 if face_duration < 30 else 3)
        
        # Suspicious objects
        if object_data.get('suspicious_detected', False):
            objects = [obj['class_name'] for obj in object_data.get('suspicious_objects', [])]
            self._trigger_alert('suspicious_objects', f'Suspicious objects detected: {", ".join(objects)}', 2)
        
        # Multiple voices
        if audio_data.get('multiple_voices', False):
            self._trigger_alert('multiple_voices', 'Multiple voices detected', 3)
    
    def _trigger_alert(self, alert_type, message, severity):
        """Trigger alert with cooldown check"""
        current_time = time.time()
        
        # Check cooldown
        last_time = self.last_alert_time.get(alert_type, 0)
        if current_time - last_time < 10:  # 10 second cooldown
            return
        
        self.last_alert_time[alert_type] = current_time
        
        # Create alert
        alert = {
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now(),
            'score': self.suspicious_score
        }
        
        # Add to events
        self.suspicious_events.append(alert)
        
        # Send to alert system if available
        if self.alert_system:
            self.alert_system.add_alert(alert)
        
        print(f"[DecisionEngine] ALERT [{severity}]: {message}")
    
    def _log_current_state(self):
        """Log current state for debugging"""
        if self.suspicious_score > 0.3:  # Log only when interesting
            print(f"[DecisionEngine] Score: {self.suspicious_score:.2f}")
    
    def get_current_state(self):
        """Get current state"""
        with self.lock:
            return {
                'state': self.current_state.copy(),
                'score': self.suspicious_score,
                'events': list(self.suspicious_events)[-10:]  # Last 10 events
            }
    
    def stop(self):
        """Stop decision engine"""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        print("[DecisionEngine] Stopped")

# Test function
if __name__ == "__main__":
    # Test decision engine
    engine = DecisionEngine()
    engine.start()
    
    # Simulate some data
    for i in range(10):
        engine.update_face_data({
            'multiple_faces': i % 3 == 0,
            'face_not_visible': i % 4 == 0,
            'face_not_visible_duration': i * 2
        })
        
        engine.update_object_data({
            'suspicious_detected': i % 2 == 0,
            'suspicious_objects': [{'class_name': 'cell phone'}] if i % 2 == 0 else []
        })
        
        engine.update_audio_data({
            'multiple_voices': i % 5 == 0,
            'voice_activity': True
        })
        
        time.sleep(2)
    
    engine.stop()