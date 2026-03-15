"""
Alert system for managing and displaying alerts
"""
import threading
import time
import queue
from datetime import datetime
import pygame
import os

class AlertSystem:
    def __init__(self):
        """
        Initialize alert system
        """
        self.alerts = []
        self.active_alerts = []
        self.alert_queue = queue.Queue()
        
        # Alert sounds
        self.sounds_enabled = True
        self.sound_files = {
            1: None,  # Info - no sound
            2: 'alert_warning.wav',  # Warning
            3: 'alert_critical.wav'   # Critical
        }
        
        # Initialize pygame for sounds
        pygame.mixer.init()
        
        # Alert callbacks
        self.callbacks = []
        
        # Threading
        self.is_running = False
        self.thread = None
        self.lock = threading.Lock()
        
        print("[AlertSystem] Initialized")
    
    def add_callback(self, callback):
        """Add callback function for alerts"""
        self.callbacks.append(callback)
    
    def add_alert(self, alert):
        """Add alert to queue"""
        self.alert_queue.put(alert)
        
        # Play sound if enabled
        if self.sounds_enabled:
            self._play_alert_sound(alert.get('severity', 1))
    
    def _play_alert_sound(self, severity):
        """Play alert sound based on severity"""
        sound_file = self.sound_files.get(severity)
        if sound_file and os.path.exists(sound_file):
            try:
                sound = pygame.mixer.Sound(sound_file)
                sound.play()
            except Exception as e:
                print(f"[AlertSystem] Could not play sound: {e}")
    
    def start(self):
        """Start alert system"""
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._process_alerts, daemon=True)
        self.thread.start()
        print("[AlertSystem] Started")
    
    def _process_alerts(self):
        """Process alerts from queue"""
        while self.is_running:
            try:
                # Get alert from queue (with timeout)
                alert = self.alert_queue.get(timeout=1.0)
                
                # Add to alerts list
                with self.lock:
                    self.alerts.append(alert)
                    self.active_alerts.append(alert)
                
                # Call callbacks
                for callback in self.callbacks:
                    try:
                        callback(alert)
                    except Exception as e:
                        print(f"[AlertSystem] Callback error: {e}")
                
                # Keep only last 100 alerts
                if len(self.alerts) > 100:
                    self.alerts = self.alerts[-100:]
                
                print(f"[AlertSystem] Alert processed: {alert['message']}")
                
            except queue.Empty:
                # Timeout, just continue
                pass
            except Exception as e:
                print(f"[AlertSystem] Error processing alert: {e}")
    
    def get_alerts(self, limit=50, severity=None):
        """Get recent alerts"""
        with self.lock:
            if severity:
                filtered = [a for a in self.alerts if a.get('severity') == severity]
                return filtered[-limit:]
            return self.alerts[-limit:]
    
    def clear_alerts(self):
        """Clear all alerts"""
        with self.lock:
            self.alerts.clear()
            self.active_alerts.clear()
        print("[AlertSystem] Alerts cleared")
    
    def stop(self):
        """Stop alert system"""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        print("[AlertSystem] Stopped")

# Test function
if __name__ == "__main__":
    # Test alert system
    alerts = AlertSystem()
    alerts.start()
    
    # Add test callback
    def test_callback(alert):
        print(f"Callback received: {alert['message']}")
    
    alerts.add_callback(test_callback)
    
    # Add some test alerts
    alerts.add_alert({
        'type': 'test',
        'message': 'Test info alert',
        'severity': 1,
        'timestamp': datetime.now()
    })
    
    alerts.add_alert({
        'type': 'test',
        'message': 'Test warning alert',
        'severity': 2,
        'timestamp': datetime.now()
    })
    
    alerts.add_alert({
        'type': 'test',
        'message': 'Test critical alert',
        'severity': 3,
        'timestamp': datetime.now()
    })
    
    # Wait a bit
    time.sleep(2)
    
    # Get alerts
    recent = alerts.get_alerts()
    print(f"Recent alerts: {len(recent)}")
    
    alerts.stop()