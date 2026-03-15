# verify_install.py
import sys

def check_version(package_name, import_name=None):
    if import_name is None:
        import_name = package_name
    try:
        module = __import__(import_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"✅ {package_name:20} {version}")
        return True
    except ImportError as e:
        print(f"❌ {package_name:20} Not installed - {e}")
        return False

print("=" * 50)
print("Verifying Proctoring AI Dependencies")
print("=" * 50)

# Core
check_version("OpenCV", "cv2")
check_version("NumPy", "numpy")
check_version("PyTorch", "torch")
check_version("Ultralytics", "ultralytics")
check_version("Face Recognition", "face_recognition")
check_version("SoundDevice", "sounddevice")

# Web
check_version("Flask", "flask")
check_version("Flask-SocketIO", "flask_socketio")

# ML
check_version("Scikit-learn", "sklearn")
check_version("Pandas", "pandas")
check_version("Matplotlib", "matplotlib")

# Utils
check_version("Pillow", "PIL")
check_version("PyYAML", "yaml")
check_version("ReportLab", "reportlab")

print("=" * 50)