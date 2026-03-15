#!/usr/bin/env python
"""
Script to download required ML models
"""
import os
import sys
import argparse
from pathlib import Path

def download_yolo_model():
    """Download YOLOv8 model"""
    print("📥 Downloading YOLOv8 model...")
    try:
        from ultralytics import YOLO
        model = YOLO('yolov8n.pt')
        print("✅ YOLOv8 model downloaded")
    except Exception as e:
        print(f"❌ Error downloading YOLO: {e}")

def download_face_recognition_models():
    """Download face recognition models"""
    print("📥 Downloading face recognition models...")
    try:
        import face_recognition_models
        print("✅ Face recognition models available")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("   Run: pip install face-recognition-models")

def download_all_models():
    """Download all required models"""
    print("=" * 50)
    print("🤖 Downloading ML Models for Proctoring AI")
    print("=" * 50)
    
    download_yolo_model()
    download_face_recognition_models()
    
    print("\n" + "=" * 50)
    print("✅ All models downloaded!")
    print("=" * 50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download ML models')
    parser.add_argument('--model', choices=['yolo', 'face', 'all'], 
                       default='all', help='Model to download')
    
    args = parser.parse_args()
    
    if args.model == 'yolo':
        download_yolo_model()
    elif args.model == 'face':
        download_face_recognition_models()
    else:
        download_all_models()