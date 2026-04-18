from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models import Teacher, Attendance, Salary, User
from app.extensions import db
from datetime import datetime, date
from app.models.Tattendance import TeacherAttendance
import random
from flask import current_app
import os
from werkzeug.utils import secure_filename
from sqlalchemy import func, case


teacher_checkin_bp = Blueprint('teacher_checkin_bp', __name__, url_prefix='/api/admin')

# === Image file Allower === 

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# 🔹 List all teachers
@teacher_checkin_bp.route('/teachers/list', methods=['GET'])
@jwt_required()
def list_teachers():
    user_id = get_jwt_identity()
    user = User.query.get(user_id) 
    if user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    teachers = Teacher.query.all()
    return jsonify([{
        'id': t.id,
        'name': t.fullName
    } for t in teachers])

# 🔹 Get teacher details + attendance
@teacher_checkin_bp.route('/teacher/<int:teacher_id>', methods=['GET'])
@jwt_required()
def get_teacher_checkin_data(teacher_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    teacher = Teacher.query.get_or_404(teacher_id)

    # Get all attendance records for this teacher
    records = TeacherAttendance.query.filter_by(teacher_id=teacher_id).all()
    total_days = len(records)
    present_days = sum(1 for r in records if r.status == 'Present')
    percent = round((present_days / total_days) * 100, 2) if total_days > 0 else 0


    return jsonify({
        "name": teacher.fullName,          
        "phone_primary": teacher.mobile,    
        "dob": teacher.dob,
        "gender": teacher.gender,
        "idMark": teacher.idMark,             
        "bloodGroup": teacher.bloodGroup,     
        "address": {
            "village": teacher.village,
            "po": teacher.po,
            "ps": teacher.ps,
            "pinCode": teacher.pinCode, 
            "district": teacher.district,
            "state": teacher.state
        },
        'attendance': {
            'percentage': f"{percent}%"
        }
    })


# 🔹 Mark teacher attendance
@teacher_checkin_bp.route('/teacher/<int:teacher_id>/mark-attendance', methods=['POST'])
@jwt_required()
def mark_teacher_attendance(teacher_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    status = data.get('status')  # 'present' or 'absent'

    attendance = Attendance(
        student_id=None,
        date=datetime.utcnow().date(),
        status=status,
        marked_by=teacher_id  # using teacher's user_id
    )
    db.session.add(attendance)
    db.session.commit()

    return jsonify({'message': 'Attendance marked'})


# --------- SALARY LOOK-UP ----------

@teacher_checkin_bp.route('/teacher/salary-lookup', methods=['GET'])
@jwt_required()
def salary_lookup():
    try:
        month = request.args.get('month')
        if not month:
            return jsonify({'error': 'Month parameter is required'}), 400

        month = month.strip().capitalize()
        teachers = Teacher.query.all()
        if not teachers:
            return jsonify({'message': 'No teachers found'}), 404

        
        existing = Salary.query.first()
        if not existing:
            dummy_months = [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ]
            
            for teacher in teachers:
                for m in dummy_months:
                   
                    is_paid = (teacher.id % 2 == 0 and dummy_months.index(m) % 2 == 0) or \
                              (teacher.id % 2 != 0 and dummy_months.index(m) % 2 != 0)

                    status = "Paid" if is_paid else "Due"
                    amount = 25000 if status == "Paid" else 0
                    timestamp = (
                        datetime(2025, dummy_months.index(m) + 1, 5)
                        if status == "Paid" else None
                    )

                    salary = Salary(
                        teacher_id=teacher.id,
                        month=m,
                        amount=amount,
                        status=status,
                        timestamp=timestamp
                    )
                    db.session.add(salary)

            db.session.commit()
            

        # ----- Fetch salary data for selected month ----
        data = []
        for teacher in teachers:
            record = Salary.query.filter_by(teacher_id=teacher.id, month=month).first()

            if record:
                color = "#59BE4C" if record.status.lower() == "paid" else "#808080"
                data.append({
                    "teacher_id": teacher.id,
                    "teacher_name": teacher.fullName,
                    "status": record.status,
                    "amount": record.amount,
                    "month": record.month,
                    "payment_date": record.timestamp.strftime("%Y-%m-%d") if record.timestamp else None,
                    "color": color
                })
            else:
                data.append({
                    "teacher_id": teacher.id,
                    "teacher_name": teacher.fullName,
                    "status": "Due",
                    "amount": 0,
                    "month": month,
                    "payment_date": None,
                    "color": "#808080"
                })

        return jsonify({"month": month, "salary_details": data}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500



# ------------ ATTENDANCE LOOK-UP ------------

@teacher_checkin_bp.route('/teacher/attendance-lookup', methods=['GET'])
@jwt_required()
def attendance_lookup():
    month = request.args.get('month')

    if not month:
        return jsonify({"error": "Month is required"}), 400

    # Get all teachers
    teachers = Teacher.query.all()
    data = []

    # Total working days (agar DB me hi store karte ho to yaha mat rakho)
    total_days = 22  

    attendance_summary = (
        db.session.query(
            TeacherAttendance.teacher_id,
            func.sum(case((TeacherAttendance.status == "Present", 1), else_=0)).label("present_days"),
            func.sum(case((TeacherAttendance.status == "Absent", 1), else_=0)).label("absent_days"),
        )
        .filter(TeacherAttendance.month == month)
        .group_by(TeacherAttendance.teacher_id)
        .all()
    )

    summary_map = {
        row.teacher_id: {
            "present_days": int(row.present_days or 0),
            "absent_days": int(row.absent_days or 0),
        }
        for row in attendance_summary
    }

    for teacher in teachers:
        if teacher.id in summary_map:
            present = summary_map[teacher.id]["present_days"]
            absent = summary_map[teacher.id]["absent_days"]
        else:
            present = 0
            absent = 0

        total = present + absent
        percent = round((present / total) * 100, 2) if total > 0 else 0

        data.append({
            "checkteacher_id": teacher.id,
            "teacher_name": teacher.fullName,
            "month": month,
            "present_days": present,
            "absent_days": absent,
            "percentage": f"{percent}%",
        })

    return jsonify(data), 200

# ------------- PAY - SALARY FOR TEACHER ------- 

@teacher_checkin_bp.route('/teacher/<int:teacher_id>/pay-salary', methods=['POST'])
@jwt_required()
def pay_teacher_salary(teacher_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    month = data.get('month')
    amount = data.get('amount')

    if not month or not amount:
        return jsonify({'error': 'Month and amount required'}), 400

    # ✅ pehle check karo: same teacher + same month
    salary = Salary.query.filter_by(
        teacher_id=teacher_id,
        month=month
    ).first()

    if salary:
        # update existing record
        salary.amount = amount
        salary.status = 'paid'
        salary.payment_date = date.today()
    else:
        # create new record
        salary = Salary(
            teacher_id=teacher_id,
            month=month,
            amount=amount,
            status='paid',
            payment_date=date.today()
        )
        db.session.add(salary)

    db.session.commit()

    return jsonify({'message': 'Salary marked as paid successfully'})


@teacher_checkin_bp.route('/update-details/<int:teacher_id>', methods=['GET', 'PUT'])
@jwt_required()
def admin_teacher_detail(teacher_id):
    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"error": "Admin access only"}), 403

    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({"error": "Teacher not found"}), 404

    # ---------- GET ----------
    if request.method == 'GET':
        return jsonify({
            "fullName": teacher.fullName,
            "mobile": teacher.mobile,
            "dob": teacher.dob,
            "gender": teacher.gender,
            "email": teacher.email,
            "idMark": teacher.idMark,
            "bloodGroup": teacher.bloodGroup,
            "village": teacher.village,
            "po": teacher.po,
            "ps": teacher.ps,
            "pinCode": teacher.pinCode,
            "district": teacher.district,
            "state": teacher.state
        }), 200

    # ---------- PUT ----------
    if request.method == 'PUT':
        data = request.form.to_dict()
        file = request.files.get('teacherImage')

    # ---------- TEXT FIELDS (SAFE UPDATE) ----------
    field_mapping = [
        "fullName", "mobile", "dob", "gender", "email",
        "idMark", "bloodGroup", "village", "po", "ps",
        "pinCode", "district", "state"
    ]

    for field in field_mapping:
        if field in data:
            setattr(teacher, field, data[field])

    # ---------- PHOTO UPDATE ----------
    if file and allowed_file(file.filename):
        upload_folder = os.path.join(current_app.static_folder, 'uploads/teachers')
        os.makedirs(upload_folder, exist_ok=True)

        # delete old photo
        if teacher.photo:
            old_path = os.path.join(upload_folder, teacher.photo)
            if os.path.exists(old_path):
                os.remove(old_path)

        original_filename = secure_filename(file.filename)
        unique_filename = f"{teacher.mobile}_{int(datetime.now().timestamp())}_{original_filename}"
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)

        teacher.photo = unique_filename

    db.session.commit()
    return jsonify({"message": "Teacher details updated successfully"}), 200




@teacher_checkin_bp.route('/delete/teacher/<int:teacher_id>', methods=['DELETE'])
@jwt_required()
def admin_delete_teacher(teacher_id):
    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"error": "Admin access only"}), 403

    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({"error": "Teacher not found"}), 404

    try:
        # ---------- DELETE PHOTO ----------
        if teacher.photo:
            photo_path = os.path.join(
                current_app.root_path,
                'static',
                'uploads',
                'teachers',
                teacher.photo
            )
            if os.path.exists(photo_path):
                os.remove(photo_path)

        # ---------- DELETE RELATED RECORDS ----------
        TeacherAttendance.query.filter_by(teacher_id=teacher_id).delete()
        Attendance.query.filter_by(checkteacher_id=teacher_id).delete()
        Salary.query.filter_by(teacher_id=teacher_id).delete()

        user = User.query.filter_by(teacher_id=teacher_id).first()
        if user:
            db.session.delete(user)

        # ---------- 3. DELETE TEACHER ----------
        db.session.delete(teacher)
        db.session.commit()

        return jsonify({"message": "Teacher and all related data deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print("DELETE TEACHER ERROR:", e)
        return jsonify({
            "error": "Failed to delete teacher",
            "details": str(e)
        }), 500

