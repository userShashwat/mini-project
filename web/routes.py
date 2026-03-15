"""
API routes for Proctoring AI web interface
"""
from flask import Blueprint, jsonify
from datetime import datetime

# Create blueprint
api_bp = Blueprint('api', __name__)

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    })

def register_routes(app):
    """Register all routes with the app"""
    app.register_blueprint(api_bp, url_prefix='/api')