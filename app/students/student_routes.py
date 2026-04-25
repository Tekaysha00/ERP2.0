from flask import Blueprint, jsonify, send_from_directory, request,url_for, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.student_model import Student
from app.models.assignment_model import Assignment, ExamResult
from app.models.user_model import User
from ..extensions import db
from flask_cors import cross_origin
from sqlalchemy import func
from io import BytesIO
from app.utils.helpers import format_classname
import os
from werkzeug.utils import secure_filename
from app.models.homework_model import Homework


student_bp_view = Blueprint('student_bp_view', __name__, url_prefix='/api/student')
UPLOAD_FOLDER = 'static/uploads'


# ====== homework - upload =====
ALLOWED_EXTENSIONS = {'pdf', 'mp3', 'wav', 'mp4', 'mov', 'webm'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------- HOMEWORK-DOWNLOAD ------ 

@student_bp_view.route('/homework', methods=['GET'])
@jwt_required()
def view_homework():
    print("check_hw")

    identity = get_jwt_identity()       
    claims = get_jwt()                  
    user_id = int(identity)             
    
    student = Student.query.filter_by(user_id=user_id).first()

    photo_url = None
    if student.photo:
        photo_url = url_for('static', filename=f'uploads/students/{student.photo}', _external=True)
    print("Student fetched:", student)


    if not student or claims.get("role") != "student":
        return jsonify({'error': 'Unauthorized'}), 403
    
    if not student.classname:
        return jsonify({'error': 'Student class not set'}), 400
    
    print("Student classname:", student.classname)
    assignments = Assignment.query.filter(
    db.func.replace(db.func.lower(db.func.trim(Assignment.classname)), " ", "") ==
    student.classname.strip().lower().replace(" ", "")
).all()
    print("Assignments found:", len(assignments))

    result = []
    response = {
        "student": {
            "name": student.FullName,
            "photo": photo_url,
            "phone": student.phone,
            "rollNo": student.rollNo,
            "class": format_classname(student.classname)
        },
        "assignments": []
    }

    if not assignments:
        response["assignments"] = [
            {
                "title": "Math Homework",
                "subject": "Mathematics",
                "description": "Solve exercise 1.1 questions 1 to 10",
                "download_url": None
            },
            {
                "title": "Science Project",
                "subject": "Science",
                "description": "Make a model of solar system",
                "download_url": None
            }
        ]
    else:
        for a in assignments:
            response['assignments'].append({
                'title': a.title,
                'subject': a.subject,
                'description': a.description,
                'download_url': f'/api/student/download/{a.filename}' if a.filename else None
            })
    return jsonify(response)


@student_bp_view.route('/download/<filename>', methods=['GET'])
@cross_origin()
def download_assignment(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)



# ========= homework-upload ===========

@student_bp_view.route('/upload-homework', methods=['POST'])
@jwt_required()
def upload_homework():

    file = request.files.get('file')
    assignment_id = request.form.get('assignment_id')

    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    # 🔐 Get student from JWT
    user_id = get_jwt_identity()
    student = Student.query.filter_by(user_id=user_id).first()

    if not student:
        return jsonify({"error": "Student not found"}), 404

    filename = secure_filename(file.filename)

    upload_folder = os.path.join('uploads/homework')
    os.makedirs(upload_folder, exist_ok=True)

    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)

    ext = filename.split('.')[-1].lower()
    if ext in ['mp3', 'wav']:
        file_type = 'audio'
    elif ext in ['mp4', 'mov','webm']:
        file_type = 'video'
    else:
        file_type = 'pdf'

    assignment_id = int(assignment_id) if assignment_id else None

    new_hw = Homework(
        student_id=student.id,              
        student_name=student.FullName,      
        file_url=file_path,
        assignment_id=assignment_id,
        file_type=file_type
    )

    db.session.add(new_hw)
    db.session.commit()

    return jsonify({
        "message": "Homework uploaded successfully",
        "file_url": file_path
    })



# ====== view homework uploaded ==
@student_bp_view.route('/my-homeworks/<int:student_id>', methods=['GET'])
def get_my_homeworks(student_id):

    data = Homework.query.filter_by(student_id=student_id).all()

    result = []
    for hw in data:
        result.append({
            "id": hw.id,
            "file_url": hw.file_url,
            "file_type": hw.file_type,
            "created_at": hw.created_at
        })

    return jsonify(result)

# ----- STUDENTS - ACADEMIC - UPDATES ------- 
 
@student_bp_view.route('/academic-update', methods=['GET'])
@jwt_required()
def academic_update():
    
    claims = get_jwt()
    student_id = claims.get("student_id")

    if not student_id:
        return jsonify({"error": "Unauthorized or invalid token"}), 403

    try:
        student_id_int = int(student_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid student_id in token"}), 400

    # React se term aa rahi hai
    selected_term = (request.args.get('term') or 'Term 1').strip().title()

    # Record fetch
    record = ExamResult.query.filter_by(
        student_id=student_id_int,
        exam_name=selected_term
    ).first()

    has_result = bool(record and record.result_file_data)
    has_admit = bool(record and record.admit_card_data)

    # ---- file URLs (agar tumne download routes ko public kiya hai) ----
    result_file_url = (
        url_for(
            'student_bp_view.download_result_file',
            term=selected_term,
            student_id=student_id_int,    # 👈 important
            _external=True
        )
        if has_result else None
    )
    admit_card_url = (
        url_for(
            'student_bp_view.download_admit_card',
            term=selected_term,
            student_id=student_id_int,    # 👈 important
            _external=True
        )
        if has_admit else None
    )

    if record:
        score = record.score if record.score is not None else 0
        response = {
            "term": record.exam_name,
            "score": score,
            "percentage": f"{score}%",
            "result_download": result_file_url,
            "admit_download": admit_card_url,
            "remarks": record.remarks or "",   
            "status": "Result available" if (has_result or has_admit)
                      else "Record exists but files not uploaded"
        }
    else:
        response = {
            "term": selected_term,
            "percentage": "0%",
            "result_download": None,
            "admit_download": None,
            "remarks": "",                    
            "status": f"No record found for term '{selected_term}'"
        }

    return jsonify(response), 200




# -------------------- File Download --------------------
@student_bp_view.route('/file/result', methods=['GET'])
def download_result_file():
    
    #student_id = request.args.get("student_id")
    term = (request.args.get("term") or "Term 1").strip().title()

    '''if not student_id:
        return jsonify({"error": "student_id is required"}), 400

    try:
        student_id_int = int(student_id)
    except ValueError:
        return jsonify({"error": "Invalid student_id"}), 400'''

    # Fetch record
    record = ExamResult.query.filter_by(
        #student_id=student_id_int,
        exam_name=term
    ).first()

    if not record or not record.result_file_data:
        return jsonify({"error": "Result file not found"}), 404

    # Send file from database
    return send_file(
        BytesIO(record.result_file_data),
        mimetype=record.result_file_mimetype or "application/octet-stream",
        as_attachment=True,
        download_name=record.result_file_name or f"{term}_result.pdf",
    )


# ======= ADmit Download ===

@student_bp_view.route('/file/admit', methods=['GET'])
def download_admit_card():
    # student_id must come from URL
    #student_id = request.args.get("student_id")
    term = (request.args.get("term") or "Term 1").strip().title()

    '''if not student_id:
        return jsonify({"error": "student_id is required"}), 400

    try:
        student_id_int = int(student_id)
    except ValueError:
        return jsonify({"error": "Invalid student_id"}), 400'''

    # Fetch record from DB
    record = ExamResult.query.filter_by(
        #student_id=student_id_int,
        exam_name=term
    ).first()

    if not record or not record.admit_card_data:
        return jsonify({"error": "Admit card not found"}), 404

    # Send file back to browser
    return send_file(
        BytesIO(record.admit_card_data),
        mimetype=record.admit_card_mimetype or "application/octet-stream",
        as_attachment=True,
        download_name=record.admit_card_name or f"{term}_admit_card.pdf"
    )



# --------- Details --------- 

@student_bp_view.route('/details', methods=['GET'])
@jwt_required()
def student_details():
    """
   
    """
    claims = get_jwt()
    student_id = claims.get("student_id")

    if not student_id:
        return jsonify({"error": "Unauthorized or invalid token"}), 403

    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    photo_url = None
    if student.photo:
        photo_url = url_for('static', filename=f'uploads/students/{student.photo}', _external=True)

    response = {
        "id": student.id,
        "name": student.FullName,
        "class": format_classname(student.classname),
        "phone": student.phone,
        "rollNo": student.rollNo,
        "photo": photo_url,
    }

    return jsonify(response), 200
