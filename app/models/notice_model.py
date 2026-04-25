# app/models/notice_model.py

from app import db
from datetime import datetime

class Notice(db.Model):
    __tablename__ = "notices"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)

    target = db.Column(db.String(20), default="all")  
    # options: 'all', 'student', 'teacher'

    created_at = db.Column(db.DateTime, default=datetime.utcnow)