#!/usr/bin/env python
"""
Script to train behavior models on historical data
"""
import os
import sys
import numpy as np
import json
from datetime import datetime
import argparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.behavior_profiler import BehaviorProfiler
from ml.pattern_detector import PatternDetector
from utils.database import ProctorDatabase

def generate_synthetic_data(num_students=10, num_sessions=5):
    """
    Generate synthetic training data
    """
    print(f"📊 Generating synthetic data for {num_students} students...")
    
    data = []
    for student_id in range(1, num_students + 1):
        student_name = f"student_{student_id}"
        
        for session in range(num_sessions):
            # Generate random behavior sequences
            num_observations = np.random.randint(50, 200)
            
            for obs in range(num_observations):
                # Simulate normal behavior with occasional anomalies
                is_anomaly = np.random.random() < 0.1  # 10% anomaly rate
                
                features = []
                if is_anomaly:
                    # Anomalous behavior
                    features = np.random.normal(5, 2, 20)  # Different distribution
                else:
                    # Normal behavior
                    features = np.random.normal(0, 1, 20)
                
                data.append({
                    'student_id': student_name,
                    'features': features.tolist(),
                    'timestamp': datetime.now().isoformat(),
                    'is_anomaly': is_anomaly
                })
    
    return data

def train_behavior_models(data=None, student_ids=None):
    """
    Train behavior models for students
    """
    if data is None:
        data = generate_synthetic_data()
    
    print("🤖 Training behavior models...")
    
    # Group by student
    student_data = {}
    for item in data:
        student_id = item['student_id']
        if student_ids and student_id not in student_ids:
            continue
            
        if student_id not in student_data:
            student_data[student_id] = []
        student_data[student_id].append(item['features'])
    
    # Train model for each student
    trained_count = 0
    for student_id, features_list in student_data.items():
        if len(features_list) < 50:
            print(f"⚠️ Not enough data for {student_id} (need 50, have {len(features_list)})")
            continue
        
        print(f"  Training model for {student_id}...")
        profiler = BehaviorProfiler(student_id)
        
        # Add features to history
        for features in features_list[:100]:  # Use first 100 for training
            profiler.behavior_history.append(features)
        
        if profiler.train_model():
            trained_count += 1
    
    print(f"✅ Trained {trained_count} models")
    return trained_count

def train_pattern_detector():
    """
    Train pattern detector on historical incidents
    """
    print("🔍 Training pattern detector...")
    
    detector = PatternDetector()
    
    # Generate synthetic incidents
    db = ProctorDatabase()
    sessions = db.get_sessions(limit=20)
    
    for session in sessions:
        alerts = db.get_session_alerts(session['id'])
        for alert in alerts:
            detector.log_incident(
                student_id=session.get('student_id', 'unknown'),
                incident_type=alert['type'],
                timestamp=datetime.fromisoformat(alert['timestamp']),
                confidence=alert.get('score', 0.5)
            )
    
    # Detect and save patterns
    patterns = detector.save_patterns()
    print(f"✅ Pattern detector trained: {len(patterns.get('coordinated', []))} patterns found")
    
    return patterns

def main():
    parser = argparse.ArgumentParser(description='Train behavior models')
    parser.add_argument('--students', type=int, default=10, help='Number of synthetic students')
    parser.add_argument('--sessions', type=int, default=5, help='Sessions per student')
    parser.add_argument('--real-data', action='store_true', help='Use real data from database')
    parser.add_argument('--student-ids', nargs='+', help='Specific student IDs to train')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("🧠 Behavior Model Training")
    print("=" * 50)
    
    if args.real_data:
        print("📊 Using real data from database")
        train_behavior_models(student_ids=args.student_ids)
    else:
        print(f"📊 Generating synthetic data ({args.students} students, {args.sessions} sessions each)")
        data = generate_synthetic_data(args.students, args.sessions)
        train_behavior_models(data, args.student_ids)
    
    train_pattern_detector()
    
    print("\n" + "=" * 50)
    print("✅ Training complete!")
    print("=" * 50)

if __name__ == "__main__":
    main()