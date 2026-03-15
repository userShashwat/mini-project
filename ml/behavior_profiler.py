"""
Behavior Profiling Module using Machine Learning
Tracks and learns individual student behavior patterns
"""
import numpy as np
import pickle
import os
from collections import deque
from datetime import datetime
import json
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

class BehaviorProfiler:
    """
    Adaptive behavior profiling module that learns individual student patterns
    """
    def __init__(self, student_id, model_dir='ml/models'):
        self.student_id = student_id
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        # Behavior history
        self.behavior_history = deque(maxlen=1000)
        self.timestamps = deque(maxlen=1000)
        
        # Feature buffers
        self.head_pose_history = deque(maxlen=100)
        self.gaze_history = deque(maxlen=100)
        self.face_position_history = deque(maxlen=100)
        self.blink_rate_history = deque(maxlen=50)
        
        # ML models
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Load existing model if available
        self.load_model()
        
        # Statistics
        self.total_observations = 0
        self.anomaly_count = 0
        self.baseline_profile = {}
        
    def extract_features(self, face_landmarks=None, head_pose=None, 
                        eye_aspect_ratio=None, frame=None):
        """
        Extract behavioral features from multiple inputs
        """
        features = []
        feature_names = []
        
        # Head pose features
        if head_pose:
            features.extend([
                head_pose.get('yaw', 0),    # Left-right rotation
                head_pose.get('pitch', 0),   # Up-down movement
                head_pose.get('roll', 0),     # Tilt
                head_pose.get('velocity', 0)  # Speed of movement
            ])
            feature_names.extend(['yaw', 'pitch', 'roll', 'head_velocity'])
            self.head_pose_history.append(head_pose)
        
        # Eye features
        if eye_aspect_ratio:
            features.append(eye_aspect_ratio)  # Blink detection
            feature_names.append('ear')
            
            # Calculate blink rate
            if len(self.blink_rate_history) > 0:
                blink_rate = sum(1 for ear in list(self.blink_rate_history)[-30:] 
                               if ear < 0.2) / 30
                features.append(blink_rate)
                feature_names.append('blink_rate')
            self.blink_rate_history.append(eye_aspect_ratio)
        
        # Face position features
        if face_landmarks and 'face_center' in face_landmarks:
            center = face_landmarks['face_center']
            features.extend([center[0], center[1]])
            feature_names.extend(['face_x', 'face_y'])
            self.face_position_history.append(center)
        
        # Temporal features (changes over time)
        if len(self.behavior_history) > 10:
            recent = list(self.behavior_history)[-10:]
            features.extend([
                np.std([f[0] for f in recent if len(f) > 0]) if recent else 0,
                np.mean([f[1] for f in recent if len(f) > 1]) if recent else 0,
                self.calculate_entropy(recent)
            ])
            feature_names.extend(['movement_std', 'avg_position', 'behavior_entropy'])
        
        # Pad features to ensure consistent length
        while len(features) < 20:
            features.append(0)
            feature_names.append(f'padding_{len(features)}')
        
        return np.array(features[:20]).reshape(1, -1), feature_names[:20]
    
    def update_profile(self, features, is_training_mode=False):
        """
        Update behavior profile with new observations
        """
        self.behavior_history.append(features.flatten())
        self.timestamps.append(datetime.now())
        self.total_observations += 1
        
        if is_training_mode:
            # During training: build baseline profile
            if len(self.behavior_history) >= 100 and not self.is_trained:
                self.train_model()
            return 0.0
        else:
            # During exam: detect anomalies
            if self.is_trained:
                anomaly_score = self.detect_anomaly(features)
                if anomaly_score > 0.7:
                    self.anomaly_count += 1
                return anomaly_score
            return 0.0
    
    def train_model(self):
        """Train isolation forest on normal behavior patterns"""
        if len(self.behavior_history) < 100:
            print(f"⚠️ Not enough data to train model for {self.student_id}")
            return False
        
        X = np.array(list(self.behavior_history))
        X = X.reshape(X.shape[0], -1)
        
        # Remove any NaN or inf values
        X = np.nan_to_num(X)
        
        try:
            self.scaler.fit(X)
            X_scaled = self.scaler.transform(X)
            self.model.fit(X_scaled)
            self.is_trained = True
            
            # Calculate baseline statistics
            self.baseline_profile = {
                'mean': np.mean(X, axis=0).tolist(),
                'std': np.std(X, axis=0).tolist(),
                'samples': len(X),
                'trained_at': datetime.now().isoformat()
            }
            
            # Save the model
            self.save_model()
            print(f"✅ Behavior model trained for {self.student_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error training model: {e}")
            return False
    
    def detect_anomaly(self, features):
        """Detect if current behavior is anomalous"""
        if not self.is_trained:
            return 0.0
        
        try:
            features = features.reshape(1, -1)
            features = np.nan_to_num(features)
            features_scaled = self.scaler.transform(features)
            score = self.model.score_samples(features_scaled)[0]
            
            # Convert to 0-1 anomaly score (lower score = more anomalous)
            # Isolation Forest returns negative scores for anomalies
            anomaly_score = 1 - (score + 0.5)  # Normalize to 0-1
            return max(0, min(1, anomaly_score))
            
        except Exception as e:
            print(f"❌ Error detecting anomaly: {e}")
            return 0.0
    
    def calculate_entropy(self, sequence):
        """Calculate entropy of behavior sequence"""
        try:
            from scipy.stats import entropy
            if len(sequence) < 2:
                return 0
            
            # Convert sequence to discrete values
            flat_sequence = np.array(sequence).flatten()
            if len(flat_sequence) == 0:
                return 0
            
            # Create histogram
            hist, _ = np.histogram(flat_sequence, bins=10)
            hist = hist / hist.sum()
            return entropy(hist)
            
        except Exception as e:
            return 0
    
    def get_profile(self):
        """Get current behavior profile"""
        return {
            'student_id': self.student_id,
            'is_trained': self.is_trained,
            'total_observations': self.total_observations,
            'anomaly_count': self.anomaly_count,
            'anomaly_rate': self.anomaly_count / max(self.total_observations, 1),
            'baseline': self.baseline_profile,
            'recent_behavior': list(self.behavior_history)[-10:] if self.behavior_history else []
        }
    
    def save_model(self):
        """Save trained model to disk"""
        if not self.is_trained:
            return
        
        model_path = os.path.join(self.model_dir, f'behavior_{self.student_id}.pkl')
        scaler_path = os.path.join(self.model_dir, f'scaler_{self.student_id}.pkl')
        profile_path = os.path.join(self.model_dir, f'profile_{self.student_id}.json')
        
        try:
            joblib.dump(self.model, model_path)
            joblib.dump(self.scaler, scaler_path)
            
            with open(profile_path, 'w') as f:
                json.dump({
                    'student_id': self.student_id,
                    'baseline': self.baseline_profile,
                    'total_observations': self.total_observations,
                    'trained_at': datetime.now().isoformat()
                }, f)
                
            print(f"💾 Model saved for {self.student_id}")
            
        except Exception as e:
            print(f"❌ Error saving model: {e}")
    
    def load_model(self):
        """Load trained model from disk"""
        model_path = os.path.join(self.model_dir, f'behavior_{self.student_id}.pkl')
        scaler_path = os.path.join(self.model_dir, f'scaler_{self.student_id}.pkl')
        profile_path = os.path.join(self.model_dir, f'profile_{self.student_id}.json')
        
        try:
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                self.is_trained = True
                
                if os.path.exists(profile_path):
                    with open(profile_path, 'r') as f:
                        profile = json.load(f)
                        self.baseline_profile = profile.get('baseline', {})
                        self.total_observations = profile.get('total_observations', 0)
                
                print(f"📂 Loaded existing model for {self.student_id}")
                
        except Exception as e:
            print(f"⚠️ Could not load model for {self.student_id}: {e}")