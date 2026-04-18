from app.extensions import db
from datetime import datetime

class LiveClass(db.Model):
    __tablename__ = 'live_classes'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    meeting_link = db.Column(db.String(255), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    teacher_id = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)