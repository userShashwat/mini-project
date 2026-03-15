#!/usr/bin/env python
"""
Script to generate sample data for testing
"""
import os
import sys
import json
import random
import numpy as np
from datetime import datetime, timedelta
import argparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import ProctorDatabase

def generate_students(num_students=20):
    """Generate sample students"""
    first_names = ['John', 'Jane', 'Mike', 'Sarah', 'David', 'Emma', 'Chris', 'Lisa', 'Tom', 'Anna']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
    
    students = []
    for i in range(num_students):
        student = {
            'id': f"S{2026000 + i}",
            'first_name': random.choice(first_names),
            'last_name': random.choice(last_names),
            'email': f"student{i}@university.edu",
            'year': random.randint(1, 4),
            'major': random.choice(['CS', 'Engineering', 'Business', 'Math', 'Physics'])
        }
        students.append(student)
    
    return students

def generate_exams(num_exams=10):
    """Generate sample exams"""
    exam_names = ['Midterm Exam', 'Final Exam', 'Quiz 1', 'Quiz 2', 'Programming Test', 
                  'Theory Exam', 'Lab Test', 'Project Presentation', 'Oral Exam', 'Written Test']
    
    exams = []
    for i in range(num_exams):
        start_date = datetime.now() - timedelta(days=random.randint(0, 30))
        exam = {
            'id': f"E{2026000 + i}",
            'name': random.choice(exam_names),
            'course': f"CSC{random.randint(100, 500)}",
            'date': start_date.strftime('%Y-%m-%d'),
            'start_time': start_date.strftime('%H:%M:%S'),
            'duration': random.choice([60, 90, 120, 180]),
            'proctor': f"P{random.randint(1, 5)}"
        }
        exams.append(exam)
    
    return exams

def generate_session_data(student_id, exam_id, num_alerts=20):
    """Generate sample session data"""
    start_time = datetime.now() - timedelta(hours=random.randint(1, 48))
    end_time = start_time + timedelta(minutes=random.randint(30, 120))
    
    session = {
        'student_id': student_id,
        'exam_id': exam_id,
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'duration': (end_time - start_time).total_seconds() / 60,
        'status': random.choice(['completed', 'terminated', 'in_progress']),
        'suspicious_score': random.uniform(0, 1),
        'alert_count': num_alerts
    }
    
    # Generate alerts
    alerts = []
    alert_types = ['multiple_faces', 'cell_phone', 'looking_away', 'audio', 'object']
    severities = [1, 2, 3]
    
    for i in range(num_alerts):
        alert_time = start_time + timedelta(seconds=random.randint(30, int((end_time - start_time).total_seconds())))
        alert = {
            'timestamp': alert_time.isoformat(),
            'type': random.choice(alert_types),
            'severity': random.choice(severities),
            'message': f"Alert {i+1}: {random.choice(alert_types)} detected",
            'score': random.uniform(0.5, 1)
        }
        alerts.append(alert)
    
    # Sort alerts by time
    alerts.sort(key=lambda x: x['timestamp'])
    
    # Generate timeline scores
    timeline = []
    num_points = 20
    for i in range(num_points):
        time_point = start_time + timedelta(seconds=i * ((end_time - start_time).total_seconds() / num_points))
        score = random.uniform(0, 1)
        # Make score more realistic with trends
        if i > num_points // 2:
            score = min(1, score + 0.2)  # Higher scores towards end
        timeline.append({
            'time': time_point.strftime('%H:%M:%S'),
            'score': score
        })
    
    return {
        'session': session,
        'alerts': alerts,
        'timeline': timeline
    }

def generate_all_data():
    """Generate complete dataset"""
    print("📊 Generating sample data...")
    
    # Generate students and exams
    students = generate_students(15)
    exams = generate_exams(8)
    
    # Generate sessions
    sessions = []
    all_alerts = []
    
    for student in students:
        # Each student takes 1-3 exams
        num_sessions = random.randint(1, 3)
        taken_exams = random.sample(exams, min(num_sessions, len(exams)))
        
        for exam in taken_exams:
            num_alerts = random.randint(5, 30)
            session_data = generate_session_data(student['id'], exam['id'], num_alerts)
            
            sessions.append(session_data['session'])
            all_alerts.extend([{**alert, 'session_id': len(sessions)} for alert in session_data['alerts']])
    
    return {
        'students': students,
        'exams': exams,
        'sessions': sessions,
        'alerts': all_alerts
    }

def save_to_database(data):
    """Save generated data to database"""
    db = ProctorDatabase()
    
    print("💾 Saving to database...")
    
    # Save students (if table exists)
    for student in data['students']:
        try:
            db.cursor.execute('''
                INSERT OR IGNORE INTO students (id, first_name, last_name, email, year, major)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (student['id'], student['first_name'], student['last_name'], 
                  student['email'], student['year'], student['major']))
        except:
            pass
    
    # Save sessions and alerts
    for i, session in enumerate(data['sessions']):
        try:
            session_id = db.create_session(f"sample_{session['student_id']}_{session['exam_id']}")
            
            # Add alerts for this session
            session_alerts = [a for a in data['alerts'] if a.get('session_id') == i]
            for alert in session_alerts:
                db.add_alert(session_id, alert)
            
            # End session
            db.end_session(session_id)
        except Exception as e:
            print(f"  Error saving session: {e}")
    
    db.conn.commit()
    print(f"✅ Saved {len(data['sessions'])} sessions to database")

def save_to_json(data, filename='sample_data.json'):
    """Save generated data to JSON file"""
    output_dir = 'data/samples'
    os.makedirs(output_dir, exist_ok=True)
    
    filepath = os.path.join(output_dir, filename)
    
    # Convert datetime objects to strings
    def convert_to_serializable(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj
    
    with open(filepath, 'w') as f:
        json.dump(data, f, default=convert_to_serializable, indent=2)
    
    print(f"✅ Saved sample data to {filepath}")
    return filepath

def print_summary(data):
    """Print summary of generated data"""
    print("\n" + "=" * 50)
    print("📊 Sample Data Summary")
    print("=" * 50)
    print(f"Students: {len(data['students'])}")
    print(f"Exams: {len(data['exams'])}")
    print(f"Sessions: {len(data['sessions'])}")
    print(f"Alerts: {len(data['alerts'])}")
    
    # Alert statistics
    severities = [a['severity'] for a in data['alerts']]
    print(f"\nAlert Severity Distribution:")
    print(f"  Critical (3): {severities.count(3)}")
    print(f"  Warning (2): {severities.count(2)}")
    print(f"  Info (1): {severities.count(1)}")
    
    # Session statistics
    avg_score = np.mean([s['suspicious_score'] for s in data['sessions']])
    avg_alerts = np.mean([s['alert_count'] for s in data['sessions']])
    print(f"\nAverage suspicious score: {avg_score:.2f}")
    print(f"Average alerts per session: {avg_alerts:.1f}")

def main():
    parser = argparse.ArgumentParser(description='Generate sample data for testing')
    parser.add_argument('--format', choices=['json', 'db', 'both'], default='both',
                       help='Output format')
    parser.add_argument('--output', type=str, default='sample_data.json',
                       help='Output filename for JSON')
    
    args = parser.parse_args()
    
    # Generate data
    data = generate_all_data()
    print_summary(data)
    
    # Save in requested formats
    if args.format in ['json', 'both']:
        save_to_json(data, args.output)
    
    if args.format in ['db', 'both']:
        save_to_database(data)
    
    print("\n✅ Sample data generation complete!")

if __name__ == "__main__":
    main()