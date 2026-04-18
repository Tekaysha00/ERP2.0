from models.student_model import Student
from werkzeug.security import generate_password_hash
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db  # Assuming db is initialized in extensions.py
from app.Admin.main_routes import admin_bp
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from app.models.teacher_model import Teacher


admin_bp = Blueprint('admin_bp', __name__, name='admin_bp_unique') 



@admin_bp.route('/register_student', methods=['POST'])
@jwt_required()
def register_student():
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.get_json()
    student = Student(
        FullName=data['FullName'],
        phone=data['phone'],
        dob=data['dob'],
        gender=data['gender'],
        admissionNo=data['admissionNo'],
        fatherName=data['fatherName'],
        user_id=data['user_id'],
        password=generate_password_hash(data['dob'])  # DOB as default password
    )
    db.session.add(student)
    db.session.commit()
    return jsonify({"msg": "Student registered successfully"})


#Teacher's registration

@admin_bp.route('/admin/register_teacher', methods=['POST'])
@jwt_required()
def register_teacher():
    if get_jwt_identity()["role"] != "admin":
        return jsonify({'msg': 'Unauthorized'}), 403

    data = request.get_json()
    hashed_pw = generate_password_hash(data['dob'])

    teacher = Teacher(
        full_name=data['full_name'],
        dob=data['dob'],
        phone=data['phone'],
        gender=data.get('gender', ''),
        id_mark=data.get('id_mark', ''),
        blood_group=data.get('blood_group', ''),
        village=data.get('village', ''),
        post_office=data.get('post_office', ''),
        police_station=data.get('police_station', ''),
        pin_code=data.get('pin_code', ''),
        district=data.get('district', ''),
        state=data.get('state', ''),
        password=hashed_pw
    )

    db.session.add(teacher)
    db.session.commit()
    return jsonify({'msg': 'Teacher registered successfully'})


# ------ for testing ------- 
from flask import render_template

@admin_bp.route('/dashboard')
@jwt_required()
def admin_dashboard():
    identity = get_jwt_identity()
    if identity['role'] != 'admin':
        return jsonify({'msg': 'Unauthorized'}), 403

    return render_template('admin_dashboard.html')  
