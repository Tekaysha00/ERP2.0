from ..extensions import db
from datetime import datetime

class S_attendance(db.Model):
    __tablename__ = 'S_attendance'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    status = db.Column(db.String(10), nullable=False)
    marked_by = db.Column(db.String)
    #classname = db.Column(db.String(50))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    user = db.relationship('User', back_populates='attendance_marked')

    def __repr__(self):
        return f'<S_attendance {self.id} - User {self.user_id} - {self.status}>'
    

