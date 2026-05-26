from flask import Blueprint, jsonify, request
from datetime import datetime
from app.extensions import db
from app.models import Student, Teacher, Salary
from sqlalchemy import func, case
from app.models.attendance_model import S_attendance
from app.models.Tattendance import TeacherAttendance
from app.models.live_class import LiveClass
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.payment_model import Payment
from app.models.student_model import Student
from app.models.raise_issue import Issue
from app.models.fees_model import FeeRecord
import os
from app.models.exam_link import ExamLink
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func, case
from datetime import datetime, timedelta



dashboard_bp = Blueprint('admin_main', __name__, url_prefix='/api/admin/dashboard')



# =========================================================
# TOTAL ENROLLED (OPTIMIZED)
# =========================================================

@dashboard_bp.route('/total-enrolled', methods=['GET'])
@jwt_required()
def total_enrolled():

    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"error": "Admin only"}), 403

    current_year = datetime.now().year
    current_month = datetime.now().month

    months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    # ================= TOTAL COUNTS =================

    total_students = db.session.query(
        func.count(Student.id)
    ).scalar() or 0

    total_teachers = db.session.query(
        func.count(Teacher.id)
    ).scalar() or 0

    # ================= CURRENT MONTH =================

    new_students = db.session.query(
        func.count(Student.id)
    ).filter(
        func.extract('month', Student.registration_date) == current_month,
        func.extract('year', Student.registration_date) == current_year
    ).scalar() or 0

    new_teachers = db.session.query(
        func.count(Teacher.id)
    ).filter(
        func.extract('month', Teacher.created_at) == current_month,
        func.extract('year', Teacher.created_at) == current_year
    ).scalar() or 0

    # ================= STUDENT MONTHLY =================

    student_data = db.session.query(
        func.extract('month', Student.registration_date).label('month'),
        func.count(Student.id).label('count')
    ).filter(
        func.extract('year', Student.registration_date) == current_year
    ).group_by(
        func.extract('month', Student.registration_date)
    ).all()

    # ================= TEACHER MONTHLY =================

    teacher_data = db.session.query(
        func.extract('month', Teacher.created_at).label('month'),
        func.count(Teacher.id).label('count')
    ).filter(
        func.extract('year', Teacher.created_at) == current_year
    ).group_by(
        func.extract('month', Teacher.created_at)
    ).all()

    # ================= MAP =================

    student_map = {
        int(row.month): row.count
        for row in student_data
    }

    teacher_map = {
        int(row.month): row.count
        for row in teacher_data
    }

    student_monthly = [
        student_map.get(i, 0)
        for i in range(1, 13)
    ]

    teacher_monthly = [
        teacher_map.get(i, 0)
        for i in range(1, 13)
    ]

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


# =========================================================
# ATTENDANCE OVERVIEW (FULLY OPTIMIZED)
# =========================================================

@dashboard_bp.route('/attendance-overview', methods=['GET'])
@jwt_required()
def attendance_overview():

    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"error": "Admin only"}), 403

    today = datetime.today()

    # Sunday start
    start_of_week = today - timedelta(
        days=today.weekday() + 1 if today.weekday() != 6 else 0
    )

    days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    # =====================================================
    # STUDENT ATTENDANCE
    # =====================================================

    student_rows = db.session.query(
        func.date(S_attendance.date).label("day"),
        func.count(S_attendance.id).label("total"),
        func.sum(
            case(
                (S_attendance.status == 'present', 1),
                else_=0
            )
        ).label("present")
    ).filter(
        S_attendance.date >= start_of_week.date()
    ).group_by(
        func.date(S_attendance.date)
    ).all()

    student_map = {
        str(row.day): {
            "total": row.total,
            "present": int(row.present or 0)
        }
        for row in student_rows
    }

    # =====================================================
    # TEACHER ATTENDANCE
    # =====================================================

    teacher_rows = db.session.query(
        func.date(TeacherAttendance.attendance_date).label("day"),
        func.count(TeacherAttendance.id).label("total"),
        func.sum(
            case(
                (TeacherAttendance.status == 'present', 1),
                else_=0
            )
        ).label("present")
    ).filter(
        TeacherAttendance.attendance_date >= start_of_week.date()
    ).group_by(
        func.date(TeacherAttendance.attendance_date)
    ).all()

    teacher_map = {
        str(row.day): {
            "total": row.total,
            "present": int(row.present or 0)
        }
        for row in teacher_rows
    }

    # =====================================================
    # CALCULATE WEEKLY %
    # =====================================================

    s_weekly = []
    t_weekly = []

    s_total_present = 0
    s_total_records = 0

    t_total_present = 0
    t_total_records = 0

    for i in range(7):

        current_day = (
            start_of_week + timedelta(days=i)
        ).date()

        # ================= STUDENT =================

        s_data = student_map.get(str(current_day), {
            "total": 0,
            "present": 0
        })

        s_total = s_data["total"]
        s_present = s_data["present"]

        s_percent = round(
            (s_present / s_total * 100), 1
        ) if s_total > 0 else 0

        s_weekly.append(s_percent)

        s_total_present += s_present
        s_total_records += s_total

        # ================= TEACHER =================

        t_data = teacher_map.get(str(current_day), {
            "total": 0,
            "present": 0
        })

        t_total = t_data["total"]
        t_present = t_data["present"]

        t_percent = round(
            (t_present / t_total * 100), 1
        ) if t_total > 0 else 0

        t_weekly.append(t_percent)

        t_total_present += t_present
        t_total_records += t_total

    # =====================================================
    # OVERALL %
    # =====================================================

    s_overall_present = round(
        (s_total_present / s_total_records * 100), 1
    ) if s_total_records > 0 else 0

    s_overall_absent = round(
        100 - s_overall_present, 1
    )

    t_overall_present = round(
        (t_total_present / t_total_records * 100), 1
    ) if t_total_records > 0 else 0

    t_overall_absent = round(
        100 - t_overall_present, 1
    )

    return jsonify({
        "days": days,
        "students": {
            "present_percent": s_overall_present,
            "absent_percent": s_overall_absent,
            "weekly": s_weekly
        },
        "teachers": {
            "present_percent": t_overall_present,
            "absent_percent": t_overall_absent,
            "weekly": t_weekly
        }
    })


# ========== Salary Overview ===========

@dashboard_bp.route('/salary-overview', methods=['GET'])
@jwt_required()
def salary_overview():

    claims = get_jwt()

    # 🔐 ADMIN ONLY
    if claims.get("role") != "admin":
        return jsonify({
            "error": "Admin only"
        }), 403

    current_month = datetime.now().month
    current_year = datetime.now().year

    # =====================================================
    # 📊 CURRENT MONTH SALARY RECORDS
    # =====================================================

    salary_records = db.session.query(Salary).filter(
        Salary.month == current_month,
        Salary.year == current_year
    ).all()

    total_salary_records = len(salary_records)

    # =====================================================
    # ✅ PAID COUNT
    # =====================================================

    paid_count = db.session.query(
        func.count(Salary.id)
    ).filter(
        Salary.status == 'paid',
        Salary.month == current_month,
        Salary.year == current_year
    ).scalar() or 0

    # =====================================================
    # ❌ UNPAID COUNT
    # =====================================================

    unpaid_count = db.session.query(
        func.count(Salary.id)
    ).filter(
        Salary.status == 'unpaid',
        Salary.month == current_month,
        Salary.year == current_year
    ).scalar() or 0

    # =====================================================
    # 📈 PERCENTAGES
    # =====================================================

    paid_percent = round(
        (paid_count / total_salary_records) * 100,
        1
    ) if total_salary_records > 0 else 0

    unpaid_percent = round(
        (unpaid_count / total_salary_records) * 100,
        1
    ) if total_salary_records > 0 else 0

    # =====================================================
    # 👨‍🏫 UNPAID TEACHERS
    # =====================================================

    unpaid_records = (
        db.session.query(
            Teacher.id,
            Teacher.fullName,
            Salary.amount
        )
        .join(
            Salary,
            Salary.teacher_id == Teacher.id
        )
        .filter(
            Salary.status == 'unpaid',
            Salary.month == current_month,
            Salary.year == current_year
        )
        .distinct()
        .all()
    )

    unpaid_teachers = []

    for teacher_id, full_name, amount in unpaid_records:

        unpaid_teachers.append({
            "id": teacher_id,
            "name": full_name,
            "amount": amount
        })

    # =====================================================
    # 💰 TOTAL PAID & UNPAID AMOUNT
    # =====================================================

    total_paid_amount = db.session.query(
        func.sum(Salary.amount)
    ).filter(
        Salary.status == 'paid',
        Salary.month == current_month,
        Salary.year == current_year
    ).scalar() or 0

    total_unpaid_amount = db.session.query(
        func.sum(Salary.amount)
    ).filter(
        Salary.status == 'unpaid',
        Salary.month == current_month,
        Salary.year == current_year
    ).scalar() or 0

    # =====================================================
    # 🚀 RESPONSE
    # =====================================================

    return jsonify({
        "success": True,

        "current_month": current_month,
        "current_year": current_year,

        "total_salary_records": total_salary_records,

        "paid_count": paid_count,
        "unpaid_count": unpaid_count,

        "paid_percent": paid_percent,
        "unpaid_percent": unpaid_percent,

        "total_paid_amount": float(total_paid_amount),
        "total_unpaid_amount": float(total_unpaid_amount),

        "unpaid_teachers": unpaid_teachers
    }), 200



# ======= LIVE- CLASSES ====

@dashboard_bp.route('/live-classes', methods=['GET'])
@jwt_required()
def get_all_live_classes():

    claims = get_jwt()

    # 🔐 Admin only
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin only"}), 403

    # 📚 Fetch all live classes
    live_classes = LiveClass.query.order_by(
        LiveClass.start_time.desc()
    ).all()

    result = []

    for live in live_classes:

        # 👨‍🏫 Teacher info
        teacher = Teacher.query.get(live.teacher_id)

        result.append({
            "id": live.id,
            "title": f"{live.subject} - Class {live.class_id}",

            "link": live.meeting_link,
            "message": (
                f"{teacher.fullName if teacher else 'Unknown'} | "
                f"{live.start_time.strftime('%d %b %Y %I:%M %p')}"
            )
        })
    
    return jsonify({
        "success": True,
        "data": result
    }), 200
           


# =========== VIEW ALL EXAM LINK =======

@dashboard_bp.route('/exam-links', methods=['GET'])
@jwt_required()
def get_all_exams():

    claims = get_jwt()

    # 🔐 Only Admin
    if claims.get("role") != "admin":
        return jsonify({
            "error": "Admin only"
        }), 403

    # 📥 Fetch All Exams
    exams = ExamLink.query.order_by(
        ExamLink.exam_time.desc()
    ).all()

    result = []

    for e in exams:

        result.append({

            # unique id
            "id": e.id,

            # title shown on dashboard
            "title": f"{e.subject} - Class {e.class_id}",

            # exam link
            "link": e.exam_link,

            # extra info
            "message": (
                f"Exam Time: "
                f"{e.exam_time.strftime('%d %b %Y %I:%M %p')}"
            )
        })

    return jsonify({
        "success": True,
        "data": result
    }), 200

# ======== VIEW - NOTICE JST FOR CHECK WITH DUMMY ===== =

'''@dashboard_bp.route('/notices', methods=['GET'])
@jwt_required()
def admin_get_notices():

    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin only"}), 403
    
    # 🔥 Dummy Data (Later replace with DB query)
    notices = [
        {
            "id": 1,
            "title": "Holiday Announcement",
            "message": "School will remain closed tomorrow due to heavy rain.",
            "teacher_id": 101,
            "teacher_name": "Rahul Sharma",
            "created_at": datetime(2026, 4, 20, 10, 30).strftime("%Y-%m-%d %H:%M:%S"),
            "priority": "High"
        },
        {
            "id": 2,
            "title": "Exam Notice",
            "message": "Unit test will start from next Monday.",
            "teacher_id": 102,
            "teacher_name": "Anita Verma",
            "created_at": datetime(2026, 4, 19, 14, 15).strftime("%Y-%m-%d %H:%M:%S"),
            "priority": "Medium"
        },
        {
            "id": 3,
            "title": "PTM Meeting",
            "message": "Parent-teacher meeting scheduled on Saturday.",
            "teacher_id": 103,
            "teacher_name": "Suresh Kumar",
            "created_at": datetime(2026, 4, 18, 9, 0).strftime("%Y-%m-%d %H:%M:%S"),
            "priority": "Low"
        }
    ]

    return jsonify({
        "status": "success",
        "total_notices": len(notices),
        "data": notices
    }), 200
'''


# ============= FEE ANALYTICS ================ 

@dashboard_bp.route('/analytics', methods=['GET'])
@jwt_required()
def fee_analytics():

    claims = get_jwt()

    # 🔐 ADMIN ONLY
    if claims.get("role") != "admin":
        return jsonify({
            "error": "Admin only"
        }), 403

    # =====================================================
    # 🎯 FILTERS
    # =====================================================

    status = request.args.get('status', '').lower()
    month = request.args.get('month')

    # =====================================================
    # 📊 MAIN QUERY
    # =====================================================

    query = db.session.query(
        Payment.id,
        Student.FullName.label('student_name'),
        Student.classname.label('class_name'),
        Payment.timestamp,
        Payment.amount,
        Payment.status,
        Payment.month
    ).join(
        Student,
        Student.id == Payment.student_id
    )

    # =====================================================
    # ✅ STATUS FILTER
    # =====================================================

    if status in ['paid', 'unpaid']:
        query = query.filter(
            func.lower(Payment.status) == status
        )

    # =====================================================
    # 📅 MONTH FILTER
    # =====================================================

    if month:
        query = query.filter(
            func.lower(Payment.month) == month.lower()
        )

    # =====================================================
    # 📥 FETCH RECORDS
    # =====================================================

    records = query.order_by(
        Payment.timestamp.desc()
    ).all()

    # =====================================================
    # 📋 TABLE DATA
    # =====================================================

    table_data = []
    total_amount = 0

    for row in records:

        amount = float(row.amount or 0)

        total_amount += amount

        table_data.append({
            "id": row.id,
            "student_name": row.student_name,
            "class": row.class_name,
            "time": row.timestamp.strftime("%I:%M %p") if row.timestamp else "-",
            "amount": amount,
            "status": row.status.capitalize(),
            "month": row.month
        })

    # =====================================================
    # 📈 MONTHLY SUMMARY
    # =====================================================

    summary_query = db.session.query(

        Payment.month,

        func.sum(
            Payment.amount
        ).label('total_amount'),

        func.sum(
            case(
                (Payment.status == 'paid', Payment.amount),
                else_=0
            )
        ).label('paid_amount'),

        func.sum(
            case(
                (Payment.status == 'unpaid', Payment.amount),
                else_=0
            )
        ).label('unpaid_amount'),

        func.count(
            Payment.id
        ).label('total_students'),

        func.sum(
            case(
                (Payment.status == 'paid', 1),
                else_=0
            )
        ).label('paid_count'),

        func.sum(
            case(
                (Payment.status == 'unpaid', 1),
                else_=0
            )
        ).label('unpaid_count')

    ).group_by(
        Payment.month
    )

    summary_records = summary_query.all()

    monthly_summary = []

    for row in summary_records:

        monthly_summary.append({

            "month": row.month,

            "total_amount": float(
                row.total_amount or 0
            ),

            "paid_amount": float(
                row.paid_amount or 0
            ),

            "unpaid_amount": float(
                row.unpaid_amount or 0
            ),

            "total_students": int(
                row.total_students or 0
            ),

            "paid_count": int(
                row.paid_count or 0
            ),

            "unpaid_count": int(
                row.unpaid_count or 0
            )
        })

    # =====================================================
    # 👨‍🎓 MONTH DETAILS
    # =====================================================

    paid_students = []
    unpaid_students = []

    if month:

        # ✅ PAID
        paid_q = db.session.query(
            Student.FullName,
            Student.classname,
            Payment.amount,
            Payment.timestamp
        ).join(
            Student
        ).filter(
            func.lower(Payment.month) == month.lower(),
            Payment.status == 'paid'
        )

        # ❌ UNPAID
        unpaid_q = db.session.query(
            Student.FullName,
            Student.classname,
            Payment.amount
        ).join(
            Student
        ).filter(
            func.lower(Payment.month) == month.lower(),
            Payment.status == 'unpaid'
        )

        # =========================
        # PAID STUDENTS
        # =========================

        for row in paid_q.all():

            paid_students.append({
                "student_name": row.FullName,
                "class": row.classname,
                "amount": float(row.amount or 0),
                "time": row.timestamp.strftime("%I:%M %p") if row.timestamp else "-"
            })

        # =========================
        # UNPAID STUDENTS
        # =========================

        for row in unpaid_q.all():

            unpaid_students.append({
                "student_name": row.FullName,
                "class": row.classname,
                "amount": float(row.amount or 0)
            })

    # =====================================================
    # 🚀 FINAL RESPONSE
    # =====================================================

    return jsonify({

        "success": True,

        # 📋 TABLE
        "table_data": table_data,

        # 💰 TOTAL
        "total_amount": total_amount,

        # 🎯 FILTERS
        "selected_status": status,
        "selected_month": month,

        # 📈 SUMMARY
        "monthly_summary": monthly_summary,

        # 👨‍🎓 DETAILS
        "month_detail": {
            "paid_students": paid_students,
            "unpaid_students": unpaid_students
        }

    }), 200



# ========= APPROVAL API ======= 
@dashboard_bp.route('/approvals', methods=['GET'])
@jwt_required()
def get_uploaded_students():

    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({
            "error": "Admin only"
        }), 403

    # =====================================================
    # FETCH PENDING APPROVALS
    # =====================================================

    records = db.session.query(
        FeeRecord,
        Student
    ).join(
        Student,
        Student.id == FeeRecord.student_id
    ).filter(
        FeeRecord.payment_screenshot != None,
        FeeRecord.approval_status == "Pending"
    ).order_by(
        FeeRecord.created_at.desc()
    ).all()

    data = []

    for fee, student in records:

        data.append({

            "id": fee.id,

            "student_name": student.FullName,

            "month": fee.month,

            "amount": fee.total_amount,

            "status": fee.payment_status,

            "approval_status": fee.approval_status,

            "file_url": fee.payment_screenshot
        })

    return jsonify({        
        "success": True,
        "total": len(data),
        "data": data
    }), 200

# ========= approvals ========
@dashboard_bp.route(
    '/approvals/<int:fee_id>',
    methods=['POST']
)
@jwt_required()
def handle_approval(fee_id):

    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({
            "error": "Admin only"
        }), 403

    data = request.get_json()

    action = data.get("action")

    fee_record = FeeRecord.query.get(fee_id)

    if not fee_record:
        return jsonify({
            "error": "Fee record not found"
        }), 404

    # =====================================================
    # ACCEPT
    # =====================================================

    if action == "accept":

        fee_record.approval_status = "Accepted"

        fee_record.payment_status = "Paid"

        fee_record.payment_date = datetime.utcnow()

    # =====================================================
    # DECLINE
    # =====================================================

    elif action == "decline":

        fee_record.approval_status = "Declined"

        fee_record.payment_status = "Unpaid"

    else:

        return jsonify({
            "error": "Invalid action"
        }), 400

    db.session.commit()

    return jsonify({

        "success": True,

        "message": f"Payment {action}ed successfully",

        "payment_status": fee_record.payment_status,

        "approval_status": fee_record.approval_status

    }), 200


# ====== view student issue ==== 

@dashboard_bp.route('/student-issues', methods=['GET'])
@jwt_required()
def get_all_issues():
    try:
        claims = get_jwt()

        if claims.get("role") != "admin":
            return jsonify({"error": "Only admin allowed"}), 403

        issues = Issue.query.order_by(Issue.created_at.desc()).all()

        data = []
        for issue in issues:
            data.append({
                "id": issue.id,
                "sender_id": issue.sender_id,
                "sender_role": issue.sender_role,
                "receiver_id": issue.receiver_id,
                "receiver_role": issue.receiver_role,
                "subject": issue.subject,
                "message": issue.message,
                "status": issue.status,
                "attachment": issue.attachment,
                "created_at": issue.created_at
            })

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500