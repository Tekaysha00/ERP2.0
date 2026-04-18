from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
import os, uuid
from app import db
from app.models.assignment_model import Assignment

academic_bp = Blueprint('academic_bp', __name__, url_prefix='/admin')
UPLOAD_FOLDER = 'static/uploads/academic'

@academic_bp.route('/upload-academic', methods=['POST'])
@jwt_required()
def upload_academic():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    content_type = request.content_type or ''
    current_app.logger.info("content_type=%s", content_type) 

    # Decide source of data/files
    if content_type.startswith('multipart/form-data'):
        data = request.form
        files = request.files
    elif content_type.startswith('application/json'):
        data = (request.get_json(silent=True) or {})
        files = {}
    else:
        return jsonify({
            'error': 'unsupported_media_type',
            'expected': 'multipart/form-data', 
            'got': content_type
        }), 415

    # Collect fields safely
    student_id = data.get('student_id')
    exam_name = data.get('exam_name')
    score_raw = data.get('score')

    result_file = files.get('result_file')
    admit_file = files.get('admit_card_file')

    # Validate
    errors = []
    if not student_id: errors.append('student_id is required')
    if not exam_name: errors.append('exam_name is required')
    if score_raw is None: errors.append('score is required')

    if content_type.startswith('multipart/form-data'):
        if not result_file or result_file.filename == '':
            errors.append('result_file is required')
        if not admit_file or admit_file.filename == '':
            errors.append('admit_card_file is required')

    if errors:
        return jsonify({'error': 'validation_failed', 'details': errors}), 400

    # Parse score
    try:
        score = float(str(score_raw).strip())
    except Exception:
        return jsonify({'error': 'invalid_score', 'details': 'score must be a number'}), 400

    # Save files with unique names
    def save_if_present(fileobj):
        if not fileobj: return None
        fname = f"{uuid.uuid4().hex}_{secure_filename(fileobj.filename)}"
        fileobj.save(os.path.join(UPLOAD_FOLDER, fname))
        return fname

    result_filename = save_if_present(result_file)
    admit_filename  = save_if_present(admit_file)

    
    try:
        record = Assignment(
            student_id=student_id,
            exam_name=exam_name,
            score=score,
            result_file=result_filename,
            admit_card_file=admit_filename
        )
        db.session.add(record)
        db.session.commit()
        return jsonify({'message': 'Academic record uploaded successfully', 'id': record.id}), 200
    except Exception as e:
        current_app.logger.exception("upload_academic failed")
        db.session.rollback()
        return jsonify({'error': 'internal_error'}), 500