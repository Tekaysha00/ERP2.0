from ..extensions import db
from app.models.attendance_model import S_attendance

class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True)
    mobile = db.Column(db.String(15), unique=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    teacher_id = db.Column(db.Integer)
    dob = db.Column(db.String(20), nullable=True)
    class_name = db.Column(db.String(20))

  # Date of Birth for teachers/students login

    attendance_marked = db.relationship(
        'S_attendance',
        back_populates='user',
        lazy=True,
      #  foreign_keys=[S_attendance.user_id]
    )