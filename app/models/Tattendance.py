from app.extensions import db
from datetime import datetime

class Attendance(db.Model):
    __tablename__ = 'T_attendance'
    id = db.Column(db.Integer, primary_key=True)

    checkteacher_id = db.Column(db.Integer, db.ForeignKey('checkteachers.id'), nullable=False)  
    month = db.Column(db.String(20), nullable=False)
    present_days = db.Column(db.Integer, default=0)
    absent_days = db.Column(db.Integer, default=0)

    checkteacher = db.relationship('Checkteacher', backref='attendances')



class TeacherAttendance(db.Model):
    __tablename__ = 'teacher_attendance'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    month = db.Column(db.String(20), nullable=False)

    teacher = db.relationship('Teacher', backref='attendances')
