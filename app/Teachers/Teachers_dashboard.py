from flask import Blueprint, jsonify, url_for, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.teacher_model import Teacher

from app.models.live_class import LiveClass
from app.extensions import db
from datetime import datetime
from app.utils.jitsi_meet import generate_meeting_link

from app.models.raise_issue import Issue



teacher_dashboard_bp = Blueprint('teacher_dashboard_bp', __name__, url_prefix='/api/teachers/dashboard')

@teacher_dashboard_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_teacher(id):
    teacher_data = Teacher.query.filter_by(id=id).first()

    if not teacher_data:
        return jsonify({'error': 'Teacher not found'}), 404

    # 
    photo_url = (
    url_for('static', filename=f'uploads/teachers/{teacher_data.photo}', _external=True)
    if teacher_data.photo else None
)

    return jsonify({
        "name": teacher_data.fullName,
        "mobile": teacher_data.mobile,
        "photo": photo_url,          
        "personalInfo": {
            "DateOfBirth": teacher_data.dob,
            "Gender": teacher_data.gender,
            "IDMark": teacher_data.idMark,
            "BloodGroup": teacher_data.bloodGroup,
        },
        "address": {
            "Village": teacher_data.village,
            "PO": teacher_data.po,
            "PS": teacher_data.ps,
            "PIN": teacher_data.pinCode,
            "District": teacher_data.district,
            "State": teacher_data.state
        }
    }), 200



# ========================= LIVE CLASS API =========================

@teacher_dashboard_bp.route('/create-live-class', methods=['POST'])
def create_live_class():
    data = request.json

    start_time = datetime.fromisoformat(data['start_time'])

  #meet link gnrt
    meet_link = generate_meeting_link(data['class_id'])

    
    live_class = LiveClass(
        class_id=data['class_id'],
        subject=data['subject'],
        meeting_link=meet_link,
        start_time=start_time,
        teacher_id=1  # temp for testing
    )

    db.session.add(live_class)
    db.session.commit()

    return jsonify({
        "message": "Live class created",
        "meet_link": meet_link
    })

# ========= RAISE AN ISSUE =======

@teacher_dashboard_bp.route('/raise-issue', methods=['POST'])
def raise_issue():
    data = request.json

    issue = Issue(
        sender_id=data['sender_id'],
        sender_role=data['sender_role'],
        receiver_id=data.get('receiver_id'),  # optional
        receiver_role=data['receiver_role'],
        message=data['message']
    )

    db.session.add(issue)
    db.session.commit()

    return jsonify({"message": "Issue raises successfully"})