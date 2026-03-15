"""
Feature Extraction Module
Extracts and engineers features from raw data
"""
import numpy as np
import cv2
from collections import deque
from scipy import signal
from scipy.fft import fft
import math

class FeatureExtractor:
    """
    Extracts features from video, audio, and behavioral data
    """
    def __init__(self):
        self.face_history = deque(maxlen=30)
        self.audio_history = deque(maxlen=100)
        self.motion_history = deque(maxlen=30)
        
    def extract_face_features(self, face_landmarks, head_pose):
        """
        Extract features from face landmarks and head pose
        """
        features = {}
        
        if face_landmarks:
            # Eye aspect ratio
            left_eye = face_landmarks.get('left_eye', [])
            right_eye = face_landmarks.get('right_eye', [])
            
            if left_eye and right_eye:
                left_ear = self.eye_aspect_ratio(left_eye)
                right_ear = self.eye_aspect_ratio(right_eye)
                features['left_ear'] = left_ear
                features['right_ear'] = right_ear
                features['avg_ear'] = (left_ear + right_ear) / 2
                features['ear_diff'] = abs(left_ear - right_ear)
            
            # Mouth aspect ratio (for talking detection)
            mouth = face_landmarks.get('mouth', [])
            if mouth:
                features['mar'] = self.mouth_aspect_ratio(mouth)
            
            # Face bounding box
            if 'face_bbox' in face_landmarks:
                bbox = face_landmarks['face_bbox']
                features['face_width'] = bbox[2] - bbox[0]
                features['face_height'] = bbox[3] - bbox[1]
                features['face_area'] = features['face_width'] * features['face_height']
        
        if head_pose:
            features.update({
                'head_yaw': head_pose.get('yaw', 0),
                'head_pitch': head_pose.get('pitch', 0),
                'head_roll': head_pose.get('roll', 0),
                'head_velocity': head_pose.get('velocity', 0)
            })
        
        # Temporal features
        self.face_history.append(features.copy())
        
        if len(self.face_history) > 5:
            recent = list(self.face_history)[-5:]
            
            # Calculate statistics over recent frames
            for key in ['avg_ear', 'head_yaw', 'head_pitch']:
                if key in features:
                    values = [f.get(key, 0) for f in recent if key in f]
                    if values:
                        features[f'{key}_std'] = np.std(values)
                        features[f'{key}_mean'] = np.mean(values)
                        features[f'{key}_range'] = max(values) - min(values)
        
        return features
    
    def extract_audio_features(self, audio_data, sample_rate=16000):
        """
        Extract features from audio data
        """
        features = {}
        
        if audio_data is None or len(audio_data) == 0:
            return features
        
        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Energy features
        features['energy'] = np.sqrt(np.mean(audio_data**2))
        features['peak_energy'] = np.max(np.abs(audio_data))
        
        # Zero crossing rate (for voice activity)
        zcr = np.sum(np.abs(np.diff(np.sign(audio_data)))) / (2 * len(audio_data))
        features['zero_crossing_rate'] = zcr
        
        # Spectral features
        try:
            spectrum = fft(audio_data)
            magnitude = np.abs(spectrum[:len(spectrum)//2])
            freqs = np.fft.fftfreq(len(audio_data), 1/sample_rate)[:len(spectrum)//2]
            
            # Dominant frequency
            dominant_idx = np.argmax(magnitude[1:]) + 1  # Skip DC
            features['dominant_freq'] = abs(freqs[dominant_idx])
            
            # Spectral centroid
            if np.sum(magnitude) > 0:
                features['spectral_centroid'] = np.sum(freqs * magnitude) / np.sum(magnitude)
            
            # Spectral bandwidth
            centroid = features.get('spectral_centroid', 0)
            features['spectral_bandwidth'] = np.sqrt(
                np.sum(((freqs - centroid) ** 2) * magnitude) / np.sum(magnitude)
            )
        except:
            pass
        
        # MFCC-like features (simplified)
        try:
            # Mel-scale filterbank
            mel_banks = self.mel_filterbank(audio_data, sample_rate)
            features.update(mel_banks)
        except:
            pass
        
        # Temporal features
        self.audio_history.append(features.copy())
        
        if len(self.audio_history) > 10:
            recent_energy = [f.get('energy', 0) for f in list(self.audio_history)[-10:]]
            features['energy_std'] = np.std(recent_energy)
            features['energy_mean'] = np.mean(recent_energy)
            features['voice_activity'] = features['energy'] > 0.02  # Simple threshold
        
        return features
    
    def extract_motion_features(self, flow):
        """
        Extract features from optical flow
        """
        features = {}
        
        if flow is None:
            return features
        
        # Separate flow components
        fx = flow[..., 0]
        fy = flow[..., 1]
        
        # Magnitude and direction
        magnitude = np.sqrt(fx**2 + fy**2)
        direction = np.arctan2(fy, fx)
        
        features['mean_motion'] = np.mean(magnitude)
        features['max_motion'] = np.max(magnitude)
        features['motion_std'] = np.std(magnitude)
        
        # Motion histogram
        hist, _ = np.histogram(direction[magnitude > 1], bins=8, range=(-np.pi, np.pi))
        for i, h in enumerate(hist):
            features[f'motion_dir_{i}'] = h / (np.sum(hist) + 1e-6)
        
        # Motion concentration (entropy)
        probs = hist / (np.sum(hist) + 1e-6)
        entropy = -np.sum(probs * np.log2(probs + 1e-6))
        features['motion_entropy'] = entropy
        
        # Temporal features
        self.motion_history.append(features.copy())
        
        if len(self.motion_history) > 5:
            recent_motion = [f.get('mean_motion', 0) for f in list(self.motion_history)[-5:]]
            features['motion_acceleration'] = np.diff(recent_motion).mean() if len(recent_motion) > 1 else 0
        
        return features
    
    def eye_aspect_ratio(self, eye_points):
        """
        Calculate eye aspect ratio
        """
        try:
            # Vertical distances
            A = np.linalg.norm(eye_points[1] - eye_points[5])
            B = np.linalg.norm(eye_points[2] - eye_points[4])
            
            # Horizontal distance
            C = np.linalg.norm(eye_points[0] - eye_points[3])
            
            # EAR = (A + B) / (2 * C)
            ear = (A + B) / (2.0 * C + 1e-6)
            return float(ear)
        except:
            return 0.0
    
    def mouth_aspect_ratio(self, mouth_points):
        """
        Calculate mouth aspect ratio (for talking detection)
        """
        try:
            # Vertical distances
            A = np.linalg.norm(mouth_points[2] - mouth_points[6])
            B = np.linalg.norm(mouth_points[3] - mouth_points[5])
            
            # Horizontal distance
            C = np.linalg.norm(mouth_points[0] - mouth_points[4])
            
            # MAR = (A + B) / (2 * C)
            mar = (A + B) / (2.0 * C + 1e-6)
            return float(mar)
        except:
            return 0.0
    
    def mel_filterbank(self, audio_data, sample_rate, n_filters=13):
        """
        Simplified mel filterbank features
        """
        features = {}
        
        try:
            # Simple spectrogram
            frequencies, times, spectrogram = signal.spectrogram(
                audio_data, 
                fs=sample_rate,
                nperseg=min(512, len(audio_data))
            )
            
            # Create mel filters (simplified)
            mel_min = 0
            mel_max = 2595 * math.log10(1 + sample_rate/2 / 700)
            mel_points = np.linspace(mel_min, mel_max, n_filters + 2)
            hz_points = 700 * (10**(mel_points / 2595) - 1)
            
            bin_indices = np.floor((len(frequencies) - 1) * hz_points / (sample_rate/2)).astype(int)
            bin_indices = np.clip(bin_indices, 0, len(frequencies)-1)
            
            # Apply filters
            filter_banks = np.zeros((n_filters, spectrogram.shape[1]))
            
            for i in range(n_filters):
                start = bin_indices[i]
                center = bin_indices[i+1]
                end = bin_indices[i+2]
                
                for t in range(spectrogram.shape[1]):
                    if start < center:
                        filter_banks[i, t] += np.sum(spectrogram[start:center, t] * 
                                                     np.linspace(0, 1, center-start))
                    if center < end:
                        filter_banks[i, t] += np.sum(spectrogram[center:end, t] * 
                                                     np.linspace(1, 0, end-center))
            
            # Take log
            filter_banks = np.log(filter_banks + 1e-6)
            
            # DCT (simplified MFCC)
            mfcc = np.zeros((n_filters, spectrogram.shape[1]))
            for k in range(n_filters):
                for n in range(n_filters):
                    mfcc[k] += filter_banks[n] * math.cos(math.pi * k * (2*n + 1) / (2 * n_filters))
            
            # Store first few coefficients
            for i in range(min(5, n_filters)):
                features[f'mfcc_{i}'] = float(np.mean(mfcc[i]))
                
        except Exception as e:
            pass
        
        return features
    
    def extract_all_features(self, frame, face_landmarks, head_pose, 
                            audio_data, flow):
        """
        Extract all features from all modalities
        """
        all_features = {}
        
        # Face features
        face_feats = self.extract_face_features(face_landmarks, head_pose)
        all_features.update(face_feats)
        
        # Audio features
        audio_feats = self.extract_audio_features(audio_data)
        all_features.update(audio_feats)
        
        # Motion features
        motion_feats = self.extract_motion_features(flow)
        all_features.update(motion_feats)
        
        # Frame-level features
        if frame is not None:
            all_features['brightness'] = np.mean(frame)
            all_features['contrast'] = np.std(frame)
            
            # Edge density (as a measure of scene complexity)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            all_features['edge_density'] = np.sum(edges > 0) / edges.size
        
        return all_features