from flask import Blueprint, jsonify
from datetime import datetime
from app.extensions import db
from app.models import Student, Teacher, Salary
from sqlalchemy import func
from app.models.attendance_model import S_attendance
from app.models.Tattendance import TeacherAttendance
from app.models.live_class import LiveClass
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt


dashboard_bp = Blueprint('admin_main', __name__, url_prefix='/api/admin/dashboard')

# ========= TOTAL ENROLLED ===============
@dashboard_bp.route('/total-enrolled', methods=['GET'])
def total_enrolled():
    current_month = datetime.now().month
    current_year  = datetime.now().year

    # ─── Total Enrolled ───────────────────────────────────────────
    total_students = db.session.query(func.count(Student.id)).scalar() or 0
    total_teachers = db.session.query(func.count(Teacher.id)).scalar() or 0

    if total_students == 0 and total_teachers == 0:
        return jsonify({
            "total_students": 120,
            "total_teachers": 15,
            "new_students_this_month": 25,
            "new_teachers_this_month": 3,
            "analytics": {
                "months": ["Jan","Feb","Mar","Apr","May","Jun",
                           "Jul","Aug","Sep","Oct","Nov","Dec"],
                "students": [5, 10, 15, 20, 18, 25, 30, 28, 35, 40, 38, 45],
                "teachers": [1, 2, 1, 3, 2, 4, 3, 5, 4, 6, 5, 7]
            }
        })

    new_students = db.session.query(func.count(Student.id)).filter(
        func.extract('month', Student.registration_date) == current_month,
        func.extract('year',  Student.registration_date) == current_year
    ).scalar() or 0

    new_teachers = db.session.query(func.count(Teacher.id)).filter(
        func.extract('month', Teacher.created_at) == current_month,
        func.extract('year',  Teacher.created_at)  == current_year
    ).scalar() or 0

    # ─── Analytics – month-wise enrollment (current year) ─────────
    months = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]

    student_monthly = []
    teacher_monthly = []

    for m in range(1, 13):
        s_count = db.session.query(func.count(Student.id)).filter(
            func.extract('month', Student.registration_date) == m,
            func.extract('year',  Student.registration_date) == current_year
        ).scalar() or 0

        t_count = db.session.query(func.count(Teacher.id)).filter(
            func.extract('month', Teacher.created_at) == m,
            func.extract('year',  Teacher.created_at)  == current_year
        ).scalar() or 0

        student_monthly.append(s_count)
        teacher_monthly.append(t_count)

    return jsonify({
        "total_students": total_students,
        "total_teachers": total_teachers,
        "new_students_this_month": new_students,
        "new_teachers_this_month": new_teachers,
        "analytics": {
            "months": months,
            "students": student_monthly,
            "teachers": teacher_monthly
        }
    })


# ========== Salary Overview ===========

@dashboard_bp.route('/salary-overview', methods=['GET'])
def salary_overview():
    
    total_salary_records = db.session.query(func.count(Salary.id)).scalar() or 0

    paid_count = db.session.query(func.count(Salary.id)).filter(
        Salary.status == 'paid'
    ).scalar() or 0

    unpaid_count = db.session.query(func.count(Salary.id)).filter(
        Salary.status == 'unpaid'
    ).scalar() or 0

    paid_percent   = round((paid_count   / total_salary_records * 100), 1) if total_salary_records else 0
    unpaid_percent = round((unpaid_count / total_salary_records * 100), 1) if total_salary_records else 0

    # ─── Unpaid Teachers ──────────────────────────────────────────
    unpaid_records = (
        db.session.query(
            Teacher.id,
            Teacher.fullName
        )
        .join(Salary, Salary.teacher_id == Teacher.id)
        .filter(Salary.status == 'unpaid')
        .distinct()
        .all()
    )

    unpaid_teachers = [
        {
            "id": teacher_id,
            "name": full_name
        }
        for teacher_id, full_name in unpaid_records
    ]

    return jsonify({
        "paid_percent": paid_percent,
        "unpaid_percent": unpaid_percent,
        "unpaid_teachers": unpaid_teachers
    })


# =============== ATTENDANCE-OVERVIEW ==========
@dashboard_bp.route('/attendance-overview', methods=['GET'])
def attendance_overview():
    from datetime import datetime, timedelta

    today = datetime.today()

    # Sunday se start
    start_of_week = today - timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0)

    days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    def student_attendance():
        weekly = []
        total_present = 0
        total_records = 0

        for i in range(7):
            day = start_of_week + timedelta(days=i)

            total = db.session.query(func.count(S_attendance.id)).filter(
                func.date(S_attendance.date) == day.date()
            ).scalar() or 0

            present = db.session.query(func.count(S_attendance.id)).filter(
                S_attendance.status == 'present',
                func.date(S_attendance.date) == day.date()
            ).scalar() or 0

            percent = round((present / total * 100), 1) if total else 0
            weekly.append(percent)

            total_present += present
            total_records += total

        overall_present = round((total_present / total_records * 100), 1) if total_records else 0
        return overall_present, 100 - overall_present, weekly


    def teacher_attendance():
        weekly = []
        total_present = 0
        total_records = 0

        for i in range(7):
            day = start_of_week + timedelta(days=i)

            total = db.session.query(func.count(TeacherAttendance.id)).filter(
                func.date(TeacherAttendance.attendance_date) == day.date()
            ).scalar() or 0

            present = db.session.query(func.count(TeacherAttendance.id)).filter(
                TeacherAttendance.status == 'present',
                func.date(TeacherAttendance.attendance_date) == day.date()
            ).scalar() or 0

            percent = round((present / total * 100), 1) if total else 0
            weekly.append(percent)

            total_present += present
            total_records += total

        overall_present = round((total_present / total_records * 100), 1) if total_records else 0
        return overall_present, 100 - overall_present, weekly


    s_present, s_absent, s_weekly = student_attendance()
    t_present, t_absent, t_weekly = teacher_attendance()

    return jsonify({
        "days": days,
        "students": {
            "present_percent": s_present,
            "absent_percent": s_absent,
            "weekly": s_weekly
        },
        "teachers": {
            "present_percent": t_present,
            "absent_percent": t_absent,
            "weekly": t_weekly
        }
    })



# ======= LIVE- CLASSES ====

@dashboard_bp.route('/live-classes', methods=['GET'])
@jwt_required()
def get_live_classes_admin():

    # 🔐 GET DATA FROM JWT
    user_id = get_jwt_identity()   # ye string hoga
    claims = get_jwt()             # yaha role milega

    role = claims.get("role")

    # 🔒 ROLE CHECK
    if role != "admin":
        return jsonify({"error": "Only admin allowed"}), 403

    # 📊 FETCH DATA
    classes = LiveClass.query.order_by(LiveClass.start_time.desc()).all()

    return jsonify([
        {
            "id": c.id,
            "class_id": c.class_id,
            "subject": c.subject,
            "link": c.meeting_link,
            "time": c.start_time.strftime("%Y-%m-%d %H:%M"),
            "teacher_id": c.teacher_id
        }
        for c in classes
    ]), 200