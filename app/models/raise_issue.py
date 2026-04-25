from datetime import datetime
from app.extensions import db

class Issue(db.Model):
    __tablename__ = 'issues'

    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(db.Integer, nullable=False)
    sender_role = db.Column(db.String(20))   # 'student' / 'teacher'

    receiver_id = db.Column(db.Integer, nullable=True)
    receiver_role = db.Column(db.String(20))  # 'teacher' / 'admin'

    subject = db.Column(db.String(255))   # ✅ ADD THIS
    message = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(20), default='open')
    attachment = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)