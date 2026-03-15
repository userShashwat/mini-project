"""
PDF Report Generator for Proctoring Sessions
"""
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
import base64
from PIL import Image as PILImage
import cv2

class ReportGenerator:
    """
    Generate PDF reports for proctoring sessions
    """
    def __init__(self, output_dir='data/reports'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.styles = getSampleStyleSheet()
        self.create_custom_styles()
        
    def create_custom_styles(self):
        """Create custom styles for the report"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=30,
            textColor=colors.HexColor('#1a1a2e')
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            alignment=TA_LEFT,
            spaceAfter=12,
            textColor=colors.HexColor('#16213e')
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT,
            spaceAfter=6,
            textColor=colors.HexColor('#333333')
        ))
    
    def generate_session_report(self, session_id, session_data, output_filename=None):
        """
        Generate comprehensive session report
        
        Args:
            session_id: Session identifier
            session_data: Dictionary with session metrics
            output_filename: Optional output filename
        """
        if output_filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"report_{session_id}_{timestamp}.pdf"
        
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Build story
        story = []
        
        # Title
        title = f"Proctoring Session Report: {session_id}"
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Spacer(1, 0.25 * inch))
        
        # Session info
        info_data = [
            ['Student Name:', session_data.get('student_name', 'Unknown')],
            ['Exam Name:', session_data.get('exam_name', 'Unknown')],
            ['Date:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Duration:', session_data.get('duration', 'N/A')],
            ['Status:', session_data.get('status', 'Completed')]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#16213e')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#333333')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(Paragraph("Session Information", self.styles['CustomHeading']))
        story.append(info_table)
        story.append(Spacer(1, 0.25 * inch))
        
        # Summary statistics
        story.append(Paragraph("Summary Statistics", self.styles['CustomHeading']))
        
        stats = session_data.get('statistics', {})
        stats_data = [
            ['Total Alerts:', str(stats.get('total_alerts', 0))],
            ['Critical Alerts:', str(stats.get('critical_alerts', 0))],
            ['Warnings:', str(stats.get('warnings', 0))],
            ['Max Suspicious Score:', f"{stats.get('max_score', 0):.2f}"],
            ['Average Score:', f"{stats.get('avg_score', 0):.2f}"],
            ['Face Detections:', str(stats.get('face_detections', 0))],
            ['Suspicious Objects:', str(stats.get('suspicious_objects', 0))],
            ['Audio Events:', str(stats.get('audio_events', 0))]
        ]
        
        stats_table = Table(stats_data, colWidths=[2*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(stats_table)
        story.append(Spacer(1, 0.25 * inch))
        
        # Score timeline chart
        if 'score_timeline' in session_data:
            story.append(Paragraph("Suspicious Score Timeline", self.styles['CustomHeading']))
            chart_img = self.create_score_chart(session_data['score_timeline'])
            if chart_img:
                story.append(chart_img)
                story.append(Spacer(1, 0.25 * inch))
        
        # Alerts table
        alerts = session_data.get('alerts', [])
        if alerts:
            story.append(Paragraph("Alert Log", self.styles['CustomHeading']))
            
            alert_data = [['Time', 'Type', 'Severity', 'Message']]
            for alert in alerts[:20]:  # Show last 20 alerts
                alert_data.append([
                    alert.get('time', ''),
                    alert.get('type', ''),
                    str(alert.get('severity', '')),
                    alert.get('message', '')
                ])
            
            alert_table = Table(alert_data, colWidths=[1.2*inch, 1.2*inch, 0.8*inch, 3*inch])
            alert_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            story.append(alert_table)
        
        # Build PDF
        doc.build(story)
        
        return output_path
    
    def create_score_chart(self, timeline_data):
        """
        Create a matplotlib chart of scores over time
        """
        try:
            plt.figure(figsize=(8, 3))
            
            times = [d['time'] for d in timeline_data]
            scores = [d['score'] for d in timeline_data]
            
            plt.plot(times, scores, 'b-', linewidth=2)
            plt.axhline(y=0.7, color='r', linestyle='--', alpha=0.5, label='Critical Threshold')
            plt.axhline(y=0.4, color='orange', linestyle='--', alpha=0.5, label='Warning Threshold')
            
            plt.xlabel('Time')
            plt.ylabel('Suspicious Score')
            plt.title('Suspicious Score Over Time')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Save to bytes buffer
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
            plt.close()
            
            img_buffer.seek(0)
            
            # Convert to ReportLab Image
            img = Image(img_buffer, width=6*inch, height=2.5*inch)
            return img
            
        except Exception as e:
            print(f"Error creating chart: {e}")
            return None
    
    def generate_student_report(self, student_id, sessions_data):
        """
        Generate report for a student across multiple sessions
        """
        output_path = os.path.join(self.output_dir, f"student_{student_id}_report.pdf")
        
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        
        # Title
        story.append(Paragraph(f"Student Report: {student_id}", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.25 * inch))
        
        # Summary
        total_sessions = len(sessions_data)
        total_alerts = sum(s.get('total_alerts', 0) for s in sessions_data)
        avg_score = np.mean([s.get('avg_score', 0) for s in sessions_data]) if sessions_data else 0
        
        summary_data = [
            ['Total Sessions:', str(total_sessions)],
            ['Total Alerts:', str(total_alerts)],
            ['Average Score:', f"{avg_score:.2f}"],
            ['Report Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        story.append(Paragraph("Summary", self.styles['CustomHeading']))
        story.append(summary_table)
        story.append(Spacer(1, 0.25 * inch))
        
        # Sessions table
        story.append(Paragraph("Session History", self.styles['CustomHeading']))
        
        session_data = [['Date', 'Duration', 'Alerts', 'Max Score']]
        for session in sessions_data[-10:]:  # Last 10 sessions
            session_data.append([
                session.get('date', ''),
                session.get('duration', ''),
                str(session.get('total_alerts', 0)),
                f"{session.get('max_score', 0):.2f}"
            ])
        
        session_table = Table(session_data, colWidths=[2*inch, 1.5*inch, 1*inch, 1.5*inch])
        session_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ]))
        
        story.append(session_table)
        
        doc.build(story)
        return output_path
    
    def generate_proctor_report(self, proctor_id, date_range):
        """
        Generate report for proctor activity
        """
        output_path = os.path.join(self.output_dir, f"proctor_{proctor_id}_report.pdf")
        
        doc = SimpleDocTemplate(output_path, pagesize=landscape(letter))
        story = []
        
        story.append(Paragraph(f"Proctor Activity Report: {proctor_id}", self.styles['CustomTitle']))
        
        # Add content...
        
        doc.build(story)
        return output_path

# Quick test
if __name__ == "__main__":
    report_gen = ReportGenerator()
    
    # Test data
    test_data = {
        'student_name': 'John Doe',
        'exam_name': 'Final Exam 2026',
        'duration': '45 minutes',
        'status': 'Completed',
        'statistics': {
            'total_alerts': 12,
            'critical_alerts': 3,
            'warnings': 9,
            'max_score': 0.89,
            'avg_score': 0.45,
            'face_detections': 1250,
            'suspicious_objects': 2,
            'audio_events': 8
        },
        'score_timeline': [
            {'time': '10:00', 'score': 0.2},
            {'time': '10:05', 'score': 0.3},
            {'time': '10:10', 'score': 0.8},
            {'time': '10:15', 'score': 0.4},
        ],
        'alerts': [
            {'time': '10:12', 'type': 'object', 'severity': 3, 'message': 'Cell phone detected'},
            {'time': '10:08', 'type': 'face', 'severity': 2, 'message': 'Multiple faces'},
        ]
    }
    
    report_path = report_gen.generate_session_report('test123', test_data)
    print(f"Report generated: {report_path}")