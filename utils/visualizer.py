"""
Visualization utility for displaying proctoring data
"""
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io
from datetime import datetime

class ProctorVisualizer:
    def __init__(self):
        """
        Initialize visualizer
        """
        self.fig = None
        self.ax = None
        
        # Colors for different alert levels
        self.colors = {
            1: (0, 255, 0),    # Info - Green
            2: (0, 255, 255),  # Warning - Yellow
            3: (0, 0, 255)     # Critical - Red
        }
    
    def create_overlay(self, frame, state, alerts=None):
        """
        Create overlay on video frame
        
        Args:
            frame: Original frame
            state: Current state from decision engine
            alerts: Recent alerts
            
        Returns:
            Annotated frame
        """
        if frame is None:
            return None
        
        # Make a copy
        overlay = frame.copy()
        h, w = overlay.shape[:2]
        
        # Add semi-transparent header
        header_height = 80
        cv2.rectangle(overlay, (0, 0), (w, header_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
        
        # Add title
        cv2.putText(frame, "Proctoring AI System", (10, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (w - 200, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Add suspicious score
        score = state.get('score', 0)
        score_color = self._get_score_color(score)
        cv2.putText(frame, f"Suspicious Score: {score:.2f}", (10, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, score_color, 2)
        
        # Add module status
        y_offset = 80
        
        # Face status
        face_state = state.get('state', {}).get('face', {}).get('data', {})
        face_text = f"Face: {face_state.get('face_count', 0)} detected"
        if face_state.get('multiple_faces', False):
            face_text += " [MULTIPLE!]"
            color = (0, 0, 255)
        else:
            color = (0, 255, 0)
        cv2.putText(frame, face_text, (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        y_offset += 20
        
        # Object status
        obj_state = state.get('state', {}).get('object', {}).get('data', {})
        obj_text = f"Objects: {obj_state.get('detection_count', 0)} detected"
        if obj_state.get('suspicious_detected', False):
            obj_text += " [SUSPICIOUS!]"
            color = (0, 0, 255)
        else:
            color = (0, 255, 0)
        cv2.putText(frame, obj_text, (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        y_offset += 20
        
        # Audio status
        audio_state = state.get('state', {}).get('audio', {}).get('data', {})
        audio_text = f"Audio: "
        if audio_state.get('multiple_voices', False):
            audio_text += "Multiple voices!"
            color = (0, 0, 255)
        elif audio_state.get('voice_activity', False):
            audio_text += "Voice detected"
            color = (0, 255, 0)
        else:
            audio_text += "Silence"
            color = (200, 200, 200)
        cv2.putText(frame, audio_text, (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Add recent alerts if available
        if alerts:
            y_offset = h - 100
            cv2.rectangle(frame, (0, y_offset - 5), (w, h), (0, 0, 0), -1)
            cv2.addWeighted(frame[y_offset-5:h, 0:w], 0.3, 
                           np.zeros((105, w, 3), dtype=np.uint8), 0.7, 0, 
                           frame[y_offset-5:h, 0:w])
            
            cv2.putText(frame, "Recent Alerts:", (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            y_offset += 20
            
            for alert in alerts[-3:]:  # Show last 3 alerts
                severity = alert.get('severity', 1)
                color = self.colors.get(severity, (255, 255, 255))
                
                # Truncate long messages
                message = alert.get('message', '')
                if len(message) > 50:
                    message = message[:47] + "..."
                
                cv2.putText(frame, f"• {message}", (20, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                y_offset += 20
        
        return frame
    
    def _get_score_color(self, score):
        """Get color based on suspicious score"""
        if score < 0.3:
            return (0, 255, 0)  # Green
        elif score < 0.7:
            return (0, 255, 255)  # Yellow
        else:
            return (0, 0, 255)  # Red
    
    def create_dashboard(self, session_data):
        """
        Create a matplotlib dashboard
        
        Args:
            session_data: Dictionary with session data
            
        Returns:
            numpy array of dashboard image
        """
        # Create figure
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle('Proctoring Session Dashboard', fontsize=16)
        
        # Alert timeline
        if 'alerts' in session_data:
            alerts = session_data['alerts']
            times = [a['timestamp'] for a in alerts]
            severities = [a['severity'] for a in alerts]
            
            axes[0, 0].scatter(times, severities, c=severities, cmap='RdYlGn_r')
            axes[0, 0].set_title('Alerts Timeline')
            axes[0, 0].set_xlabel('Time')
            axes[0, 0].set_ylabel('Severity')
        
        # Suspicious score over time
        if 'scores' in session_data:
            scores = session_data['scores']
            axes[0, 1].plot(scores)
            axes[0, 1].set_title('Suspicious Score')
            axes[0, 1].set_xlabel('Time')
            axes[0, 1].set_ylabel('Score')
            axes[0, 1].axhline(y=0.7, color='r', linestyle='--', alpha=0.5)
        
        # Module activity
        if 'module_stats' in session_data:
            modules = list(session_data['module_stats'].keys())
            values = list(session_data['module_stats'].values())
            
            axes[1, 0].bar(modules, values)
            axes[1, 0].set_title('Module Activity')
            axes[1, 0].set_ylabel('Events')
        
        # Alert types pie chart
        if 'alert_types' in session_data:
            types = list(session_data['alert_types'].keys())
            counts = list(session_data['alert_types'].values())
            
            axes[1, 1].pie(counts, labels=types, autopct='%1.1f%%')
            axes[1, 1].set_title('Alert Types')
        
        plt.tight_layout()
        
        # Convert to image
        canvas = FigureCanvas(fig)
        canvas.draw()
        
        # Get image as numpy array
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        
        # Convert to OpenCV format
        img_arr = np.frombuffer(buf.getvalue(), dtype=np.uint8)
        img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
        
        plt.close(fig)
        
        return img
    
    def close(self):
        """Clean up"""
        if self.fig:
            plt.close(self.fig)

# Test function
if __name__ == "__main__":
    # Test visualizer
    viz = ProctorVisualizer()
    
    # Create test frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Test state
    state = {
        'score': 0.75,
        'state': {
            'face': {'data': {'face_count': 1, 'multiple_faces': False}},
            'object': {'data': {'detection_count': 3, 'suspicious_detected': True}},
            'audio': {'data': {'voice_activity': True, 'multiple_voices': False}}
        }
    }
    
    # Test alerts
    alerts = [
        {'severity': 2, 'message': 'Multiple faces detected'},
        {'severity': 3, 'message': 'Suspicious object: cell phone'},
        {'severity': 1, 'message': 'Session started'}
    ]
    
    # Create overlay
    overlay = viz.create_overlay(frame, state, alerts)
    
    if overlay is not None:
        cv2.imshow('Visualizer Test', overlay)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    viz.close()