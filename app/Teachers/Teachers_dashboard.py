from flask import Blueprint, jsonify, url_for, request
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request, get_jwt
from app.extensions import db
from app.models.teacher_model import Teacher

#live-class
from app.models.live_class import LiveClass
from app.extensions import db
from datetime import datetime
from app.utils.jitsi_meet import generate_meeting_link

#issue
from app.models.raise_issue import Issue
import os
from werkzeug.utils import secure_filename

#exam 
from app.models.exam_link import ExamLink
# notcie
from app.models.notice_model import Notice
#homewrk
from app.models.homework_model import Homework






teacher_dashboard_bp = Blueprint('teacher_dashboard_bp', __name__, url_prefix='/api/teachers/dashboard')

@teacher_dashboard_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_teacher(id):
    teacher_data = Teacher.query.filter_by(id=id).first()

    if not teacher_data:
        return jsonify({'error': 'Teacher not found'}), 404

    # 
    photo_url = (
    url_for('static', filename=f'uploads/teachers/{teacher_data.photo}', _external=True)
    if teacher_data.photo else None
)

    return jsonify({
        "name": teacher_data.fullName,
        "mobile": teacher_data.mobile,
        "photo": photo_url,          
        "personalInfo": {
            "DateOfBirth": teacher_data.dob,
            "Gender": teacher_data.gender,
            "IDMark": teacher_data.idMark,
            "BloodGroup": teacher_data.bloodGroup,
        },
        "address": {
            "Village": teacher_data.village,
            "PO": teacher_data.po,
            "PS": teacher_data.ps,
            "PIN": teacher_data.pinCode,
            "District": teacher_data.district,
            "State": teacher_data.state
        }
    }), 200



# ========================= LIVE CLASS API =========================

@teacher_dashboard_bp.route('/create-live-class', methods=['POST'])
def create_live_class():
    data = request.get_json()

    # 🎯 DEFAULT (dummy teacher for testing)
    teacher_id = 1

    # 🔐 TRY JWT (OPTIONAL — no crash if token missing)
    try:
        verify_jwt_in_request()  # token ho to validate karega
        current_user = get_jwt_identity()

        if current_user and current_user.get("role") == "teacher":
            teacher_id = current_user.get("id")

    except Exception:
        # token nahi hai → dummy use hoga
        pass

    # ⚠️ BASIC VALIDATION
    if not data.get('class_id') or not data.get('subject') or not data.get('start_time'):
        return jsonify({"error": "Missing required fields"}), 400

    # ⏰ TIME PARSE
    try:
        start_time = datetime.fromisoformat(data['start_time'])
    except Exception:
        return jsonify({"error": "Invalid datetime format. Use YYYY-MM-DDTHH:MM:SS"}), 400

    # 🚫 DUPLICATE CHECK
    existing = LiveClass.query.filter_by(
        class_id=data['class_id'],
        start_time=start_time
    ).first()

    if existing:
        return jsonify({"error": "Class already scheduled"}), 400

    # 🔥 AUTO LINK GENERATE (JITSI)
    meet_link = generate_meeting_link(data['class_id'])

    # 💾 SAVE TO DB
    live_class = LiveClass(
        class_id=data['class_id'],
        subject=data['subject'],
        meeting_link=meet_link,
        start_time=start_time,
        teacher_id=teacher_id
    )

    db.session.add(live_class)
    db.session.commit()

    return jsonify({
        "message": "Live class created",
        "meet_link": meet_link,
        "teacher_id": teacher_id
    }), 201


# ========= RAISE AN ISSUE =======

UPLOAD_FOLDER = 'uploads/issues'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

# check file type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@teacher_dashboard_bp.route('/raise-issue', methods=['POST'])
def raise_issue():
    try:
        # form-data (NOT JSON now)
        sender_id = request.form.get('sender_id')
        sender_role = request.form.get('sender_role')
        receiver_id = request.form.get('receiver_id')
        receiver_role = request.form.get('receiver_role')
        message = request.form.get('message')

        file = request.files.get('attachment')

        file_path = None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)

            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)

        issue = Issue(
            sender_id=sender_id,
            sender_role=sender_role,
            receiver_id=receiver_id,
            receiver_role=receiver_role,
            message=message,
            attachment=file_path
        )

        db.session.add(issue)
        db.session.commit()

        return jsonify({"message": "Issue raised successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

# ======= show issue raise by tcher =======
@teacher_dashboard_bp.route('/my-issues/<int:teacher_id>', methods=['GET'])
def get_my_issues(teacher_id):
    issues = Issue.query.filter_by(sender_id=teacher_id).all()

    data = []
    for issue in issues:
        data.append({
            "id": issue.id,
            "message": issue.message,
            "attachment": issue.attachment,
            "status": "sent",
            "created_at": issue.created_at
        })

    return jsonify(data)


# ========== EXAM LINK GENERATOR ======== 

@teacher_dashboard_bp.route('/generate-exam-link', methods=['POST'])
def generate_exam():
    data = request.get_json()

    # 🔐 JWT OPTIONAL
    teacher_id = 1
    try:
        verify_jwt_in_request()
        claims = get_jwt()

        if claims.get("role") == "teacher":
            teacher_id = int(get_jwt_identity())
    except:
        pass

    # 📥 INPUT
    class_id = data.get("class_id")
    subject = data.get("subject")
    exam_time_str = data.get("exam_time")

    if not class_id or not subject or not exam_time_str:
        return jsonify({"error": "Missing fields"}), 400

    try:
        exam_time = datetime.fromisoformat(exam_time_str)
    except:
        return jsonify({"error": "Invalid date format"}), 400

    # 🚫 DUPLICATE CHECK
    existing = ExamLink.query.filter_by(
        class_id=class_id,
        subject=subject,
        exam_time=exam_time
    ).first()

    if existing:
        return jsonify({"error": "Exam already scheduled"}), 400

    # 🔥 GENERATE LINK
    link = generate_meeting_link(data['class_id'], prefix="exam")

    # 💾 SAVE
    exam = ExamLink(
        class_id=class_id,
        subject=subject,
        exam_link=link,
        exam_time=exam_time,
        teacher_id=teacher_id
    )

    db.session.add(exam)
    db.session.commit()

    return jsonify({
        "message": "Exam link generated",
        "link": link
    }), 201


# ========== see exam link ===========
@teacher_dashboard_bp.route('/my-exams', methods=['GET'])
def get_my_exams():

    teacher_id = 1  

    try:
        verify_jwt_in_request()
        claims = get_jwt()

        if claims.get("role") in ["teacher", "staff"]:
            teacher_id = claims.get("teacher_id") or int(get_jwt_identity())
        else:
            return jsonify({"error": "Only teachers allowed"}), 403

    except Exception:
        pass  # no token → testing mode

    exams = ExamLink.query.filter_by(teacher_id=teacher_id)\
        .order_by(ExamLink.exam_time.desc()).all()

    # 🔥 fallback → agar login teacher ka data nahi mila
    if not exams and teacher_id != 1:
        exams = ExamLink.query.filter_by(teacher_id=1)\
            .order_by(ExamLink.exam_time.desc()).all()

    # 🔥 dummy fallback
    if not exams:
        return jsonify([
            {
                "id": 1,
                "class_id": "10",
                "subject": "Math",
                "link": "https://dummy-exam-link.com",
                "time": "2026-01-10 10:00"
            },
            {
                "id": 2,
                "class_id": "9",
                "subject": "Science",
                "link": "https://dummy-exam-link2.com",
                "time": "2026-01-11 11:00"
            }
        ]), 200

    return jsonify([
        {
            "id": e.id,
            "class_id": e.class_id,
            "subject": e.subject,
            "link": e.exam_link,
            "time": e.exam_time.strftime("%Y-%m-%d %H:%M")
        }
        for e in exams
    ]), 200



# =========== live class links ===========
@teacher_dashboard_bp.route('/my-live-classes', methods=['GET'])
def get_my_live_classes():

    teacher_id = 1  # 🧪 default testing

    try:
        verify_jwt_in_request()
        claims = get_jwt()

        if claims.get("role") in ["teacher", "staff"]:
            teacher_id = claims.get("teacher_id") or int(get_jwt_identity())
        else:
            return jsonify({"error": "Only teachers allowed"}), 403

    except Exception:
        pass  # no token → testing

    classes = LiveClass.query.filter_by(teacher_id=teacher_id)\
        .order_by(LiveClass.start_time.desc()).all()

    # 🔥 fallback to default teacher
    if not classes and teacher_id != 1:
        classes = LiveClass.query.filter_by(teacher_id=1)\
            .order_by(LiveClass.start_time.desc()).all()

    # 🔥 dummy data fallback
    if not classes:
        return jsonify([
            {
                "id": 1,
                "class_id": "10",
                "subject": "English",
                "link": "https://dummy-live-class.com",
                "time": "2026-01-09 09:00"
            },
            {
                "id": 2,
                "class_id": "8",
                "subject": "History",
                "link": "https://dummy-live-class2.com",
                "time": "2026-01-08 08:30"
            }
        ]), 200

    return jsonify([
        {
            "id": c.id,
            "class_id": c.class_id,
            "subject": c.subject,
            "link": c.meeting_link,
            "time": c.start_time.strftime("%Y-%m-%d %H:%M")
        }
        for c in classes
    ]), 200


# ======= notice - check for teacherr ===

@teacher_dashboard_bp.route('/notices', methods=['GET'])
@jwt_required()
def get_notices():

    claims = get_jwt()
    role = claims.get("role")

    # 🔥 normalize role
    if role == "staff":
        role = "teacher"

    # 🔥 visibility logic
    def is_visible(target, role):
        if target == "all":
            return True

        if role == "teacher":
            return target in ["admin", "student"]

        if role == "student":
            return target in ["student", "all"]

        return False

    notices = Notice.query.order_by(Notice.created_at.desc()).all()

    # ================= DUMMY DATA =================
    if not notices:
        dummy_data = [
            {
                "id": 1,
                "title": "Welcome to GRT",
                "message": "This is your ERP Software for school",
                "target": "all",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            },
            {
                "id": 2,
                "title": "Holiday Notice",
                "message": "School closed on Sunday.",
                "target": "student",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            },
            {
                "id": 3,
                "title": "Admin Announcement",
                "message": "New rules applied from next week.",
                "target": "admin",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            },
            {
                "id": 4,
                "title": "Teacher Meeting",
                "message": "Meeting at 10 AM.",
                "target": "teacher",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        ]

        filtered_dummy = [
            n for n in dummy_data if is_visible(n["target"], role)
        ]

        return jsonify(filtered_dummy), 200

    # ================= REAL DATA =================
    filtered = []

    for n in notices:
        if is_visible(n.target, role):
            filtered.append({
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "target": n.target,
                "created_at": n.created_at.strftime("%Y-%m-%d %H:%M")
            })

    return jsonify(filtered), 200


# ======== issue view by student =====

@teacher_dashboard_bp.route('/students-issue', methods=['GET'])
@jwt_required()
def get_teacher_issues():
    try:
        teacher_id = get_jwt_identity()
        claims = get_jwt()

        if claims.get("role") != "teacher":
            return jsonify({"error": "Only teacher allowed"}), 403

        issues = Issue.query.filter_by(
            receiver_id=teacher_id,
            receiver_role="teacher"
        ).order_by(Issue.created_at.desc()).all()

        data = []
        for issue in issues:
            data.append({
                "id": issue.id,
                "sender_id": issue.sender_id,
                "sender_role": issue.sender_role,
                "subject": issue.subject,
                "message": issue.message,
                "status": issue.status,
                "attachment": issue.attachment,
                "created_at": issue.created_at
            })

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

# ======= view hw 
@teacher_dashboard_bp.route('/all-homeworks', methods=['GET'])
def get_all_homeworks():

    data = Homework.query.all()

    result = []
    for hw in data:
        result.append({
            "student_name": hw.student_name,
            "file_url": hw.file_url,
            "file_type": hw.file_type,
            "created_at": hw.created_at
        })

    return jsonify(result)