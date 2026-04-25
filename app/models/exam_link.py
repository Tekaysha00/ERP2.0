from app.extensions import db
from datetime import datetime

class ExamLink(db.Model):
    __tablename__ = 'exam_links'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    exam_link = db.Column(db.String(255), nullable=False)
    exam_time = db.Column(db.DateTime, nullable=False)
    teacher_id = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)