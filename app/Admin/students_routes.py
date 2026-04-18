from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.models.student_model import Student

student_bp_admin = Blueprint('student_bp_admin', __name__, url_prefix='/api')

@student_bp_admin.route('/students', methods=['GET'])
@jwt_required()
def get_all_students():
    students = Student.query.all()
    return jsonify([{
        'id': s.id,
        'name': s.FullName,
        'class': s.classname,
        'phone': s.phone,
        'email': s.email
    } for s in students])