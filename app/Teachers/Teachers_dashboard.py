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
@jwt_required()
def create_live_class():

    claims = get_jwt()

    # 🔐 ONLY TEACHER
    if claims.get("role") not in ["teacher", "staff"]:
        return jsonify({
            "error": "Only teachers can create live classes"
        }), 403

    teacher_id = get_jwt_identity()

    data = request.get_json()

    # ✅ VALIDATION
    required_fields = ['class_id', 'subject', 'start_time']

    for field in required_fields:
        if not data.get(field):
            return jsonify({
                "error": f"{field} is required"
            }), 400

    # ⏰ DATETIME PARSE
    try:
        start_time = datetime.fromisoformat(
            data['start_time']
        )

    except Exception:
        return jsonify({
            "error": "Invalid datetime format. Use YYYY-MM-DDTHH:MM:SS"
        }), 400

    # 🚫 DUPLICATE CHECK
    existing = LiveClass.query.filter_by(
        class_id=data['class_id'],
        start_time=start_time
    ).first()

    if existing:
        return jsonify({
            "error": "Class already scheduled"
        }), 400

    # 🔗 AUTO MEETING LINK
    meet_link = generate_meeting_link(
        data['class_id']
    )

    # 💾 SAVE
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
        "success": True,
        "message": "Live class created successfully",
        "data": {
            "id": live_class.id,
            "class_id": live_class.class_id,
            "subject": live_class.subject,
            "meeting_link": live_class.meeting_link,
            "start_time": live_class.start_time.isoformat(),
            "teacher_id": live_class.teacher_id
        }
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
@jwt_required()
def generate_exam():

    claims = get_jwt()

    if claims.get("role") not in ["teacher", "staff"]:
        return jsonify({
            "error": "Only teachers allowed"
        }), 403

    teacher_id = int(get_jwt_identity())

    data = request.get_json()

    class_id = data.get("class_id")
    subject = data.get("subject")
    exam_time_str = data.get("exam_time")

    if not class_id or not subject or not exam_time_str:
        return jsonify({
            "error": "Missing fields"
        }), 400

    try:
        exam_time = datetime.fromisoformat(exam_time_str)

    except Exception:
        return jsonify({
            "error": "Invalid date format"
        }), 400

    existing = ExamLink.query.filter_by(
        class_id=class_id,
        subject=subject,
        exam_time=exam_time
    ).first()

    if existing:
        return jsonify({
            "error": "Exam already scheduled"
        }), 400

    link = generate_meeting_link(
        class_id,
        prefix="exam"
    )

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
        "success": True,
        "message": "Exam link generated successfully",
        "data": {
            "id": exam.id,
            "class_id": exam.class_id,
            "subject": exam.subject,
            "link": exam.exam_link,
            "time": exam.exam_time.strftime("%Y-%m-%d %H:%M")
        }
    }), 201


# ========== see exam link ===========

@teacher_dashboard_bp.route('/my-exams', methods=['GET'])
@jwt_required()
def get_my_exams():

    claims = get_jwt()

    if claims.get("role") not in ["teacher", "staff"]:
        return jsonify({
            "error": "Only teachers allowed"
        }), 403

    teacher_id = int(get_jwt_identity())

    exams = ExamLink.query.filter_by(
        teacher_id=teacher_id
    ).order_by(
        ExamLink.exam_time.desc()
    ).all()

    result = []

    for e in exams:
        result.append({
            "id": e.id,
            "class_id": e.class_id,
            "subject": e.subject,
            "link": e.exam_link,
            "time": e.exam_time.strftime("%Y-%m-%d %H:%M")
        })

    return jsonify(result), 200



# =========== live class links ===========
@teacher_dashboard_bp.route('/my-live-classes', methods=['GET'])
@jwt_required()
def get_my_live_classes():

    claims = get_jwt()

    if claims.get("role") not in ["teacher", "staff"]:
        return jsonify({
            "error": "Only teachers allowed"
        }), 403

    # CHANGE THIS
    teacher_id = get_jwt_identity()

    classes = LiveClass.query.filter_by(
        teacher_id=teacher_id
    ).order_by(
        LiveClass.start_time.desc()
    ).all()

    result = []

    for c in classes:
        result.append({
            "id": c.id,
            "class_id": c.class_id,
            "subject": c.subject,
            "link": c.meeting_link,
            "time": c.start_time.strftime("%Y-%m-%d %H:%M")
        })

    return jsonify({
        "success": True,
        "data": result
    }), 200


# ======= notice - check for teacherr ===

@teacher_dashboard_bp.route('/notices', methods=['GET'])
@jwt_required()
def get_notices():

    claims = get_jwt()
    role = claims.get("role")

    # normalize role
    if role == "staff":
        role = "teacher"

    if role != "teacher":
        return jsonify({
            "error": "Only teachers allowed"
        }), 403

    user_id = get_jwt_identity()

    # logged in teacher
    teacher = Teacher.query.filter_by(user_id=user_id).first()

    if not teacher:
        return jsonify({
            "error": "Teacher not found"
        }), 404

    # ===== FETCH NOTICES =====

    notices = Notice.query.filter(
        (Notice.target == "all") |
        (
            (Notice.target == "teacher") &
            (Notice.teacher_id == teacher.id)
        )
    ).order_by(Notice.created_at.desc()).all()

    # ===== DUMMY DATA =====

    if not notices:

        return jsonify([
            {
                "id": 1,
                "title": "No Notices",
                "message": "No notices available right now.",
                "attachment": None,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        ])

    # ===== RESPONSE =====

    filtered = []

    for n in notices:

        filtered.append({
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "target": n.target,
            "attachment": n.attachment,
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



