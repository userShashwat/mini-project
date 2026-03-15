"""
WebSocket events for real-time communication
"""
from flask_socketio import SocketIO, emit, join_room, leave_room
import time
import json
from datetime import datetime

# Initialize socketio (will be configured in app.py)
socketio = None

def init_socketio(sio):
    """Initialize socketio with app"""
    global socketio
    socketio = sio
    register_handlers()

def register_handlers():
    """Register all WebSocket event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        print(f"🟢 Client connected: {request.sid}")
        emit('connected', {'message': 'Connected to proctoring server'})

    @socketio.on('disconnect')
    def handle_disconnect():
        print(f"🔴 Client disconnected: {request.sid}")

    @socketio.on('join_exam')
    def handle_join_exam(data):
        """Student joins exam room"""
        exam_id = data['exam_id']
        student_id = data['student_id']
        room = f"exam_{exam_id}"
        
        join_room(room)
        emit('joined_exam', {
            'exam_id': exam_id,
            'student_id': student_id,
            'timestamp': datetime.now().isoformat()
        })
        
        # Notify proctors
        emit('student_joined', {
            'student_id': student_id,
            'exam_id': exam_id
        }, room='proctors')

    @socketio.on('join_proctor')
    def handle_join_proctor():
        """Proctor joins monitoring room"""
        join_room('proctors')
        emit('joined_proctor', {'message': 'Now monitoring all exams'})

    @socketio.on('alert')
    def handle_alert(data):
        """Handle new alert"""
        alert = {
            'id': data.get('id'),
            'type': data.get('type'),
            'severity': data.get('severity', 1),
            'message': data.get('message'),
            'student_id': data.get('student_id'),
            'exam_id': data.get('exam_id'),
            'timestamp': datetime.now().isoformat(),
            'score': data.get('score', 0)
        }
        
        # Broadcast to proctors
        emit('new_alert', alert, room='proctors')
        
        # Log to database
        from utils.database import ProctorDatabase
        db = ProctorDatabase()
        db.add_alert(data.get('session_id'), alert)

    @socketio.on('suspicious_score')
    def handle_suspicious_score(data):
        """Handle suspicious score update"""
        emit('score_update', {
            'student_id': data['student_id'],
            'score': data['score'],
            'timestamp': datetime.now().isoformat()
        }, room='proctors')

    @socketio.on('proctor_action')
    def handle_proctor_action(data):
        """Handle proctor intervention"""
        action = data['action']
        target = data['target']
        message = data.get('message', '')
        
        if action == 'warn':
            emit('proctor_warning', {
                'message': message,
                'severity': 'warning'
            }, room=f"student_{target}")
        elif action == 'terminate':
            emit('exam_terminated', {
                'reason': message
            }, room=f"student_{target}")
        
        # Log action
        emit('action_logged', {
            'proctor': data['proctor_id'],
            'action': action,
            'target': target,
            'timestamp': datetime.now().isoformat()
        }, room='proctors')

    @socketio.on('heartbeat')
    def handle_heartbeat(data):
        """Handle client heartbeat"""
        emit('heartbeat_ack', {
            'timestamp': datetime.now().isoformat()
        })

    @socketio.on('leave_exam')
    def handle_leave_exam(data):
        """Student leaves exam"""
        exam_id = data['exam_id']
        student_id = data['student_id']
        room = f"exam_{exam_id}"
        
        leave_room(room)
        emit('left_exam', {
            'student_id': student_id,
            'exam_id': exam_id
        })
        
        # Notify proctors
        emit('student_left', {
            'student_id': student_id,
            'exam_id': exam_id
        }, room='proctors')