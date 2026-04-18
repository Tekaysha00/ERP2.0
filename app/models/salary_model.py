from app.extensions import db
from datetime import datetime

class Salary(db.Model):
    __tablename__ = 'salaries'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    month = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='unpaid')
    payment_date = db.Column(db.Date, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    checkteacher_id = db.Column(db.Integer, db.ForeignKey('checkteachers.id'))
    teacher = db.relationship('Teacher', backref='salaries')

