from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.student_model import StudentAttendance
from app.models.student_model import Student
from flask import url_for
from ..extensions import db
from datetime import datetime
from sqlalchemy import extract
from app.utils.helpers import format_classname
from flask import session
from app.models.live_class import LiveClass


students_bp = Blueprint('students_bp', __name__, url_prefix='/api/students')


@students_bp.route('/attendance-status/<int:student_id>', methods=['GET'])
@jwt_required()
def view_attendance(student_id):
    user_id = get_jwt_identity()
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404
    if student.id != student_id:
        return jsonify({"error": "Unauthorized access"}), 403

    month = request.args.get('month')
    if not month:
        return jsonify({"error": "Month is required"}), 400

    # ✅ Case-insensitive month filtering
    records = StudentAttendance.query.filter(
        StudentAttendance.student_id == student_id,
        db.func.lower(StudentAttendance.month) == month.lower()
    ).all()

    # ✅ No records for that month
    if not records:
        return jsonify({
            "month": month,
            "percentage": "0%",
            "records": [],
            "name": student.FullName,
            "photo": url_for('static', filename=f'uploads/students/{student.photo}', _external=True) if student.photo else None,
            "class": format_classname(student.classname),
            "rollNo": student.rollNo,
            "phone": student.phone
        }), 200

    # ✅ Calculate percentage from real data
    total_days = len(records)
    present_days = sum(1 for r in records if r.status.lower() == 'present')
    percent = round((present_days / total_days) * 100, 2)

    data = {
        "month": month,
        "percentage": f"{percent}%",
        "records": [
            {"date": r.attendance_date.strftime("%Y-%m-%d"), "status": r.status}
            for r in records
        ],
        "name": student.FullName,
        "photo": url_for('static', filename=f'uploads/students/{student.photo}', _external=True) if student.photo else None,
        "class": format_classname(student.classname) ,
        "rollNo": student.rollNo,
        "phone": student.phone
    }

    print("✅ DEBUG attendance data:", data)
    return jsonify(data)


# ========== GET LIVE CLASS API ========= 

@students_bp.route('/live-classes')
def get_live_classes():
    student_class_id = session['class_id']

    classes = LiveClass.query.filter_by(
        class_id=student_class_id
    ).all()

    return jsonify([
        {
            "subject": c.subject,
            "link": c.meeting_link,
            "time": c.start_time
        } for c in classes
    ])
