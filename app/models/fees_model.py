from app.extensions import db
from datetime import datetime

class FeeRecord(db.Model):
    __tablename__ = 'fee_records'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    month = db.Column(db.String(20))
    school_fee = db.Column(db.Integer)
    sports_fee = db.Column(db.Integer)
    other_fee = db.Column(db.Integer)
    total_amount = db.Column(db.Integer)
    upi_id = db.Column(db.String(100))
    razorpay_order_id = db.Column(db.String(100))
    payment_status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref='fee_records')