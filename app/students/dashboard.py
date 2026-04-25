from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.student_model import Student
from flask import url_for
from app.utils.helpers import format_classname
from app.models.notice_model import Notice
from datetime import datetime
from app.models.exam_link import ExamLink
from app.models.raise_issue import Issue
from app.models.live_class import LiveClass
from app.extensions import db

import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads/issues'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)



student_dashboard_bp = Blueprint('student_dashboard_bp', __name__, url_prefix='/api/student/dashboard')

@student_dashboard_bp.route('<int:id>', methods=['GET'])
@jwt_required()
def get_student(id):
    student = Student.query.get_or_404(id)

    current_raw_class = getattr(student, "classname", None)
    # Base photo URL  
    photo_url = None
    if student.photo:
        photo_url = url_for('static', filename=f'uploads/students/{student.photo}', _external=True)

    return jsonify({
        "id": student.id,
        "name": student.FullName,
        "phone": student.phone,
        "rollNo": student.rollNo,
        "classname": current_raw_class,
        "classname": format_classname(current_raw_class),
        "photo": photo_url,  
        "personalInfo": {
            "email": student.email,
            "DateOfBirth": student.dob,
            "AdmissionNo": student.admissionNo,
            "Gender": student.gender,
            "IDMark": student.idMark,
            "BloodGroup": student.bloodGroup,
        },
        "address": {
            "Village": student.village,
            "PO": student.po,
            "PS": student.ps,
            "PIN": student.pinCode,
            "District": student.district,
            "State": student.state,
        },
    })


# ======== view notice =======

@student_dashboard_bp.route('/notices', methods=['GET'])
@jwt_required()
def get_notices():

    claims = get_jwt()
    role = claims.get("role")   # student / teacher

    notices = Notice.query.order_by(Notice.created_at.desc()).all()

    # ========== dummy data ===============
    if not notices:
        dummy_data = [
            {
                "id": 1,
                "title": "Welcome to ERP",
                "message": "This is your first notice. Stay updated with announcements.",
                "target": "all",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            },
            {
                "id": 2,
                "title": "Holiday Notice",
                "message": "School will remain closed on Sunday.",
                "target": "student",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            },
            {
                "id": 3,
                "title": "Staff Meeting",
                "message": "All teachers must attend meeting at 10 AM.",
                "target": "teacher",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        ]

        # filter based on role
        filtered_dummy = [
            n for n in dummy_data
            if n["target"] == "all" or n["target"] == role
        ]

        return jsonify(filtered_dummy)

    filtered = []

    for n in notices:
        if n.target == "all" or n.target == role:
            filtered.append({
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "target": n.target,
                "created_at": n.created_at.strftime("%Y-%m-%d %H:%M")
            })

    return jsonify(filtered)


# ============ view live class ======= 
@student_dashboard_bp.route('/live-classes-view', methods=['GET'])
@jwt_required()
def get_live_classes():

    user_id = get_jwt_identity()

    # 🔥 student fetch karo
    student = Student.query.filter_by(user_id=user_id).first()

    if not student:
        return jsonify({"error": "Student not found"}), 404

    class_id = int(student.classname.split()[-1])

    classes = LiveClass.query.filter_by(class_id=class_id).all()

    # 🔥 dummy fallback
    if not classes:
        return jsonify([
            {
                "id": 1,
                "class_id": class_id,
                "subject": "Math",
                "link": "https://dummy-live-class.com",
                "time": "2026-01-10 10:00"
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




# ============ exam link ========= 

@student_dashboard_bp.route('/exam-links', methods=['GET'])
@jwt_required()
def get_exam_links():

    user_id = get_jwt_identity()

    # 🔥 student fetch
    student = Student.query.filter_by(user_id=user_id).first()

    if not student:
        return jsonify({"error": "Student not found"}), 404

    class_id = int(student.classname.split()[-1])

    exams = ExamLink.query.filter_by(class_id=class_id).all()

    # 🔥 dummy fallback
    if not exams:
        return jsonify([
            {
                "id": 1,
                "class_id": class_id,
                "subject": "Science",
                "link": "https://dummy-exam-link.com",
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


# ====== issue raise ====== 
@student_dashboard_bp.route('/raise-issue', methods=['POST'])
@jwt_required()
def raise_issue():
    try:
        student_id = get_jwt_identity()
        claims = get_jwt()

        if claims.get("role") != "student":
            return jsonify({"error": "Only students allowed"}), 403

        receiver_type = request.form.get('receiver_role')  # admin / teacher
        receiver_id = request.form.get('receiver_id')  # optional (for teacher)

        subject = request.form.get('subject')
        message = request.form.get('message')

        file = request.files.get('attachment')
        file_path = None

        # ======================
        # FILE UPLOAD
        # ======================
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)

        # ======================
        # CREATE ISSUE
        # ======================
        issue = Issue(
            sender_id=student_id,
            sender_role="student",
            receiver_id=receiver_id if receiver_type == "teacher" else None,
            receiver_role=receiver_type,
            subject=subject,
            message=message,
            attachment=file_path
        )

        db.session.add(issue)
        db.session.commit()

        return jsonify({
            "message": "Issue raised successfully"
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500