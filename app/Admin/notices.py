
from flask import Blueprint, jsonify, request
from datetime import datetime
from app.extensions import db
from app.models import Student, Teacher
from app.models.student_model import Student
from app.models.notice_model import Notice
import os
from werkzeug.utils import secure_filename




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