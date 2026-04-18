from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, get_jwt
from datetime import datetime
from app.models.user_model import User
from app.models.teacher_model import Teacher
from ..extensions import jwt, bcrypt
from app.extensions import db
from app.models.Tattendance import Attendance
from app.models.Tattendance import TeacherAttendance


attendance_bp = Blueprint('attendance_bp', __name__, url_prefix='/api/admin')

# -------------- TEACHER ATTENDANCE MARKING ROUTES BY ADMIN --------------

@attendance_bp.route('/mark-attendance', methods=['POST'])
@jwt_required()
def mark_teacher_attendance():
    data = request.get_json()
    print("DEBUG DATA:", data)

    date = data.get('date')
    attendance_list = data.get('attendance', [])

    if not date or not attendance_list:
        return jsonify({'error': 'Date and attendance list are required'}), 400

    attendance_date = datetime.strptime(date, "%Y-%m-%d").date()
    month = attendance_date.strftime("%B")

    already_marked = []
    newly_added = []

    try:
      
        for item in attendance_list:
            teacher_id = item.get('teacher_id')
            status = item.get('status')

            if not teacher_id or not status:
                continue

            existing = TeacherAttendance.query.filter_by(
                teacher_id=teacher_id,
                attendance_date=attendance_date
            ).first()

            if existing:
                already_marked.append({
                    "teacher_id": teacher_id,
                    "status": existing.status
                })
            else:
                new_record = TeacherAttendance(
                    teacher_id=teacher_id,
                    attendance_date=attendance_date,
                    status=status,
                    month=month
                )
                db.session.add(new_record)
                newly_added.append({
                    "teacher_id": teacher_id,
                    "status": status
                })

        db.session.commit()

        if already_marked and newly_added:
            return jsonify({
                "message": "Some attendance marked successfully",
                "already_marked": already_marked,
                "newly_added": newly_added
            }), 207

        elif already_marked and not newly_added:
            return jsonify({
                "error": "All records already marked for this date",
                "already_marked": already_marked
            }), 409

        else:
            return jsonify({
                "message": "Attendance marked successfully",
                "newly_added": newly_added
            }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



# =========== Details view =============

@attendance_bp.route('/teachers', methods=['GET'])
@jwt_required()
def get_all_teachers():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({'error': 'Admin access required'}), 403

    teachers = Teacher.query.all()
    result = [{'id': t.id, 'name': t.fullName, 'mobile': t.mobile} for t in teachers]
    return jsonify({'teachers': result})


@attendance_bp.route('/get-attendance', methods=['GET'])
@jwt_required()
def get_attendance():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({'error': 'Admin access required'}), 403

    month = request.args.get('month')
    date_filter = request.args.get('date')

    query = TeacherAttendance.query
    if month:
        query = query.filter_by(month=month)
    if date_filter:
        query = query.filter_by(attendance_date=date_filter)

    records = query.all()
    data = []
    for record in records:
        teacher = Teacher.query.get(record.teacher_id)
        data.append({
            'id': record.teacher_id,
            'name': teacher.fullName if teacher else 'Unknown',
            'date': record.attendance_date.strftime("%Y-%m-%d"),
            'month': record.month,
            'status': record.status
        })
    return jsonify(data)
