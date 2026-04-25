from flask import Blueprint, jsonify, url_for
from app.models.student_model import Student
from flask_jwt_extended import jwt_required
from app.utils.helpers import format_classname




student_details_bp = Blueprint('student_details_bp', __name__, url_prefix='/api/student')

@student_details_bp.route('<int:id>', methods=['GET'])
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