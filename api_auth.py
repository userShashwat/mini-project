import secrets
from functools import wraps
from flask import request, jsonify

api_keys = {}

def generate_api_key(user_id):
    """Generate a new API key for user"""
    key = secrets.token_urlsafe(32)
    api_keys[key] = user_id
    return key

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key not in api_keys:
            return jsonify({'error': 'Invalid or missing API key'}), 401
        return f(*args, **kwargs)
    return decorated