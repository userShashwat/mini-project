"""
Logging utility for proctoring system
"""
import logging
import os
from datetime import datetime
from config.settings import LOGS_DIR

class ProctorLogger:
    def __init__(self, session_name=None):
        """
        Initialize logger
        
        Args:
            session_name: Name of the session (default: timestamp)
        """
        if session_name is None:
            session_name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.session_name = session_name
        self.log_file = os.path.join(LOGS_DIR, f"{session_name}.log")
        
        # Create logger
        self.logger = logging.getLogger(session_name)
        self.logger.setLevel(logging.DEBUG)
        
        # File handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Session events
        self.events = []
        
        print(f"[Logger] Initialized: {self.log_file}")
    
    def info(self, message):
        """Log info message"""
        self.logger.info(message)
        self.events.append(('INFO', message, datetime.now()))
    
    def warning(self, message):
        """Log warning message"""
        self.logger.warning(message)
        self.events.append(('WARNING', message, datetime.now()))
    
    def error(self, message):
        """Log error message"""
        self.logger.error(message)
        self.events.append(('ERROR', message, datetime.now()))
    
    def critical(self, message):
        """Log critical message"""
        self.logger.critical(message)
        self.events.append(('CRITICAL', message, datetime.now()))
    
    def debug(self, message):
        """Log debug message"""
        self.logger.debug(message)
    
    def log_alert(self, alert):
        """Log alert from alert system"""
        severity = alert.get('severity', 1)
        message = f"ALERT [{severity}]: {alert['message']}"
        
        if severity == 3:
            self.critical(message)
        elif severity == 2:
            self.warning(message)
        else:
            self.info(message)
    
    def get_events(self, limit=None):
        """Get recent events"""
        if limit:
            return self.events[-limit:]
        return self.events
    
    def export_summary(self):
        """Export session summary"""
        summary_file = os.path.join(LOGS_DIR, f"{self.session_name}_summary.txt")
        
        with open(summary_file, 'w') as f:
            f.write(f"Session: {self.session_name}\n")
            f.write(f"Date: {datetime.now()}\n")
            f.write("-" * 50 + "\n\n")
            
            # Count by level
            levels = {'INFO': 0, 'WARNING': 0, 'ERROR': 0, 'CRITICAL': 0}
            for level, _, _ in self.events:
                levels[level] = levels.get(level, 0) + 1
            
            f.write("Event Summary:\n")
            for level, count in levels.items():
                f.write(f"  {level}: {count}\n")
            
            f.write("\nRecent Events:\n")
            for level, message, timestamp in self.events[-20:]:
                f.write(f"  [{timestamp.strftime('%H:%M:%S')}] {level}: {message}\n")
        
        print(f"[Logger] Summary exported to: {summary_file}")
        return summary_file
    
    def close(self):
        """Close logger"""
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
        print(f"[Logger] Closed: {self.session_name}")

# Test function
if __name__ == "__main__":
    # Test logger
    logger = ProctorLogger("test_session")
    
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")
    
    # Test alert logging
    logger.log_alert({
        'severity': 2,
        'message': 'Test alert'
    })
    
    # Get events
    events = logger.get_events(5)
    print(f"Recent events: {len(events)}")
    
    # Export summary
    logger.export_summary()
    
    logger.close()