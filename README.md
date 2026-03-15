# 🎓 AI-Powered Proctoring System

An advanced, real-time exam monitoring system that uses computer vision and machine learning to ensure academic integrity during online exams.

## ✨ Features

*   **Multi-Modal Monitoring**: Combines video (face/object detection) and audio analysis.
*   **Real-Time Alerts**: Detects and flags suspicious activities like multiple faces, mobile phone use, or multiple voices.
*   **Role-Based Access**: Separate interfaces and permissions for **Students**, **Proctors**, and **Admins**.
*   **Live Dashboard**: Proctors can monitor all active exam sessions in real-time.
*   **Machine Learning Integration**: Includes modules for behavior profiling and pattern detection (cheating pattern analysis).
*   **Comprehensive Logging & Reporting**: All sessions and alerts are logged and can be exported.

## 🛠️ Technology Stack

*   **Backend**: Python, Flask, Flask-SocketIO
*   **Frontend**: HTML, CSS, JavaScript
*   **AI/ML**: OpenCV, PyTorch, Ultralytics YOLO, Face Recognition, Scikit-learn
*   **Database**: SQLite
*   **Authentication**: Flask-Login, Flask-Bcrypt

## 🚀 Getting Started

### Prerequisites
*   Python 3.9+
*   Conda (recommended) or pip
*   Git
*   Webcam and Microphone

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/userShashwat/mini-project.git
    cd mini-project
