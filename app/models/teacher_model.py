from ..extensions import db
from app.extensions import db
from datetime import datetime


class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    fullName = db.Column(db.String(100))  
    mobile = db.Column(db.String(15), unique=True)
    dob = db.Column(db.String(10))
    email = db.Column(db.String(120))
    gender = db.Column(db.String(10))
    idMark = db.Column(db.String(50))  
    bloodGroup = db.Column(db.String(10)) 
    village = db.Column(db.String(100))
    po = db.Column(db.String(100))
    ps = db.Column(db.String(100))
    pinCode = db.Column(db.String(50)) 
    district = db.Column(db.String(100))
    state = db.Column(db.String(100))
    photo = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Checkteacher(db.Model):
    __tablename__ = 'checkteachers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    salaries = db.relationship('Salary', backref='checkteacher', lazy=True)


