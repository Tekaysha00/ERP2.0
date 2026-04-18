from datetime import datetime
from app.extensions import db

class Issue(db.Model):
    __tablename__ = 'issues'

    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    sender_role = db.Column(db.String(20))  

    receiver_id = db.Column(db.Integer, nullable=True)  # null if admin
    receiver_role = db.Column(db.String(20))  # 'teacher' or 'admin'

    message = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(20), default='open')  # open / resolved

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender = db.relationship('Teacher', foreign_keys=[sender_id])