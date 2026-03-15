"""
Session Manager module for Proctoring AI
Manages exam sessions, student data, and session state
"""
from datetime import datetime
import uuid
import json
from collections import deque

class SessionManager:
    """
    Manages individual exam sessions
    """
    def __init__(self, student_id="unknown", exam_name="General Exam"):
        self.session_id = str(uuid.uuid4())[:8]
        self.student_id = student_id
        self.exam_name = exam_name
        self.start_time = datetime.now()
        self.end_time = None
        self.is_active = True
        self.alerts = []
        self.events = deque(maxlen=500)
        self.suspicious_scores = deque(maxlen=1000)
        self.current_score = 0.0
        self.max_score = 0.0
        self.alert_count = 0
        
        print(f"[SessionManager] Session {self.session_id} started for {student_id}")
    
    def log_event(self, event_type, details=None):
        """Log an event in the session"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'details': details or {}
        }
        self.events.append(event)
        return event
    
    def add_alert(self, alert):
        """Add an alert to the session"""
        alert['timestamp'] = datetime.now().isoformat()
        alert['session_id'] = self.session_id
        self.alerts.append(alert)
        self.alert_count += 1
        return alert
    
    def update_score(self, score):
        """Update suspicious score"""
        self.suspicious_scores.append(score)
        self.current_score = score
        if score > self.max_score:
            self.max_score = score
    
    def get_duration(self):
        """Get session duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()
    
    def end_session(self):
        """End the session"""
        self.is_active = False
        self.end_time = datetime.now()
        print(f"[SessionManager] Session {self.session_id} ended. Duration: {self.get_duration():.1f}s")
    
    def get_summary(self):
        """Get session summary"""
        return {
            'session_id': self.session_id,
            'student_id': self.student_id,
            'exam_name': self.exam_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.get_duration(),
            'is_active': self.is_active,
            'alert_count': self.alert_count,
            'max_score': self.max_score,
            'current_score': self.current_score
        }
    
    def to_dict(self):
        """Convert session to dictionary"""
        return {
            'session_id': self.session_id,
            'student_id': self.student_id,
            'exam_name': self.exam_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'is_active': self.is_active,
            'alert_count': self.alert_count,
            'max_score': self.max_score,
            'current_score': self.current_score,
            'alerts': self.alerts[-10:]  # Last 10 alerts
        }