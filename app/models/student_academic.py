from app import db
from datetime import datetime

class AcademicRecord(db.Model):
    __tablename__ = 'academic_records'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    exam_name = db.Column(db.String(100))
    score = db.Column(db.Float)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref='academic_records')