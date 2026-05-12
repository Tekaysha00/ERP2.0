# app/models/notice_model.py

from app import db
from datetime import datetime

class Notice(db.Model):
    __tablename__ = "notices"

    id = db.Column(db.Integer, primary_key=True)

    # Subject
    title = db.Column(db.String(200), nullable=False)

    # Issue / Description
    message = db.Column(db.Text, nullable=True)

    # student / teacher
    target = db.Column(db.String(20), nullable=False)

    # Student notice ke liye
    classname = db.Column(db.String(50), nullable=True)

    # Teacher notice ke liye
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=True)

    # attachment
    attachment = db.Column(db.String(300), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)