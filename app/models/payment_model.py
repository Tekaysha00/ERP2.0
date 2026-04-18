from app.extensions import db
from datetime import datetime

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='unpaid')  
    mode = db.Column(db.String(20), default='none')   
    month = db.Column(db.String(20))  
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    student = db.relationship('Student', backref='payments')

    def __repr__(self):
        return f"<Payment id={self.id} student_id={self.student_id} amount={self.amount} status={self.status}>"