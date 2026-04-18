# ========================= TEACHER ROUTES =========================

from flask import Blueprint, request, jsonify, send_from_directory, current_app, url_for
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, get_jwt_identity, verify_jwt_in_request
from ..extensions import db, bcrypt
from app.models.teacher_model import Teacher
from app.models.user_model import User
from app.models.student_model import StudentAttendance, Student
from app.models.assignment_model import Assignment
from app.models.Tattendance import Attendance, TeacherAttendance
from app.models.salary_model import Salary
import os, re
from app.models.class_model import Class 
from sqlalchemy import func, or_
from datetime import datetime
from werkzeug.utils import secure_filename




teacher_bp_view = Blueprint('teacher_bp_view', __name__, url_prefix='/api/teachers')

UPLOAD_FOLDER = 'static/uploads' # for assignment upload
TEACHER_UPLOAD_SUBDIR = 'uploads/teachers'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Check if uploaded file has a valid image extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def build_teacher_photo_url(teacher):
    """Return full photo URL for a teacher, or None if not available"""
    if not teacher or not getattr(teacher, "photo", None):
        return None
    return url_for('static', filename=f'uploads/teachers/{teacher.photo}', _external=True)


# ========================= REGISTER TEACHER (ADMIN ONLY) =========================
@teacher_bp_view.route('/register-teacher', methods=['POST'])
@jwt_required()
def register_teacher():
    print("DEBUG Authorization header:", request.headers.get('Authorization'))

    # --- JWT Validation ---
    try:
        verify_jwt_in_request()
    except Exception as e:
        print("JWT verification error:", e)
        return jsonify({'error': f'Token verification failed: {str(e)}'}), 401

    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    # --- Parse Form Data ---
    data = request.form.to_dict() or {}
    file = request.files.get('teacherImage')  
    print("DEBUG form data:", data)

    # --- Required Fields ---
    required = ['fullName', 'dob', 'mobile', 'email']
    missing = [k for k in required if not data.get(k)]
    if missing:
        return jsonify({'error': 'Missing required fields', 'fields': missing}), 400

    # --- Uniqueness Check ---
    if User.query.filter_by(mobile=data['mobile']).first():
        return jsonify({'error': 'Mobile number already registered'}), 409

    # --- Generate Password from DOB ---
    try:
        dob_date = datetime.strptime(data['dob'], "%Y-%m-%d")
        formatted_dob = dob_date.strftime("%d%m%Y")
        hashed_pw = bcrypt.generate_password_hash(formatted_dob).decode('utf-8')
    except Exception as e:
        return jsonify({'error': 'Invalid DOB format', 'details': str(e)}), 400

    # --- Create User Record ---
    user = User(
        username=data['mobile'],
        mobile=data['mobile'],
        password=hashed_pw,
        role='staff',
        dob=data['dob']
    )
    db.session.add(user)
    db.session.flush()

    # ================== MAIN UPLOAD LOGIC (Teacher) ==================
    photo_filename = None
    if file and allowed_file(file.filename):
        # 1) safe filename
        original_filename = secure_filename(file.filename)

        # 2) teacher upload folder: static/uploads/teachers
        upload_folder = os.path.join(current_app.static_folder, 'uploads/teachers')
        os.makedirs(upload_folder, exist_ok=True)

        # 3) unique filename (mobile + timestamp + originalname)
        unique_filename = f"{data.get('mobile')}_{int(datetime.now().timestamp())}_{original_filename}"

        # 4) full path & save
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)

        photo_filename = unique_filename
        print("✅ Teacher photo saved:", filepath)
    else:
        print("⚠️ No valid photo uploaded or invalid file type")

    # --- Create Teacher Record ---
    teacher = Teacher(
        fullName=data.get('fullName'),
        mobile=data.get('mobile'),
        dob=data.get('dob'),
        gender=data.get('gender'),
        email=data.get('email'),
        idMark=data.get('idMark'),
        bloodGroup=data.get('bloodGroup'),
        village=data.get('village'),
        po=data.get('po'),
        ps=data.get('ps'),
        pinCode=data.get('pinCode'),
        district=data.get('district'),
        state=data.get('state'),
        photo=photo_filename,
        user_id=user.id
    )

    db.session.add(teacher)
    db.session.commit()

    # --- Photo URL (same pattern as student) ---
    photo_url = (
    url_for('static', filename=f'uploads/teachers/{photo_filename}', _external=True)
    if photo_filename else None
)


    # --- Response ---
    return jsonify({
        'message': 'Teacher registered successfully',
        'teacher_id': teacher.id,
        'user_id': user.id,
        'username': data['mobile'],
        'password': formatted_dob,
        'photo_url': photo_url,
        'login_credentials': {
            'mobile': data['mobile'],
            'password': formatted_dob
        }
    }), 201


    

# ========================= GET SINGLE TEACHER =========================

@teacher_bp_view.route('/<int:teacher_id>', methods=['GET'])
def get_teacher(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({'message': 'Teacher not found'}), 404

    return jsonify({
        'id': teacher.id,
        'fullName': teacher.fullName,
        'mobile': teacher.mobile,
        'District': teacher.District,
        'photo': build_teacher_photo_url(teacher) 
    })

# ========================= GET ALL TEACHERS =========================

@teacher_bp_view.route('', methods=['GET'])
def get_all_teachers():
    teachers = Teacher.query.all()
    return jsonify([{
        'id': t.id,
        'fullName': t.fullName,
        'mobile': t.mobile,
        'District': t.District,
        'photo': build_teacher_photo_url(t)
    } for t in teachers])

# ========================= TEACHER PROFILE DETAILS =========================

@teacher_bp_view.route('/dashboard/<int:id>', methods=['GET'])
@jwt_required()
def get_teacher_details(id):
    teacher = Teacher.query.get(id)
    if not teacher:
        return jsonify({"message": "Teacher not found"}), 404

    photo_url = None
    if teacher.photo:
        photo_url = url_for('static', filename=f'uploads/teachers/{teacher.photo}', _external=True)

    return jsonify({
        "name": teacher.fullName,          
        "phone": teacher.mobile,
        "email": teacher.email,
        "photo": photo_url,
        "personalInfo":{ 
            "dob": teacher.dob,  
            "gender": teacher.gender,
            "idMark": teacher.idMark,             
            "bloodGroup": teacher.bloodGroup,
            "phone": teacher.mobile
        },    
        "address": {
            "village": teacher.village,
            "po": teacher.po,
            "ps": teacher.ps,
            "pinCode": teacher.pinCode,       
            "district": teacher.district,
            "state": teacher.state
    }
})

# ========================= CLASS STUDENTS VIEW =========================

@teacher_bp_view.route('/class-students', methods=['GET'])
@jwt_required()
def get_students_by_class():
    classname = request.args.get('classname', '').strip().lower()
    section = request.args.get('section', '').strip().lower()
 
    claims = get_jwt()
    teacher_id = claims.get("teacher_id")

    teacher = Teacher.query.filter_by(id=teacher_id).first()
    if not teacher:
        return jsonify({"message": "Teacher not found"}), 404

    # Flexible filtering
    students = Student.query.filter(
        func.replace(func.lower(Student.classname), ' ', '') == classname.replace(' ', ''),
        func.lower(func.coalesce(Student.section, '')) == section
    ).all()

    student_data = [
        {"id": s.id, "roll_no": s.admissionNo, "name": s.FullName}
        for s in students
    ]

    data = {
        "teacher": {
            "id": teacher.id,
            "name": teacher.fullName,
            "email": teacher.email,
            "phone": teacher.mobile,
            "photo": build_teacher_photo_url(teacher) 
        },
        "students": student_data
    }

    return jsonify(data), 200

    # ========================= SUBMIT STUDENT ATTENDANCE =========================

@teacher_bp_view.route('/submit-attendance', methods=['POST'])
@jwt_required()
def submit_attendance():
    data = request.get_json()
    print("DEBUG - Incoming Attendance Payload:", data)

    ui_class_no = data.get('class_id')   # frontend se 1, 2, 3...
    section = data.get('section')
    month = data.get('month')
    date_str = data.get('date')
    attendance_list = data.get('attendance')

    # ------------ basic validation ------------
    if not (ui_class_no and section and month and date_str and attendance_list):
        print("DEBUG ERROR: Missing some fields")
        return jsonify({"error": "Missing required fields"}), 400

    try:
        ui_class_no = int(ui_class_no)
    except:
        print("DEBUG ERROR: Invalid class number:", ui_class_no)
        return jsonify({"error": "Invalid class number"}), 400

    # ------------ resolve real class_id ------------
    # Try: assume ID == class number
    class_obj = Class.query.get(ui_class_no)

    # Agar future me IDs change ho jayein to name se bhi try kar sakte hain
    if not class_obj:
        name1 = f"class{ui_class_no}"
        name2 = f"class {ui_class_no}"
        name3 = f"Class {ui_class_no}"
        class_obj = Class.query.filter(
            or_(
                Class.name.ilike(name1),
                Class.name.ilike(name2),
                Class.name.ilike(name3),
            )
        ).first()

    if not class_obj:
        # Debug ke liye existing classes print
        all_classes = Class.query.with_entities(Class.id, Class.name).all()
        print("DEBUG - No class found for:", ui_class_no, "Available:", all_classes)
        return jsonify({
            "error": f"No class found in DB for Class {ui_class_no}"
        }), 400

    class_id = class_obj.id
    print("DEBUG - Resolved class_id:", class_id, "name:", class_obj.name)

    # ------------ date convert ------------
    from datetime import datetime
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    # ------------ duplicate check ------------
    existing = StudentAttendance.query.filter_by(
        class_id=class_id,
        section=section,
        attendance_date=date_obj
    ).first()

    if existing:
        return jsonify({"error": "Attendance already submitted for this date"}), 409

    # ------------ save attendance ------------
    try:
        for entry in attendance_list:
            student_id_raw = entry.get("student_id")
            status = entry.get("status")

            try:
                student_id = int(student_id_raw)
            except:
                return jsonify({"error": f"Invalid student_id: {student_id_raw}"}), 400

            record = StudentAttendance(
                student_id=student_id,
                class_id=class_id,
                section=section,
                month=month,
                attendance_date=date_obj,
                status=status
            )
            db.session.add(record)

        db.session.commit()
        return jsonify({"message": "Attendance submitted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print("ERROR while saving attendance:", e)
        return jsonify({"error": "Internal server error"}), 500



# ========================= ASSIGNMENT UPLOAD =========================

def parse_and_normalize_class(raw: str):
    if not raw:
        return None, None
    raw = raw.strip()
    # try to find digits anywhere
    m = re.search(r'(\d+)', raw)
    if m:
        class_num = m.group(1)
        normalized = f"Class {int(class_num)}"
        return class_num, normalized
    
    return None, " ".join(raw.split())

@teacher_bp_view.route('/assign-work', methods=['POST'])
@jwt_required()
def assign_work():
    identity = get_jwt_identity()
    claims = get_jwt()
    teacher_id = int(identity)
    teacher_role = str(claims.get("role")).lower().strip()
    if teacher_role != "staff":
        return jsonify({'error': 'Unauthorized'}), 403

    title = (request.form.get('title') or "").strip()
    subject = (request.form.get('subject') or "").strip()
    description = (request.form.get('description') or "").strip()
    raw_class = (request.form.get('classname') or "").strip()
    section = (request.form.get('section') or "").strip()
    file = request.files.get('file')

    if not all([title, subject, raw_class, section]):
        return jsonify({'error': 'Missing required fields'}), 400

    class_num, normalized_classname = parse_and_normalize_class(raw_class)
    classname_to_save = normalized_classname if normalized_classname else raw_class

    filename = None
    if file and file.filename and file.filename.strip():
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

    assignment = Assignment(
        title=title,
        subject=subject,
        description=description,
        filename=filename,
        classname=classname_to_save,
        section=section,
        teacher_id=teacher_id
    )
    db.session.add(assignment)
    db.session.commit()
    return jsonify({'message': 'Assignment uploaded successfully'}), 201

# ---------- get_sections endpoint (match many formats) ----------
@teacher_bp_view.route('/sections', methods=['GET'])
@jwt_required()
def get_sections():
    raw = (request.args.get('classId') or "").strip()

    if not raw:
        return jsonify({'error': 'classId is required'}), 400

    # Extract numeric part → works for: Class1, class 1, class1, 1, Class 1
    m = re.search(r'(\d+)', raw)
    if not m:
        return jsonify([]), 200

    class_num = m.group(1)
    classname_db = f"Class {class_num}"    # <-- Normalized class name

    print("DEBUG → Looking for classname:", classname_db)

    # Match ANY version in DB
    possible_matches = [
        classname_db,           
        classname_db.lower(),   
        f"class{class_num}",    
        f"Class{class_num}",    
        class_num               
    ]

    print("DEBUG → All match patterns:", possible_matches)

    sections = (
        db.session.query(Student.section)
        .filter(Student.classname.in_(possible_matches))
        .distinct()
        .all()
    )

    section_list = [s[0] for s in sections if s[0]]

    print("DEBUG → Sections found:", section_list)

    return jsonify(section_list), 200


# ---------- get_assignments endpoint (same tolerant matching) ----------
@teacher_bp_view.route('/assignments/view', methods=['GET'])
@jwt_required()
def get_assignments():
    teacher_id = get_jwt_identity()
    raw = (request.args.get('classId') or "").strip()
    section = (request.args.get('section') or "").strip()

    if not raw or not section:
        return jsonify({'error': 'classId and section are required'}), 400

    class_num, normalized = parse_and_normalize_class(raw)
    candidates = set([raw])
    if normalized and class_num:
        candidates.update({normalized, f"Class{class_num}", class_num})
    candidates = {c for c in candidates if c}

    print("get_assignments - candidates for classname match:", candidates)

    assignments = Assignment.query.filter(
        Assignment.teacher_id == teacher_id,
        Assignment.section == section,
        Assignment.classname.in_(list(candidates))
    ).all()

    data = [{
        "id": a.id,
        "title": a.title,
        "subject": a.subject,
        "description": a.description,
        "file_path": a.filename,
        "classname": a.classname,
        "section": a.section,
    } for a in assignments]

    return jsonify(data), 200



@teacher_bp_view.route('/edit/assignment/<int:id>', methods=['PUT'])
@jwt_required()
def edit_assignment(id):
    data = request.get_json()
    assignment = Assignment.query.get(id)
    if not assignment:
        return jsonify({"message": "Assignment not found"}), 404

    assignment.title = data.get('title', assignment.title)
    assignment.subject = data.get('subject', assignment.subject)
    assignment.description = data.get('description', assignment.description)
    db.session.commit()
    return jsonify({"message": "Assignment updated successfully"}), 200

@teacher_bp_view.route('/delete/assignment/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_assignment(id):
    assignment = Assignment.query.get(id)
    if not assignment:
        return jsonify({"message": "Assignment not found"}), 404

    # Corrected: use assignment.filename instead of file_path
    if assignment.filename:
        filepath = os.path.join(UPLOAD_FOLDER, assignment.filename)
        if os.path.exists(filepath):
            os.remove(filepath)

    db.session.delete(assignment)
    db.session.commit()
    return jsonify({"message": "Assignment deleted successfully"}), 200


@teacher_bp_view.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


# --------- view profile details for teacher --------- 
@teacher_bp_view.route('/profile', methods=['GET'])
@jwt_required()
def get_teacher_profile():
    claims = get_jwt() 
    user_id = get_jwt_identity()
    teacher_id = claims.get("teacher_id")

    teacher = Teacher.query.filter_by(id=teacher_id, user_id=user_id).first()
    if not teacher:
        return jsonify({"error": "Teacher not found"}), 404

    return jsonify({
        "id": teacher.id,
        "fullName": teacher.fullName,
        "mobile": teacher.mobile,
        "email": teacher.email,
        "dob": teacher.dob,
        "gender": teacher.gender,
        "photo": build_teacher_photo_url(teacher)
    }), 200



# ========================= TEACHER ATTENDANCE VIEW =========================

@teacher_bp_view.route('/attendance/view', methods=['GET'])
@jwt_required()
def view_teacher_attendance():
    claims = get_jwt()
    teacher_id = claims.get("teacher_id")
    month = request.args.get('month')

    teacher = Teacher.query.filter_by(id=teacher_id).first()


    records = TeacherAttendance.query.filter_by(teacher_id=teacher_id, month=month).all()
    total_days = len(records)
    present_days = sum(1 for r in records if r.status == 'Present')
    percent = round((present_days / total_days) * 100, 2) if total_days > 0 else 0

    data = {
        "teacher": {
            "id": teacher.id,
            "name": teacher.fullName,
            "email": teacher.email,
            "photo": build_teacher_photo_url(teacher),
            "phone": teacher.mobile
        },
        "month": month,
        "percentage": f"{percent}%",
        #"records": [{"date": '01.01.2015', "status": 'present'}]
        "records": [{"date": r.attendance_date.strftime("%Y-%m-%d"), "status": r.status} for r in records]
    }
    return jsonify(data)

# ========================= TEACHER SALARY VIEW =========================

@teacher_bp_view.route('/salary', methods=['GET'])
@jwt_required()
def view_salary():
    claims = get_jwt()
    teacher_id = claims.get("teacher_id")

    if not teacher_id:
        return jsonify({"error": "Teacher ID not found in token"}), 400

    try:
        teacher_id = int(teacher_id)
    except ValueError:
        return jsonify({"error": "Invalid teacher ID in token"}), 400

    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({"error": "Teacher not found"}), 404

    salaries = Salary.query.filter_by(teacher_id=teacher_id).all()

    total_earned = sum(s.amount for s in salaries if s.status and s.status.lower() == 'paid')
    total_due = sum(s.amount for s in salaries if s.status and s.status.lower() == 'due')

    salary_history = []
    for s in salaries:
        salary_history.append({
            "month": s.month,
            "amount": s.amount,
            "payment_date": (
                s.payment_date.strftime("%Y-%m-%d") if s.payment_date else "Pending"
            ),
            "status": s.status
        })

    teacher_info = {
        "name": teacher.fullName,
        "phone": teacher.mobile,
        "photo": build_teacher_photo_url(teacher),
        "email": teacher.email
    }

    return jsonify({
        "teacher": teacher_info,
        "total_earned": total_earned,
        "total_due": total_due,
        "salary_history": salary_history
    })

