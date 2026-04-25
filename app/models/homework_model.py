from app import db
from datetime import datetime


class Homework(db.Model):
    __tablename__ = 'homeworks'

    id = db.Column(db.Integer, primary_key=True)

    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)

    student_id = db.Column(db.Integer, nullable=False)
    student_name = db.Column(db.String(100), nullable=False)

    file_url = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20))  # audio / video / pdf

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assignment = db.relationship('Assignment', backref='submissions')