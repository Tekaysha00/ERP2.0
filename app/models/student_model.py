from ..extensions import db
from datetime import datetime

# ========================= Student Dashboard =========================
class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    FullName = db.Column(db.String(100))
    phone = db.Column(db.String(15), unique=True)
    dob = db.Column(db.String(10))
    gender = db.Column(db.String(10))
    idMark = db.Column(db.String(50))
    bloodGroup = db.Column(db.String(10))
    admissionNo = db.Column(db.String(50), unique=True)
    fatherName = db.Column(db.String(100))
    occupation = db.Column(db.String(100))
    village = db.Column(db.String(100))
    po = db.Column(db.String(100))
    ps = db.Column(db.String(100))
    email = db.Column(db.String(100))
    pinCode = db.Column(db.String(50))
    district = db.Column(db.String(100))
    state = db.Column(db.String(100))
    rollNo = db.Column(db.String(50))
    section = db.Column(db.String(5), nullable=True)
    fees = db.relationship('Fee', backref='student', lazy=True)
    attendance = db.relationship('StudentAttendance', backref='student', lazy=True)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    classname = db.Column(db.String(50))
    photo = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

 
# ========================= STUDENT ATTENDANCE =========================

class StudentAttendance(db.Model):
    __tablename__ = 'student_attendance'
    id = db.Column(db.Integer, primary_key=True)
    attendance_date = db.Column(db.Date)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    section = db.Column(db.String(5)) 
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    month = db.Column(db.String(20))
    status = db.Column(db.String(10))