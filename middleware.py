from flask import request, jsonify
import time
from collections import defaultdict
import re

class SecurityMiddleware:
    def __init__(self):
        self.request_counts = defaultdict(list)
        self.blocked_ips = set()
        
    def check_rate_limit(self, ip, limit=100, window=60):
        """Rate limiting - 100 requests per minute per IP"""
        now = time.time()
        self.request_counts[ip] = [t for t in self.request_counts[ip] 
                                   if now - t < window]
        
        if len(self.request_counts[ip]) >= limit:
            self.blocked_ips.add(ip)
            return False
        
        self.request_counts[ip].append(now)
        return True
    
    def validate_input(self, data):
        """Prevent XSS and SQL injection"""
        if isinstance(data, str):
            # Remove potentially dangerous characters
            data = re.sub(r'[<>"\']', '', data)
        return data
    
    def check_sql_injection(self, query):
        """Detect SQL injection attempts"""
        dangerous = ['--', ';', 'DROP', 'DELETE', 'UPDATE', 'INSERT', 
                    'SELECT * FROM', 'UNION', 'OR 1=1']
        for pattern in dangerous:
            if pattern.lower() in query.lower():
                return True
        return False

security = SecurityMiddleware()

@app.before_request
def before_request():
    """Middleware before each request"""
    ip = request.remote_addr
    
    # Check if IP is blocked
    if ip in security.blocked_ips:
        return jsonify({'error': 'IP blocked due to excessive requests'}), 429
    
    # Rate limiting
    if not security.check_rate_limit(ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    # Validate input data
    if request.json:
        for key, value in request.json.items():
            if isinstance(value, str):
                request.json[key] = security.validate_input(value)
    
    # Check for SQL injection in query strings
    for key, value in request.args.items():
        if security.check_sql_injection(value):
            return jsonify({'error': 'Invalid query parameters'}), 400