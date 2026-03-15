"""
Email Alert System for Proctoring AI
Sends email notifications for critical events
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os
from datetime import datetime
import smtplib
import logging

class EmailAlertSystem:
    """
    Send email alerts for suspicious activities
    """
    def __init__(self, config_file='config/email_config.json'):
        self.config = self.load_config(config_file)
        self.logger = logging.getLogger(__name__)
        
    def load_config(self, config_file):
        """Load email configuration"""
        import json
        
        default_config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "your_email@gmail.com",
            "sender_password": "your_app_password",
            "admin_emails": ["admin@example.com"],
            "enable_ssl": True
        }
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        else:
            # Save default config
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    
    def send_alert(self, subject, message, severity=1, screenshot_path=None):
        """
        Send email alert
        
        Args:
            subject: Email subject
            message: Email body
            severity: 1=info, 2=warning, 3=critical
            screenshot_path: Optional path to screenshot
        """
        if severity == 1 and not self.config.get('send_info_emails', True):
            return
        
        msg = MIMEMultipart()
        msg['From'] = self.config['sender_email']
        msg['To'] = ', '.join(self.config['admin_emails'])
        msg['Subject'] = f"[Proctoring AI] {severity_labels[severity]}: {subject}"
        
        # Add severity emoji
        emoji = {1: "ℹ️", 2: "⚠️", 3: "🚨"}.get(severity, "📧")
        
        # Format message
        html_body = f"""
        <html>
        <body>
            <h2>{emoji} Proctoring Alert</h2>
            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Severity:</strong> {'INFO' if severity==1 else 'WARNING' if severity==2 else 'CRITICAL'}</p>
            <p><strong>Message:</strong> {message}</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Attach screenshot if provided
        if screenshot_path and os.path.exists(screenshot_path):
            with open(screenshot_path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-Disposition', 'attachment', 
                             filename=os.path.basename(screenshot_path))
                msg.attach(img)
        
        # Send email
        try:
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            if self.config.get('enable_ssl', True):
                server.starttls()
            
            server.login(self.config['sender_email'], self.config['sender_password'])
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Alert email sent: {subject}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False
    
    def send_session_report(self, session_id, report_path):
        """
        Send session report via email
        """
        subject = f"Session Report: {session_id}"
        message = f"""
        Session {session_id} has completed.
        Report attached.
        """
        
        return self.send_alert(subject, message, severity=1, 
                              screenshot_path=report_path)
    
    def send_critical_alert(self, student_id, alert_type, details):
        """
        Send critical alert for immediate attention
        """
        subject = f"CRITICAL: {alert_type} detected for {student_id}"
        message = f"""
        Student: {student_id}
        Alert Type: {alert_type}
        Details: {details}
        
        Immediate attention required.
        """
        
        return self.send_alert(subject, message, severity=3)

# Severity labels
severity_labels = {1: "INFO", 2: "WARNING", 3: "CRITICAL"}

# Quick test
if __name__ == "__main__":
    email = EmailAlertSystem()
    email.send_alert("Test Alert", "This is a test message", severity=1)