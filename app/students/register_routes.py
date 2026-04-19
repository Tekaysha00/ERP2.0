from flask import Blueprint, request, jsonify, current_app, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request
from app.extensions import db, bcrypt
from app.models.user_model import User
from app.models.student_model import Student
from datetime import datetime
import os
from werkzeug.utils import secure_filename

# ----------------- CONFIG -----------------
student_register_bp = Blueprint('student_register_bp', __name__, url_prefix='/api/students')

UPLOAD_SUBDIR = 'uploads/students'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Check if uploaded file has a valid image extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ========================= REGISTER STUDENT =========================
@student_register_bp.route('/register-student', methods=['POST'])
def register_student():
    print("DEBUG Authorization header:", request.headers.get('Authorization'))

    # --- JWT Validation ---
    try:
        verify_jwt_in_request()
    except Exception as e:
        print("JWT verification error:", e)
        return jsonify({'error': f'Token verification failed: {str(e)}'}), 401

    claims = get_jwt()
    if claims.get('role') not in ['admin', 'teacher']:
        return jsonify({'error': 'Admin or teacher access required'}), 403

    admin_id = get_jwt_identity()

    # --- Parse Form Data ---
    data = request.form.to_dict() or {}
    file = request.files.get('image')
    print("DEBUG form data:", data)

    # --- Handle Class Info ---
    raw_class = (
        data.get("class Id") or
        data.get("classId") or
        data.get("class_id") or
        data.get("classname") or
        data.get("class")
    )

    if raw_class:
        value = str(raw_class).strip().lower().replace(" ", "")

        num = ''.join(filter(str.isdigit, value))

        if num:
            resolved_classname = f"Class {num}"
        else:
            resolved_classname = raw_class
    else:
        return jsonify({"error": "Class selection required"}), 400


    # --- Required Fields ---
    required = ['mobile', 'dob', 'fullName', 'admissionNo']
    missing = [k for k in required if not data.get(k)]
    if missing:
        return jsonify({'error': 'Missing required fields', 'fields': missing}), 400

    if not resolved_classname:
        return jsonify({'error': 'Class selection required (classname or classId)'}), 400

    # --- Uniqueness Checks ---
    try:
        if User.query.filter_by(phone=data['mobile']).first():
            return jsonify({'error': 'Phone already registered'}), 409
        if Student.query.filter_by(admissionNo=data['admissionNo']).first():
            return jsonify({'error': 'Admission number already registered'}), 409
    except Exception as e:
        return jsonify({'error': 'Database lookup failed', 'details': str(e)}), 500

    # --- Create User Account (Password = DOB in DDMMYYYY) ---
    try:
        raw_dob = data['dob']

        dob_date = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%a %b %d %Y %H:%M:%S GMT%z"):
            try:
                dob_date = datetime.strptime(raw_dob, fmt)
                break
            except ValueError:
                continue

        if not dob_date:
            return jsonify({'error': 'Invalid DOB format'}), 400

        dob_for_db = dob_date.strftime("%Y-%m-%d")
        dob_for_password = dob_date.strftime("%d%m%Y")
        hashed_pw = bcrypt.generate_password_hash(dob_for_password).decode('utf-8')

        user = User(
            username=data['mobile'],
            phone=data['mobile'],
            password=hashed_pw,
            role='student',
            dob=dob_for_db
        )
        db.session.add(user)
        db.session.flush()

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'User creation failed', 'details': str(e)}), 500

    # --- Handle Profile Photo Upload ---
    photo_filename = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)

        # ✅ compute folder dynamically here
        upload_folder = os.path.join(current_app.static_folder, UPLOAD_SUBDIR)
        os.makedirs(upload_folder, exist_ok=True)

        unique_filename = f"{data.get('admissionNo')}_{int(datetime.now().timestamp())}_{filename}"
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        photo_filename = unique_filename
    else:
        print("⚠️ No valid photo uploaded or invalid file type")

    # --- Create Student Record ---
    try:
        student = Student(
            FullName=data.get('fullName'),
            phone=data.get('mobile'),
            dob=data.get('dob'),
            gender=data.get('gender'),
            idMark=data.get('idMark'),
            rollNo=data.get('rollNo'),
            section=data.get('section'),
            bloodGroup=data.get('bloodGroup'),
            admissionNo=data.get('admissionNo'),
            fatherName=data.get('fatherName'),
            occupation=data.get('occupation'),
            village=data.get('village'),
            po=data.get('po'),
            ps=data.get('ps'),
            email=data.get('email'),
            pinCode=data.get('pinCode'),
            district=data.get('district'),
            state=data.get('state'),
            classname=resolved_classname,
            user_id=user.id,
            photo=photo_filename
        )

        db.session.add(student)
        db.session.flush()
        

        #new line for fee record auto save
        from app.students.fee_service import ensure_fee_records_for_student
        ensure_fee_records_for_student(student.id)
        
        db.session.commit()


        return jsonify({
            'message': 'Student registered successfully',
            'student_id': student.id,
            'user_id': user.id,
            'classname': resolved_classname,
            'photo_url': url_for('static', filename=f'{UPLOAD_SUBDIR}/{photo_filename}', _external=True) if photo_filename else None
        }), 201

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Registration failed', 'details': str(e)}), 500
