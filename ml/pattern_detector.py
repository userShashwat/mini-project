"""
Pattern Detection Module
Detects coordinated cheating patterns across multiple students
"""
import numpy as np
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import json
import os
from scipy.cluster.hierarchy import fclusterdata
from scipy.spatial.distance import pdist

class PatternDetector:
    """
    Detects sophisticated cheating patterns across multiple students
    """
    def __init__(self, storage_dir='ml/patterns'):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        
        # Incident logs
        self.incident_log = defaultdict(list)
        self.session_log = defaultdict(dict)
        
        # Pattern thresholds
        self.thresholds = {
            'coordinated_looking': 0.7,
            'time_window': 5,  # seconds
            'group_size': 3,
            'proximity_threshold': 2,  # seconds
            'correlation_threshold': 0.8
        }
        
        # Load existing patterns
        self.load_patterns()
        
    def log_incident(self, student_id, incident_type, timestamp, confidence, metadata=None):
        """
        Log a suspicious incident
        """
        incident = {
            'student_id': student_id,
            'type': incident_type,
            'timestamp': timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(timestamp),
            'confidence': confidence,
            'metadata': metadata or {}
        }
        
        self.incident_log[student_id].append(incident)
        
        # Keep only last 1000 incidents per student
        if len(self.incident_log[student_id]) > 1000:
            self.incident_log[student_id] = self.incident_log[student_id][-1000:]
        
        return incident
    
    def detect_coordinated_cheating(self, time_window=300):
        """
        Detect groups of students exhibiting similar suspicious behavior
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=time_window)
        
        # Collect all incidents in time window
        recent_incidents = []
        for student_id, incidents in self.incident_log.items():
            for inc in incidents:
                if inc['timestamp'] > window_start:
                    recent_incidents.append({
                        'student': student_id,
                        'time': inc['timestamp'],
                        'type': inc['type'],
                        'confidence': inc['confidence']
                    })
        
        if len(recent_incidents) < self.thresholds['group_size']:
            return []
        
        # Group by incident type
        by_type = defaultdict(list)
        for inc in recent_incidents:
            by_type[inc['type']].append(inc)
        
        coordinated_patterns = []
        
        for incident_type, incidents in by_type.items():
            # Sort by time
            incidents.sort(key=lambda x: x['time'])
            
            # Cluster by time proximity
            clusters = self.cluster_by_time(incidents)
            
            # Analyze each cluster
            for cluster in clusters:
                if len(cluster) >= self.thresholds['group_size']:
                    pattern_score = self.calculate_coordination_score(cluster)
                    
                    if pattern_score >= self.thresholds['coordinated_looking']:
                        coordinated_patterns.append({
                            'type': incident_type,
                            'students': [c['student'] for c in cluster],
                            'times': [c['time'].isoformat() for c in cluster],
                            'score': pattern_score,
                            'confidence_mean': np.mean([c['confidence'] for c in cluster]),
                            'time_span': (max(c['time'] for c in cluster) - 
                                        min(c['time'] for c in cluster)).total_seconds()
                        })
        
        return coordinated_patterns
    
    def cluster_by_time(self, incidents, max_gap=5):
        """
        Cluster incidents by time proximity
        """
        if not incidents:
            return []
        
        clusters = []
        current_cluster = [incidents[0]]
        
        for i in range(1, len(incidents)):
            time_gap = (incidents[i]['time'] - incidents[i-1]['time']).total_seconds()
            
            if time_gap <= max_gap:
                current_cluster.append(incidents[i])
            else:
                if len(current_cluster) >= 2:
                    clusters.append(current_cluster)
                current_cluster = [incidents[i]]
        
        if len(current_cluster) >= 2:
            clusters.append(current_cluster)
        
        return clusters
    
    def calculate_coordination_score(self, cluster):
        """
        Calculate how coordinated the behavior is
        """
        if len(cluster) < 2:
            return 0.0
        
        # Extract times
        times = [c['time'].timestamp() for c in cluster]
        
        # Calculate time variance (lower variance = more coordinated)
        time_variance = np.var(times)
        max_variance = 100  # 100 seconds variance = low coordination
        coordination_score = 1 - min(time_variance / max_variance, 1)
        
        # Weight by confidence
        avg_confidence = np.mean([c['confidence'] for c in cluster])
        
        return coordination_score * avg_confidence
    
    def detect_escalating_pattern(self, student_id, time_window=600):
        """
        Detect if a student's behavior is escalating over time
        """
        incidents = self.incident_log.get(student_id, [])
        if len(incidents) < 10:
            return None
        
        # Sort by time
        incidents.sort(key=lambda x: x['timestamp'])
        
        # Get incidents in time window
        now = datetime.now()
        recent = [inc for inc in incidents if inc['timestamp'] > now - timedelta(seconds=time_window)]
        
        if len(recent) < 5:
            return None
        
        # Calculate moving average of confidence
        window = min(3, len(recent) // 2)
        moving_avgs = []
        
        for i in range(len(recent) - window + 1):
            avg = np.mean([inc['confidence'] for inc in recent[i:i+window]])
            moving_avgs.append(avg)
        
        # Check if trend is increasing
        if len(moving_avgs) >= 2:
            first_avg = np.mean(moving_avgs[:len(moving_avgs)//3])
            last_avg = np.mean(moving_avgs[-len(moving_avgs)//3:])
            
            trend = last_avg - first_avg
            
            if trend > 0.3:  # Significant increase
                return {
                    'student_id': student_id,
                    'trend': float(trend),
                    'current_score': float(last_avg),
                    'increase_rate': float(trend / (time_window / 60)),  # per minute
                    'alert_count': len(recent)
                }
        
        return None
    
    def detect_correlation_patterns(self, session_ids=None):
        """
        Detect correlations between different students' behavior
        """
        # Get incidents for specified sessions or all
        all_incidents = []
        for student_id, incidents in self.incident_log.items():
            if session_ids is None or student_id in session_ids:
                for inc in incidents:
                    all_incidents.append({
                        'student': student_id,
                        'time': inc['timestamp'].timestamp(),
                        'type': inc['type'],
                        'confidence': inc['confidence']
                    })
        
        if len(all_incidents) < 10:
            return []
        
        # Create time series for each student
        students = set(inc['student'] for inc in all_incidents)
        time_series = defaultdict(list)
        
        min_time = min(inc['time'] for inc in all_incidents)
        max_time = max(inc['time'] for inc in all_incidents)
        
        # Create bins (10-second intervals)
        bins = np.arange(min_time, max_time, 10)
        
        for student in students:
            student_inc = [inc for inc in all_incidents if inc['student'] == student]
            series = np.zeros(len(bins))
            
            for inc in student_inc:
                bin_idx = np.digitize(inc['time'], bins) - 1
                if 0 <= bin_idx < len(series):
                    series[bin_idx] += inc['confidence']
            
            time_series[student] = series
        
        # Calculate correlations
        correlations = []
        student_list = list(students)
        
        for i in range(len(student_list)):
            for j in range(i+1, len(student_list)):
                s1 = student_list[i]
                s2 = student_list[j]
                
                corr = np.corrcoef(time_series[s1], time_series[s2])[0, 1]
                
                if not np.isnan(corr) and abs(corr) > self.thresholds['correlation_threshold']:
                    correlations.append({
                        'student1': s1,
                        'student2': s2,
                        'correlation': float(corr),
                        'pattern': 'positive' if corr > 0 else 'negative'
                    })
        
        return correlations
    
    def save_patterns(self):
        """Save detected patterns to disk"""
        patterns = {
            'coordinated': self.detect_coordinated_cheating(),
            'escalating': [self.detect_escalating_pattern(sid) 
                          for sid in self.incident_log.keys()],
            'correlations': self.detect_correlation_patterns(),
            'updated_at': datetime.now().isoformat()
        }
        
        path = os.path.join(self.storage_dir, 'patterns.json')
        with open(path, 'w') as f:
            json.dump(patterns, f, indent=2, default=str)
        
        return patterns
    
    def load_patterns(self):
        """Load patterns from disk"""
        path = os.path.join(self.storage_dir, 'patterns.json')
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def generate_alert(self, pattern):
        """
        Generate alert based on detected pattern
        """
        severity = 1  # Default low
        
        if pattern['score'] > 0.9:
            severity = 3  # Critical
        elif pattern['score'] > 0.7:
            severity = 2  # Warning
        
        return {
            'type': 'pattern_detected',
            'subtype': pattern['type'],
            'severity': severity,
            'message': f"Detected {pattern['type']} involving {len(pattern['students'])} students",
            'details': pattern,
            'timestamp': datetime.now().isoformat()
        }