from flask import Blueprint, jsonify
from datetime import datetime
from app.extensions import db
from app.models import Student, Teacher, Salary
from sqlalchemy import func

dashboard_bp = Blueprint('admin_main', __name__, url_prefix='/api/admin')

@dashboard_bp.route('/dashboard', methods=['GET'])
def dashboard():
    current_month = datetime.now().month
    current_year  = datetime.now().year

    # ─── Total Enrolled ───────────────────────────────────────────
    total_students = db.session.query(func.count(Student.id)).scalar() or 0
    total_teachers = db.session.query(func.count(Teacher.id)).scalar() or 0

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

    analytics = {
        "months": months,
        "students": student_monthly,
        "teachers": teacher_monthly
    }

    # ─── Salary Overview ──────────────────────────────────────────
    total_salary_records = db.session.query(func.count(Salary.id)).scalar() or 0

    paid_count = db.session.query(func.count(Salary.id)).filter(
        Salary.status == 'paid'
    ).scalar() or 0

    unpaid_count = db.session.query(func.count(Salary.id)).filter(
        Salary.status == 'unpaid'
    ).scalar() or 0

    paid_percent   = round((paid_count   / total_salary_records * 100), 1) if total_salary_records else 0
    unpaid_percent = round((unpaid_count / total_salary_records * 100), 1) if total_salary_records else 0

    # Jinke koi bhi salary record unpaid hai — unka naam + id + month list
    unpaid_records = (
        db.session.query(
            Teacher.id,
            Teacher.fullName,
            Salary.month,
            Salary.amount
        )
        .join(Salary, Salary.teacher_id == Teacher.id)
        .filter(Salary.status == 'unpaid')
        .order_by(Teacher.id)
        .all()
    )

    # Teacher ke hisaab se group karo
    unpaid_teachers_dict = {}
    for teacher_id, full_name, month, amount in unpaid_records:
        if teacher_id not in unpaid_teachers_dict:
            unpaid_teachers_dict[teacher_id] = {
                "id":     teacher_id,
                "name":   full_name,
                "unpaid_months": []
            }
        unpaid_teachers_dict[teacher_id]["unpaid_months"].append({
            "month":  month,
            "amount": amount
        })

    unpaid_teachers = list(unpaid_teachers_dict.values())

    salary_overview = {
        "paid_percent":    paid_percent,
        "unpaid_percent":  unpaid_percent,
        "unpaid_teachers": unpaid_teachers   # list of teachers with unpaid months
    }

    # ─── Final Response ───────────────────────────────────────────
    return jsonify({
        "total_enrolled": {
            "total_students":          total_students,
            "total_teachers":          total_teachers,
            "new_students_this_month": new_students,
            "new_teachers_this_month": new_teachers
        },
        "analytics":       analytics,
        "salary_overview": salary_overview
    })