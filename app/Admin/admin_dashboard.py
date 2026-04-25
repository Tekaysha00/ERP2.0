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
from app.models.notice_model import Notice
from app.models.raise_issue import Issue



dashboard_bp = Blueprint('admin_main', __name__, url_prefix='/api/admin/dashboard')

# ========= TOTAL ENROLLED ===============
@dashboard_bp.route('/total-enrolled', methods=['GET'])
@jwt_required()
def total_enrolled():

    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin only"}), 403

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
@jwt_required()
def salary_overview():

    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin only"}), 403

    current_month = datetime.now().month
    current_year  = datetime.now().year

    # ─────────────────────────────────────────────
    # 🧪 DUMMY DATA (ONLY IF DB EMPTY)
    # ─────────────────────────────────────────────

    existing = db.session.query(Salary.id).first()

    if not existing:
        # 👨‍🏫 Teachers
        teachers = [
            Teacher(fullName="Abijit CID"),
            Teacher(fullName="ACP Praddyuman"),
            Teacher(fullName="Daya Bhosle"),
            Teacher(fullName="Sunil Tope"),
            Teacher(fullName="Dilip Laude"),
            Teacher(fullName="Satish Muthmare")
        ]

        db.session.add_all(teachers)
        db.session.commit()

        salaries = [
            Salary(teacher_id=teachers[0].id, amount=10000, status='paid', month=current_month, year=current_year),
            Salary(teacher_id=teachers[1].id, amount=0, status='unpaid', month=current_month, year=current_year),
            Salary(teacher_id=teachers[2].id, amount=0, status='unpaid', month=current_month, year=current_year),
            Salary(teacher_id=teachers[3].id, amount=12000, status='paid', month=current_month, year=current_year),
            Salary(teacher_id=teachers[4].id, amount=0, status='unpaid', month=current_month, year=current_year),
            Salary(teacher_id=teachers[5].id, amount=0, status='unpaid', month=current_month, year=current_year),
        ]

        db.session.add_all(salaries)
        db.session.commit()

    
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
@jwt_required()
def attendance_overview():

    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin only"}), 403
    
    from datetime import datetime, timedelta
    import random

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

            # 🔥 Dummy fallback
            if total == 0:
                total = 10
                present = random.randint(5, 10)

            percent = round((present / total * 100), 1)
            weekly.append(percent)

            total_present += present
            total_records += total

        overall_present = round((total_present / total_records * 100), 1)
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

            # 🔥 Dummy fallback
            if total == 0:
                total = 5
                present = random.randint(2, 5)

            percent = round((present / total * 100), 1)
            weekly.append(percent)

            total_present += present
            total_records += total

        overall_present = round((total_present / total_records * 100), 1)
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



# ======== VIEW - NOTICE JST FOR CHECK WITH DUMMY ===== =

@dashboard_bp.route('/notices', methods=['GET'])
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



# ============= FEE ANALYTICS ================ 

@dashboard_bp.route('/analytics', methods=['GET'])
@jwt_required()
def fee_analytics():

    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin only"}), 403

# ======= DUMMY DAATA ======
    if Payment.query.count() == 0:

        # Students create
        s1 = Student(FullName="Modi-ur-Rehman", classname="Bidaya")
        s2 = Student(FullName="Oggy Adityanath", classname="Uoola")
        s3 = Student(FullName="Sharjeel Imam", classname="Uliya")
        s4 = Student(FullName="Umar Khalid", classname="Bidaya")

        db.session.add_all([s1, s2, s3, s4])
        db.session.commit()

        # April (All Paid)
        payments = [
            Payment(student_id=s1.id, amount=15000, status="paid", month="April", timestamp=datetime.now()),
            Payment(student_id=s2.id, amount=11000, status="paid", month="April", timestamp=datetime.now()),
            Payment(student_id=s3.id, amount=13000, status="paid", month="April", timestamp=datetime.now()),
            Payment(student_id=s4.id, amount=15000, status="paid", month="April", timestamp=datetime.now()),

            # May (Mixed)
            Payment(student_id=s1.id, amount=15000, status="unpaid", month="May"),
            Payment(student_id=s2.id, amount=11000, status="unpaid", month="May"),
            Payment(student_id=s3.id, amount=13000, status="paid", month="May", timestamp=datetime.now()),
            Payment(student_id=s4.id, amount=15000, status="unpaid", month="May"),
        ]

        db.session.add_all(payments)
        db.session.commit()

        print("Dummy data inserted")

    # =========================
    # FILTERS
    # =========================
    status = request.args.get('status', 'paid').lower()
    month = request.args.get('month')
    

    # =========================
    # 1. TABLE DATA
    # =========================
    query = db.session.query(
        Payment.id,
        Student.FullName.label('student_name'),
        Student.classname.label('class_name'),
        Payment.timestamp,
        Payment.amount,
        Payment.status,
        Payment.month
    ).join(Student, Student.id == Payment.student_id)

    if status in ['paid', 'unpaid']:
        query = query.filter(Payment.status == status)

    if month:
        query = query.filter(func.lower(Payment.month) == month.lower())


    records = query.order_by(Payment.id.desc()).all()

    table_data = []
    total_amount = 0

    for row in records:
        total_amount += float(row.amount or 0)

        table_data.append({
            "student_name": row.student_name,
            "class": row.class_name,
            "time": row.timestamp.strftime("%I:%M %p") if row.timestamp else "-",
            "amount": row.amount,
            "status": row.status.capitalize(),
            "month": row.month
        })

   
    # ======= MONTHLY SUMMARY

    summary_query = db.session.query(
        Payment.month,
        func.sum(Payment.amount).label('total_amount'),
        func.sum(case((Payment.status == 'paid', Payment.amount), else_=0)).label('paid_amount'),
        func.sum(case((Payment.status == 'unpaid', Payment.amount), else_=0)).label('unpaid_amount'),
        func.count(Payment.id).label('total_students'),
        func.sum(case((Payment.status == 'paid', 1), else_=0)).label('paid_count'),
        func.sum(case((Payment.status == 'unpaid', 1), else_=0)).label('unpaid_count')
    ).group_by(Payment.month)

    summary_records = summary_query.all()

    monthly_summary = []
    for row in summary_records:
        monthly_summary.append({
            "month": row.month,
            "total_amount": float(row.total_amount or 0),
            "paid_amount": float(row.paid_amount or 0),
            "unpaid_amount": float(row.unpaid_amount or 0),
            "total_students": int(row.total_students or 0),
            "paid_count": int(row.paid_count or 0),
            "unpaid_count": int(row.unpaid_count or 0)
        })

    
    # ======== MONTH DETAILS
    paid_students = []
    unpaid_students = []

    if month:
        paid_q = db.session.query(
            Student.FullName,
            Student.classname,
            Payment.amount,
            Payment.timestamp
        ).join(Student).filter(
            func.lower(Payment.month) == month.lower(),
            Payment.status == 'paid'
        )

        unpaid_q = db.session.query(
            Student.FullName,
            Student.classname,
            Payment.amount
        ).join(Student).filter(
            func.lower(Payment.month) == month.lower(),
            Payment.status == 'unpaid'
        )

        for row in paid_q.all():
            paid_students.append({
                "student_name": row.FullName,
                "class": row.classname,
                "amount": row.amount,
                "time": row.timestamp.strftime("%I:%M %p") if row.timestamp else "-"
            })

        for row in unpaid_q.all():
            unpaid_students.append({
                "student_name": row.FullName,
                "class": row.classname,
                "amount": row.amount
            })

    return jsonify({
        "success": True,

        # table
        "table_data": table_data,
        "total_amount": total_amount,

        # filters
        "selected_status": status,
        "selected_month": month,

        # summary
        "monthly_summary": monthly_summary,

        # details
        "month_detail": {
            "paid_students": paid_students,
            "unpaid_students": unpaid_students
        }
    }), 200



# ========= APPROVAL API ======= 
uploaded_students = [
    {"id": 1, "student_name": "Alvina Firdos"},
    {"id": 2, "student_name": "Shagufta Sakahawat"},
    {"id": 3, "student_name": "Oniba Naaz"},
    {"id": 4, "student_name": "Sayma Naaz"},
    {"id": 5, "student_name": "Maryam G"},
]


@dashboard_bp.route('/approvals', methods=['GET'])
@jwt_required()
def get_uploaded_students():

    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin only"}), 403
    
    return jsonify({
        "success": True,
        "message": "Students who uploaded payment screenshot",
        "data": uploaded_students
    })

# ========== notice- create  ========= 

@dashboard_bp.route('/create-notice', methods=['POST'])
def create_notice():
    data = request.get_json()

    title = data.get('title')
    message = data.get('message')
    target = data.get('target', 'all')  # default = all

    if not title or not message:
        return jsonify({"error": "Title and message required"}), 400

    notice = Notice(
        title=title,
        message=message,
        target=target
    )

    db.session.add(notice)
    db.session.commit()

    return jsonify({"msg": "Notice created successfully"})



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