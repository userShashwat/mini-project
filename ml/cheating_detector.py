"""
Cheating Detection Module using Deep Learning
Combines multiple modalities for accurate cheating detection
"""
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from collections import deque
import cv2
from ultralytics import YOLO
import os

class CheatingDetector(nn.Module):
    """
    Hybrid deep learning model for cheating detection
    Combines CNN for spatial features and LSTM for temporal patterns
    """
    def __init__(self, num_classes=5, hidden_size=128, num_layers=2):
        super(CheatingDetector, self).__init__()
        
        # YOLO for object detection (pre-trained)
        self.yolo = YOLO('yolov8n.pt')
        
        # CNN for feature extraction from frames
        self.cnn = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1))
        )
        
        # LSTM for temporal modeling
        self.lstm = nn.LSTM(
            input_size=256 + 20,  # CNN features + behavioral features
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.3 if num_layers > 1 else 0
        )
        
        # Attention mechanism
        self.attention = nn.MultiheadAttention(hidden_size, num_heads=4, dropout=0.3)
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes)
        )
        
        # Cheating classes
        self.classes = [
            'normal',
            'cell_phone',
            'book_notes',
            'multiple_people',
            'looking_away'
        ]
        
        # Temporal buffer
        self.frame_buffer = deque(maxlen=30)  # 30 frames ~ 1 second at 30fps
        self.behavior_buffer = deque(maxlen=30)
        
    def forward(self, frames, behavioral_features=None):
        """
        Forward pass
        frames: tensor of shape (batch, seq_len, 3, H, W)
        behavioral_features: tensor of shape (batch, seq_len, 20)
        """
        batch_size, seq_len = frames.shape[:2]
        
        # Extract CNN features for each frame
        cnn_features = []
        for t in range(seq_len):
            x = frames[:, t]  # (batch, 3, H, W)
            x = self.cnn(x)   # (batch, 256, 1, 1)
            x = x.squeeze(-1).squeeze(-1)  # (batch, 256)
            cnn_features.append(x)
        
        cnn_features = torch.stack(cnn_features, dim=1)  # (batch, seq_len, 256)
        
        # Combine with behavioral features if provided
        if behavioral_features is not None:
            combined = torch.cat([cnn_features, behavioral_features], dim=-1)
        else:
            combined = cnn_features
        
        # LSTM
        lstm_out, (hidden, cell) = self.lstm(combined)
        
        # Self-attention
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        
        # Use last time step
        last_out = attn_out[:, -1, :]
        
        # Classification
        logits = self.classifier(last_out)
        probs = F.softmax(logits, dim=-1)
        
        return probs, logits
    
    def predict_frame(self, frame, behavioral_data=None):
        """
        Predict cheating for a single frame
        """
        # Preprocess frame
        frame_resized = cv2.resize(frame, (224, 224))
        frame_tensor = torch.from_numpy(frame_resized).permute(2, 0, 1).float() / 255.0
        frame_tensor = frame_tensor.unsqueeze(0).unsqueeze(0)  # (1, 1, 3, 224, 224)
        
        # Add to buffer
        self.frame_buffer.append(frame_tensor)
        
        if behavioral_data:
            self.behavior_buffer.append(behavioral_data)
        
        # Need at least 10 frames for temporal analysis
        if len(self.frame_buffer) < 10:
            return None
        
        # Prepare sequence
        frames_seq = torch.cat(list(self.frame_buffer), dim=1)  # (1, seq_len, 3, 224, 224)
        
        if self.behavior_buffer:
            behav_seq = torch.stack(list(self.behavior_buffer), dim=1)
        else:
            behav_seq = None
        
        # Inference
        with torch.no_grad():
            probs, _ = self.forward(frames_seq, behav_seq)
        
        return {
            'class': self.classes[torch.argmax(probs[0]).item()],
            'probabilities': {cls: float(prob) for cls, prob in zip(self.classes, probs[0])},
            'cheating_prob': float(1 - probs[0][0])  # Probability of any cheating
        }
    
    def detect_suspicious_objects(self, frame):
        """
        Use YOLO to detect suspicious objects
        """
        results = self.yolo(frame, verbose=False)[0]
        suspicious = []
        
        suspicious_classes = ['cell phone', 'laptop', 'book', 'remote', 'tv']
        
        if results.boxes is not None:
            for box in results.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                name = results.names[cls]
                
                if name in suspicious_classes and conf > 0.5:
                    suspicious.append({
                        'object': name,
                        'confidence': conf,
                        'bbox': box.xyxy[0].tolist()
                    })
        
        return suspicious

# Feature extractor for behavioral data
class BehavioralFeatureExtractor:
    """Extract behavioral features from face landmarks and head pose"""
    
    def __init__(self):
        self.history = deque(maxlen=30)
        
    def extract(self, face_landmarks, head_pose, eye_aspect_ratio):
        """Extract feature vector"""
        features = []
        
        # Head pose
        if head_pose:
            features.extend([
                head_pose.get('yaw', 0),
                head_pose.get('pitch', 0),
                head_pose.get('roll', 0),
                head_pose.get('velocity', 0)
            ])
        else:
            features.extend([0, 0, 0, 0])
        
        # Eye aspect ratio
        features.append(eye_aspect_ratio if eye_aspect_ratio else 0)
        
        # Face position
        if face_landmarks and 'face_center' in face_landmarks:
            center = face_landmarks['face_center']
            features.extend([center[0], center[1]])
        else:
            features.extend([0, 0])
        
        # Face size (distance from camera)
        if face_landmarks and 'face_width' in face_landmarks:
            features.append(face_landmarks['face_width'])
        else:
            features.append(0)
        
        # Temporal features
        self.history.append(features.copy())
        
        if len(self.history) > 5:
            recent = np.array(list(self.history)[-5:])
            features.extend([
                np.std(recent[:, 0]),  # Head movement variance
                np.mean(recent[:, 4]),  # Average eye aspect ratio
                np.max(recent[:, 4]) - np.min(recent[:, 4])  # Eye aspect ratio range
            ])
        else:
            features.extend([0, 0, 0])
        
        # Pad to 20 features
        while len(features) < 20:
            features.append(0)
        
        return torch.tensor([features[:20]], dtype=torch.float32)