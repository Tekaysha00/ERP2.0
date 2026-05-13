
from flask import Blueprint, jsonify, request
from datetime import datetime
from app.extensions import db
from app.models import Student, Teacher
from app.models.student_model import Student
from app.models.notice_model import Notice
import os
from werkzeug.utils import secure_filename
from app.models.raise_issue import Issue
from flask_jwt_extended import jwt_required, get_jwt



notices_bp = Blueprint('notices', __name__, url_prefix='/api/admin/notices')

# ========== notice- create  ========= 

UPLOAD_FOLDER = "static/uploads/notices"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@notices_bp.route('/create-notice', methods=['POST'])
def create_notice():

    title = request.form.get("title")
    message = request.form.get("message")
    target = request.form.get("target")

    classname = request.form.get("classname")
    teacher_id = request.form.get("teacher_id")

    file = request.files.get("attachment")

    # ================= VALIDATION =================

    if not title:
        return jsonify({"error": "Subject required"}), 400

    if target not in ["student", "teacher"]:
        return jsonify({"error": "Invalid target"}), 400

    # Student Notice
    if target == "student" and not classname:
        return jsonify({"error": "Class required"}), 400

    # Teacher Notice
    if target == "teacher" and not teacher_id:
        return jsonify({"error": "Teacher required"}), 400

    # At least message or file required
    if not message and not file:
        return jsonify({
            "error": "Message or attachment required"
        }), 400

    # ================= FILE UPLOAD =================

    attachment_path = None

    if file:

        if not allowed_file(file.filename):
            return jsonify({
                "error": "Only PNG, JPG, JPEG, PDF allowed"
            }), 400

        filename = secure_filename(file.filename)

        unique_filename = f"{datetime.utcnow().timestamp()}_{filename}"

        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)

        file.save(filepath)

        attachment_path = f"/static/uploads/notices/{unique_filename}"

    # ================= SAVE NOTICE =================

    notice = Notice(
        title=title,
        message=message,
        target=target,
        classname=classname if target == "student" else None,
        teacher_id=teacher_id if target == "teacher" else None,
        attachment=attachment_path
    )

    db.session.add(notice)
    db.session.commit()

    return jsonify({
        "message": "Notice sent successfully",
        "notice_id": notice.id,
        "attachment": attachment_path
    }), 201

@notices_bp.route('/classes', methods=['GET'])
def get_classes():

    classes = db.session.query(Student.classname).distinct().all()

    class_list = [c[0] for c in classes if c[0]]

    return jsonify(class_list)

@notices_bp.route('/teachers', methods=['GET'])
def get_teachers():

    teachers = Teacher.query.all()

    data = []

    for t in teachers:
        data.append({
            "id": t.id,
            "name": t.FullName
        })

    return jsonify(data)




# ===== show issue raise by teacher ======= 
from flask import jsonify, request
import os

# =========================
# GET ALL ISSUES FOR ADMIN
# =========================
@notices_bp.route('/view-teachers/issue', methods=['GET'])
def get_all_issues():
    try:

        issues = Issue.query.order_by(Issue.id.desc()).all()

        issue_list = []

        for issue in issues:

            attachment_url = None

            # attachment download/view url
            if issue.attachment:
                filename = os.path.basename(issue.attachment)

                attachment_url = (
                    f"{request.host_url}uploads/issues/{filename}"
                )

            issue_list.append({
                "id": issue.id,
                "sender_id": issue.sender_id,
                "sender_role": issue.sender_role,
                "receiver_id": issue.receiver_id,
                "receiver_role": issue.receiver_role,
                "message": issue.message,
                "attachment": attachment_url,
                "created_at": issue.created_at if hasattr(issue, 'created_at') else None
            })

        return jsonify({
            "success": True,
            "issues": issue_list
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500



# ====== issue view for student =====

@notices_bp.route('/view-student/issues', methods=['GET'])
@jwt_required()
def get_all_student_issues():
    try:

        claims = get_jwt()

        # only admin allowed
        if claims.get("role") != "admin":
            return jsonify({
                "error": "Only admin allowed"
            }), 403

        # get all student issues
        issues = Issue.query.filter_by(sender_role="student")\
                            .order_by(Issue.id.desc())\
                            .all()

        issue_list = []

        for issue in issues:

            attachment_url = None

            # attachment url
            if issue.attachment:
                filename = os.path.basename(issue.attachment)

                attachment_url = (
                    f"{request.host_url}uploads/issues/{filename}"
                )

            issue_list.append({
                "id": issue.id,
                "sender_id": issue.sender_id,
                "sender_role": issue.sender_role,
                "receiver_id": issue.receiver_id,
                "receiver_role": issue.receiver_role,
                "subject": issue.subject,
                "message": issue.message,
                "attachment": attachment_url,
                "created_at": issue.created_at if hasattr(issue, 'created_at') else None
            })

        return jsonify({
            "success": True,
            "issues": issue_list
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500




# ===== view notices ===

# ================= GET NOTICES =================

@notices_bp.route('/get-notices', methods=['GET'])
def get_notices():

    target = request.args.get("target")       # student / teacher
    classname = request.args.get("classname")
    teacher_id = request.args.get("teacher_id")

    query = Notice.query

    # ================= FILTERS =================

    # Student Notices
    if target == "student":

        query = query.filter_by(target="student")

        if classname:
            query = query.filter_by(classname=classname)

    # Teacher Notices
    elif target == "teacher":

        query = query.filter_by(target="teacher")

        if teacher_id:
            query = query.filter_by(teacher_id=teacher_id)

    # Invalid target
    elif target:
        return jsonify({
            "error": "Invalid target"
        }), 400

    # ================= FETCH DATA =================

    notices = query.order_by(Notice.id.desc()).all()

    data = []

    for notice in notices:

        data.append({
            "id": notice.id,
            "title": notice.title,
            "message": notice.message,
            "target": notice.target,
            "classname": notice.classname,
            "teacher_id": notice.teacher_id,
            "attachment": notice.attachment,
            "created_at": notice.created_at if hasattr(notice, "created_at") else None
        })

    return jsonify(data), 200