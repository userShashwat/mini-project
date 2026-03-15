
"""
Flask web application for Proctoring AI
"""
from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import cv2
import json
import threading
import time
from datetime import datetime
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import authentication modules
from auth import auth_bp, login_manager, bcrypt, init_auth_db, login_required, role_required
from flask_login import current_user

# Import your modules
try:
    from modules.video.capture import VideoCapture
    from modules.video.face_detector import FaceDetector
    from modules.video.object_detector import ObjectDetector
    from modules.audio.recorder import AudioRecorder
    from modules.audio.analyzer import AudioAnalyzer
    from modules.core.decision_engine import DecisionEngine
    from modules.core.alert_system import AlertSystem
    from modules.core.session_manager import SessionManager
    from utils.database import ProctorDatabase
    print("✅ All modules imported successfully")
except ImportError as e:
    print(f"⚠️ Module import warning: {e}")

# Initialize Flask app with explicit template folder
template_dir = os.path.abspath('web/templates')
static_dir = os.path.abspath('web/static')
print(f"📁 Template folder: {template_dir}")
print(f"📁 Static folder: {static_dir}")

app = Flask(__name__, 
            template_folder=template_dir,
            static_folder=static_dir)
app.config['SECRET_KEY'] = 'proctoring-ai-secret-key'
app.config['UPLOAD_FOLDER'] = 'data/recordings'

# Initialize authentication
init_auth_db()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please login to access this page.'
login_manager.login_message_category = 'warning'
bcrypt.init_app(app)

# Register auth blueprint
app.register_blueprint(auth_bp)

# Add context processor for user
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
CORS(app)

# Global variables
active_sessions = {}
db = None

# Try to initialize database
try:
    db = ProctorDatabase()
    print("✅ Database initialized")
except Exception as e:
    print(f"⚠️ Database warning: {e}")

# Ensure directories exist
os.makedirs('data/recordings', exist_ok=True)
os.makedirs('data/screenshots', exist_ok=True)
os.makedirs('data/logs', exist_ok=True)

class ExamSession:
    """Represents an active exam session"""
    def __init__(self, session_id, student_name, exam_name):
        self.session_id = session_id
        self.student_name = student_name
        self.exam_name = exam_name
        self.start_time = datetime.now()
        self.is_active = True
        self.suspicious_score = 0.0
        self.frame_count = 0
        self.alerts = []
        
        # Initialize modules if available
        try:
            self.video_capture = VideoCapture() if 'VideoCapture' in globals() else None
            self.face_detector = FaceDetector() if 'FaceDetector' in globals() else None
            self.object_detector = ObjectDetector() if 'ObjectDetector' in globals() else None
            print(f"✅ Session {session_id} created for {student_name}")
        except Exception as e:
            print(f"⚠️ Session module warning: {e}")
    
    def start(self):
        """Start all modules"""
        try:
            if hasattr(self, 'video_capture') and self.video_capture:
                self.video_capture.start()
            self.is_active = True
        except Exception as e:
            print(f"⚠️ Start warning: {e}")
    
    def get_frame(self):
        """Get current frame with annotations"""
        if not hasattr(self, 'video_capture') or not self.video_capture:
            # Return a blank frame if camera not available
            import numpy as np
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, f"Session: {self.session_id}", (50, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            return frame
        
        frame = self.video_capture.get_frame()
        if frame is not None:
            self.suspicious_score = min(1.0, self.frame_count / 1000)  # Demo score
            self.frame_count += 1
            
            # Add overlay
            cv2.putText(frame, f"Score: {self.suspicious_score:.2f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Student: {self.student_name}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        return frame
    
    def stop(self):
        """Stop all modules"""
        self.is_active = False
        try:
            if hasattr(self, 'video_capture') and self.video_capture:
                self.video_capture.stop()
        except Exception as e:
            print(f"⚠️ Stop warning: {e}")

# Routes - Public
@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/test')
def test():
    """Simple test route"""
    return """
    <html>
    <head><title>Test Page</title></head>
    <body style="background: #1a1a2e; color: white; font-family: Arial; padding: 20px;">
        <h1 style="color: #e94560;">✅ Flask is Working!</h1>
        <p>Server is running correctly.</p>
        <p>Time: {}</p>
        <p><a href="/" style="color: white;">Go to Home</a></p>
        <p><a href="/auth/login" style="color: white;">Go to Login</a></p>
        <p><a href="/auth/register" style="color: white;">Go to Register</a></p>
    </body>
    </html>
    """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

# Routes - Protected (require login)
@app.route('/exam')
@login_required
def exam_page():
    """Exam taking page"""
    session_id = request.args.get('session', 'default')
    student_name = request.args.get('student', current_user.username)
    exam_name = request.args.get('exam', 'General Exam')
    return render_template('exam.html', 
                         session_id=session_id,
                         student_name=student_name,
                         exam_name=exam_name)

@app.route('/proctor')
@login_required
@role_required('admin', 'proctor')
def proctor_dashboard():
    """Proctor monitoring dashboard"""
    return render_template('proctor_dashboard.html')

@app.route('/admin')
@login_required
@role_required('admin')
def admin_panel():
    """Admin panel"""
    return render_template('admin.html')

# API Endpoints
@app.route('/api/start_session', methods=['POST'])
@login_required
def start_session():
    """Start a new exam session"""
    data = request.json
    session_id = data.get('session_id', f"session_{len(active_sessions)}")
    student_name = data.get('student_name', current_user.username)
    exam_name = data.get('exam_name', 'General Exam')
    
    session = ExamSession(session_id, student_name, exam_name)
    session.start()
    active_sessions[session_id] = session
    
    return jsonify({
        'status': 'success',
        'session_id': session_id,
        'message': f'Session started for {student_name}'
    })

@app.route('/api/stop_session/<session_id>', methods=['POST'])
@login_required
def stop_session(session_id):
    """Stop an exam session"""
    if session_id in active_sessions:
        active_sessions[session_id].stop()
        del active_sessions[session_id]
        return jsonify({'status': 'success', 'message': 'Session stopped'})
    return jsonify({'status': 'error', 'message': 'Session not found'}), 404

@app.route('/api/sessions')
@login_required
def get_sessions():
    """Get all active sessions"""
    sessions_list = []
    for sid, session in active_sessions.items():
        sessions_list.append({
            'id': sid,
            'student': session.student_name,
            'exam': session.exam_name,
            'start_time': session.start_time.strftime('%H:%M:%S'),
            'score': session.suspicious_score,
            'active': session.is_active,
            'duration': str(datetime.now() - session.start_time).split('.')[0]
        })
    return jsonify(sessions_list)

@app.route('/api/session/<session_id>/alerts')
@login_required
def get_session_alerts(session_id):
    """Get alerts for a session"""
    if session_id in active_sessions:
        # Return dummy alerts for demo
        alerts = [
            {'type': 'info', 'severity': 1, 'message': 'Session started', 'timestamp': datetime.now().isoformat()},
            {'type': 'warning', 'severity': 2, 'message': 'Multiple faces detected', 'timestamp': datetime.now().isoformat()}
        ]
        return jsonify(alerts)
    return jsonify([])

@app.route('/api/session/<session_id>/stats')
@login_required
def get_session_stats(session_id):
    """Get session statistics"""
    if session_id in active_sessions:
        session = active_sessions[session_id]
        return jsonify({
            'frame_count': session.frame_count,
            'suspicious_score': session.suspicious_score,
            'face_count': 1,
            'objects_detected': 0,
            'suspicious_objects': False,
            'audio_active': False
        })
    return jsonify({})

@app.route('/api/proctor/intervene/<session_id>', methods=['POST'])
@login_required
@role_required('admin', 'proctor')
def proctor_intervene(session_id):
    """Proctor intervention"""
    data = request.json
    action = data.get('action', 'warn')
    message = data.get('message', '')
    
    if session_id in active_sessions:
        if action == 'warn':
            socketio.emit('proctor_message', {
                'session_id': session_id,
                'message': message,
                'type': 'warning'
            })
        elif action == 'terminate':
            active_sessions[session_id].stop()
            del active_sessions[session_id]
            return jsonify({'status': 'terminated'})
        return jsonify({'status': 'success', 'action': action})
    return jsonify({'status': 'error'}), 404

# Video Streaming
def generate_frames(session_id):
    """Generate video frames for streaming"""
    while True:
        if session_id in active_sessions:
            frame = active_sessions[session_id].get_frame()
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            # Return a blank frame if session not found
            import numpy as np
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "No Active Session", (200, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.03)  # ~30 FPS

@app.route('/video_feed/<session_id>')
@login_required
def video_feed(session_id):
    """Video streaming route"""
    return Response(generate_frames(session_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# WebSocket events
@socketio.on('connect')
def handle_connect():
    print(f'✅ Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'❌ Client disconnected: {request.sid}')

@socketio.on('join_session')
def handle_join_session(data):
    """Student joins exam session"""
    session_id = data.get('session_id')
    if session_id:
        from flask_socketio import join_room
        join_room(session_id)
        emit('joined', {'session_id': session_id})
        print(f"📌 Client joined session: {session_id}")

@socketio.on('alert_update')
def handle_alert_update(data):
    """Broadcast alert updates"""
    emit('new_alert', data, broadcast=True)

def run_web_server(port=5000, debug=False):
    """Run the web server - THIS BLOCKS UNTIL SERVER STOPS"""
    print("\n" + "="*50)
    print("🚀 PROCTORING AI WEB SERVER")
    print("="*50)
    print(f"🌐 URL: http://localhost:{port}")
    print(f"📊 Proctor: http://localhost:{port}/proctor")
    print(f"📝 Exam: http://localhost:{port}/exam")
    print(f"🔧 Admin: http://localhost:{port}/admin")
    print(f"🧪 Test: http://localhost:{port}/test")
    print(f"🔐 Login: http://localhost:{port}/auth/login")
    print(f"📝 Register: http://localhost:{port}/auth/register")
    print("="*50)
    print("Press Ctrl+C to stop the server")
    print("="*50 + "\n")
    
    # This line BLOCKS - server stays running here
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)
    
    # This code only runs after server stops
    print("\n👋 Server stopped.")

if __name__ == '__main__':
    run_web_server()