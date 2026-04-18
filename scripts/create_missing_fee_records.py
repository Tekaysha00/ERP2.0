import os
import sys

# ✅ Make sure Python can find the 'app' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.student_model import Student
from app.students.payment_routes import ensure_fee_records_for_student

app = create_app()

with app.app_context():
    students = Student.query.all()
    for s in students:
        ensure_fee_records_for_student(s.id)
