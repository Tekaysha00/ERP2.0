from flask import jsonify, Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt
from app.models.assignment_model import Assignment
from app.models.homework_model import Homework
from app.models.student_model import Student
from app.extensions import db





assignment_bp = Blueprint('assignment_supervision', __name__, url_prefix='/api/admin')

@assignment_bp.route('/homework-submissions', methods=['GET'])
@jwt_required()
def view_homework_submissions():

    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    classname = request.args.get("classname")

    if not classname:
        return jsonify({"error": "classname is required"}), 400

    students = Student.query.filter(
        db.func.replace(
            db.func.lower(db.func.trim(Student.classname)),
            " ",
            ""
        ) == classname.strip().lower().replace(" ", "")
    ).all()

    result = []

    for student in students:

        homeworks = Homework.query.filter_by(
            student_id=student.id
        ).all()

        student_data = {
            "student_id": student.id,
            "student_name": student.FullName,
            "roll_no": student.rollNo,
            "class": student.classname,
            "section": student.section,
            "homeworks": []
        }

        for hw in homeworks:

            assignment = None

            if hw.assignment_id:
                assignment = Assignment.query.get(hw.assignment_id)

            student_data["homeworks"].append({
                "homework_id": hw.id,
                "uploaded_at": hw.created_at,
                "file_url": hw.file_url,
                "file_type": hw.file_type,

                "assignment": {
                    "id": assignment.id if assignment else None,
                    "title": assignment.title if assignment else None,
                    "subject": assignment.subject if assignment else None,
                    "description": assignment.description if assignment else None
                }
            })

        result.append(student_data)

    return jsonify(result), 200