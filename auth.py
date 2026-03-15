"""
Authentication module for Proctoring AI
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from functools import wraps
import sqlite3
import os
from datetime import datetime, timedelta
import jwt
from itsdangerous import URLSafeTimedSerializer

# Initialize extensions
bcrypt = Bcrypt()
login_manager = LoginManager()
serializer = URLSafeTimedSerializer('your-secret-key-here')  # Change in production

# Database setup
def get_db():
    """Get database connection"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'users.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_auth_db():
    """Initialize authentication database"""
    conn = get_db()
    
    # Create users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Create login attempts table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            username TEXT,
            success BOOLEAN,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create sessions table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            token TEXT,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create default users if they don't exist
    users = [
        ('admin', 'admin@proctoring.com', 'admin123', 'admin'),
        ('proctor1', 'proctor@proctoring.com', 'proctor123', 'proctor'),
        ('student1', 'student@proctoring.com', 'student123', 'student')
    ]
    
    for username, email, password, role in users:
        existing = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if not existing:
            hashed = bcrypt.generate_password_hash(password).decode('utf-8')
            conn.execute('''
                INSERT INTO users (username, email, password, role)
                VALUES (?, ?, ?, ?)
            ''', (username, email, hashed, role))
    
    conn.commit()
    conn.close()
    print("✅ Authentication database initialized")

# User model
class User(UserMixin):
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
    
    @staticmethod
    def get(user_id):
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        if user:
            return User(user['id'], user['username'], user['email'], user['role'])
        return None
    
    @staticmethod
    def get_by_username(username):
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user:
            return User(user['id'], user['username'], user['email'], user['role'])
        return None
    
    @staticmethod
    def get_by_email(email):
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        if user:
            return User(user['id'], user['username'], user['email'], user['role'])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Role-based access control
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please login first.', 'warning')
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('auth.unauthorized'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', 
                                    validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('student', 'Student'), ('proctor', 'Proctor')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.get_by_username(username.data)
        if user:
            raise ValidationError('Username already taken. Please choose another.')
    
    def validate_email(self, email):
        user = User.get_by_email(email.data)
        if user:
            raise ValidationError('Email already registered. Please use another.')

# Create auth blueprint (no url_prefix so routes are at /login, /register etc.)
# Change this line in auth.py (around line 100)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        ip = request.remote_addr
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user and bcrypt.check_password_hash(user['password'], password):
            # Log successful attempt
            conn.execute('''
                INSERT INTO login_attempts (ip_address, username, success)
                VALUES (?, ?, 1)
            ''', (ip, username))
            
            # Update last login
            conn.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            ''', (user['id'],))
            conn.commit()
            
            user_obj = User(user['id'], user['username'], user['email'], user['role'])
            login_user(user_obj, remember=True)
            
            # Generate session token
            token = jwt.encode({
                'user_id': user['id'],
                'exp': datetime.utcnow() + timedelta(hours=24)
            }, 'your-secret-key', algorithm='HS256')
            
            session['token'] = token
            
            # Redirect based on role - FIXED: admin_dashboard -> admin_panel
            if user['role'] == 'admin':
                return redirect(url_for('admin_panel'))
            elif user['role'] == 'proctor':
                return redirect(url_for('proctor_dashboard'))
            else:
                return redirect(url_for('exam_page'))
        else:
            # Log failed attempt
            conn.execute('''
                INSERT INTO login_attempts (ip_address, username, success)
                VALUES (?, ?, 0)
            ''', (ip, username))
            conn.commit()
            flash('Invalid username or password', 'danger')
        
        conn.close()
    
    return render_template('login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        
        conn = get_db()
        conn.execute('''
            INSERT INTO users (username, email, password, role)
            VALUES (?, ?, ?, ?)
        ''', (form.username.data, form.email.data, hashed, form.role.data))
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/unauthorized')
def unauthorized():
    """Unauthorized access page"""
    return render_template('unauthorized.html'), 401

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html', user=current_user)

# Security middleware
def security_headers(app):
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        return response
    return app

# Rate limiting
class RateLimiter:
    def __init__(self):
        self.attempts = {}
    
    def is_allowed(self, ip, max_attempts=5, window=300):
        now = datetime.now()
        if ip in self.attempts:
            # Clean old attempts
            self.attempts[ip] = [t for t in self.attempts[ip] 
                                 if now - t < timedelta(seconds=window)]
            
            if len(self.attempts[ip]) >= max_attempts:
                return False
            
            self.attempts[ip].append(now)
        else:
            self.attempts[ip] = [now]
        
        return True

rate_limiter = RateLimiter()

# Initialize database when module is imported
init_auth_db()