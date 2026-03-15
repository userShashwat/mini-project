"""
Database utility for storing session data and alerts
"""
import sqlite3
import json
import os
from datetime import datetime
from config.settings import DATABASE_PATH

class ProctorDatabase:
    def __init__(self, db_path=DATABASE_PATH):
        """
        Initialize database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        # Connect and create tables
        self.connect()
        self.create_tables()
        
        print(f"[Database] Initialized: {db_path}")
    
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def create_tables(self):
        """Create necessary tables if they don't exist"""
        
        # Sessions table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT UNIQUE,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration INTEGER,
                alert_count INTEGER DEFAULT 0,
                max_suspicious_score REAL DEFAULT 0,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Alerts table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                timestamp TIMESTAMP,
                type TEXT,
                message TEXT,
                severity INTEGER,
                score REAL,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        ''')
        
        # Events table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                timestamp TIMESTAMP,
                event_type TEXT,
                details TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        ''')
        
        # Snapshots table (for storing frames)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                timestamp TIMESTAMP,
                filename TEXT,
                description TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        ''')
        
        self.conn.commit()
    
    def create_session(self, session_name=None):
        """Create new session"""
        if session_name is None:
            session_name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.cursor.execute('''
            INSERT INTO sessions (session_name, start_time, status)
            VALUES (?, ?, ?)
        ''', (session_name, datetime.now(), 'active'))
        
        self.conn.commit()
        session_id = self.cursor.lastrowid
        
        print(f"[Database] Created session: {session_name} (ID: {session_id})")
        return session_id
    
    def end_session(self, session_id):
        """End a session"""
        self.cursor.execute('''
            UPDATE sessions 
            SET end_time = ?, status = 'completed',
                duration = strftime('%s', ?) - strftime('%s', start_time)
            WHERE id = ?
        ''', (datetime.now(), datetime.now(), session_id))
        
        self.conn.commit()
        print(f"[Database] Ended session ID: {session_id}")
    
    def add_alert(self, session_id, alert):
        """Add alert to database"""
        metadata = {
            'type': alert.get('type'),
            'details': alert.get('details', {})
        }
        
        self.cursor.execute('''
            INSERT INTO alerts 
            (session_id, timestamp, type, message, severity, score, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            alert.get('timestamp', datetime.now()),
            alert.get('type', 'unknown'),
            alert.get('message', ''),
            alert.get('severity', 1),
            alert.get('score', 0),
            json.dumps(metadata)
        ))
        
        # Update alert count in session
        self.cursor.execute('''
            UPDATE sessions 
            SET alert_count = alert_count + 1,
                max_suspicious_score = MAX(max_suspicious_score, ?)
            WHERE id = ?
        ''', (alert.get('score', 0), session_id))
        
        self.conn.commit()
    
    def add_event(self, session_id, event_type, details=None):
        """Add event to database"""
        self.cursor.execute('''
            INSERT INTO events (session_id, timestamp, event_type, details)
            VALUES (?, ?, ?, ?)
        ''', (session_id, datetime.now(), event_type, json.dumps(details or {})))
        
        self.conn.commit()
    
    def add_snapshot(self, session_id, filename, description=None):
        """Add snapshot record"""
        self.cursor.execute('''
            INSERT INTO snapshots (session_id, timestamp, filename, description)
            VALUES (?, ?, ?, ?)
        ''', (session_id, datetime.now(), filename, description))
        
        self.conn.commit()
    
    def get_sessions(self, limit=10):
        """Get recent sessions"""
        self.cursor.execute('''
            SELECT * FROM sessions 
            ORDER BY start_time DESC 
            LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_session_alerts(self, session_id, limit=50):
        """Get alerts for a session"""
        self.cursor.execute('''
            SELECT * FROM alerts 
            WHERE session_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (session_id, limit))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_session_summary(self, session_id):
        """Get session summary"""
        # Get session info
        self.cursor.execute('SELECT * FROM sessions WHERE id = ?', (session_id,))
        session = dict(self.cursor.fetchone())
        
        # Get alert count by severity
        self.cursor.execute('''
            SELECT severity, COUNT(*) as count 
            FROM alerts 
            WHERE session_id = ? 
            GROUP BY severity
        ''', (session_id,))
        
        alerts_by_severity = {row['severity']: row['count'] for row in self.cursor.fetchall()}
        
        session['alerts_by_severity'] = alerts_by_severity
        
        return session
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("[Database] Closed")

# Test function
if __name__ == "__main__":
    # Test database
    db = ProctorDatabase(":memory:")  # Use in-memory database for testing
    
    # Create session
    session_id = db.create_session("test_session")
    
    # Add some alerts
    db.add_alert(session_id, {
        'type': 'multiple_faces',
        'message': 'Test alert',
        'severity': 2,
        'score': 0.8,
        'timestamp': datetime.now()
    })
    
    # Add event
    db.add_event(session_id, 'test_event', {'key': 'value'})
    
    # Get sessions
    sessions = db.get_sessions()
    print(f"Sessions: {sessions}")
    
    # Get session summary
    summary = db.get_session_summary(session_id)
    print(f"Summary: {summary}")
    
    db.close()