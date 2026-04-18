from app import db
from datetime import datetime

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    filename = db.Column(db.String(200))
    classname = db.Column(db.String(20), nullable=False)
    section = db.Column(db.String(10))
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    teacher = db.relationship('User', backref='assignments')
    


class ExamResult(db.Model):
    __tablename__ = 'exam_results'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    exam_name = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer)

    # ---------- Result file ----------
    result_file_name = db.Column(db.String(200))        
    result_file_mimetype = db.Column(db.String(100))   
    result_file_data = db.Column(db.LargeBinary)        

    # ---------- Admit card file (agar chahiye) ----------
    admit_card_name = db.Column(db.String(200))
    admit_card_mimetype = db.Column(db.String(100))
    admit_card_data = db.Column(db.LargeBinary)

    remarks = db.Column(db.Text)

    student = db.relationship('Student', backref='exam_results')
