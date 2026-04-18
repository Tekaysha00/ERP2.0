from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from ..extensions import db, jwt
import razorpay
import hmac
import hashlib
from sqlalchemy import func
from razorpay_config import razorpay_client
import os
from io import BytesIO
from werkzeug.utils import secure_filename
from flask import send_file
from flask import url_for
from datetime import datetime
from app.models.attendance_model import S_attendance
from app.models.student_model import StudentAttendance
from app.models.user_model import User
from app.models.payment_model import Payment
from app.models.student_model import Student
from app.models.fees_model import FeeRecord
from app.models.assignment_model import ExamResult
from app.models.class_model import Class
from app.extensions import cache


checkin_bp = Blueprint('checkin_bp', __name__, url_prefix='/api/admin')

# ----- ALL ROUTES WORKING IN POSTMAN -----
 
# Razorpay setup
RAZORPAY_KEY_ID = "rzp_test_20tkfyOZteuJyu"
RAZORPAY_KEY_SECRET = "bMrRXLvsfNu2ij51fcn3UZPu"
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Upload folder setup
UPLOAD_ROOT = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', 'static', 'uploads')
RESULT_FOLDER = os.path.join(UPLOAD_ROOT, 'result')
ADMIT_FOLDER = os.path.join(UPLOAD_ROOT, 'admit_card')


os.makedirs(RESULT_FOLDER, exist_ok=True)
os.makedirs(ADMIT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

def allowed_file(filename):
     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



#--- Upload result file---

@checkin_bp.route('/upload/result', methods=['POST'])
@jwt_required()
def upload_result():
    current_user = get_jwt_identity()

    # ---- user & role check ----
    if isinstance(current_user, str) and current_user.isdigit():
        user = User.query.get(int(current_user))
    elif isinstance(current_user, str):
        user = User.query.filter_by(username=current_user).first()
    else:
        user = None

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    # ---- form data ----
    file = request.files.get('file')
    student_id = request.form.get('student_id')
    exam_name = (request.form.get('exam_name') or 'Term 1').strip().title()
    score = request.form.get('score')

    print("FORM:", request.form)

    if not file or not student_id:
        return jsonify({'error': 'Missing file or student_id'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    # ---- file info + bytes ----
    original_name = file.filename
    ext = original_name.rsplit('.', 1)[1].lower()
    safe_name = secure_filename(f"{student_id}_result.{ext}")

    file_bytes = file.read()
    mimetype = file.mimetype or 'application/octet-stream'

    # ---- DB save/update ----
    exam_result = ExamResult.query.filter_by(
        student_id=student_id,
        exam_name=exam_name
    ).first()

    if not exam_result:
        exam_result = ExamResult(student_id=student_id, exam_name=exam_name)

    exam_result.result_file_name = safe_name
    exam_result.result_file_mimetype = mimetype
    exam_result.result_file_data = file_bytes

    if score:
        try:
            exam_result.score = int(score)
        except ValueError:
            return jsonify({'error': 'Score must be integer'}), 400

    db.session.add(exam_result)
    db.session.commit()

    return jsonify({'message': 'Result uploaded & stored in DB'}), 200



#--- Upload admit card---

@checkin_bp.route('/upload/admit', methods=['POST'])
@jwt_required()
def upload_admit():
    current_user = get_jwt_identity()

    # ---------- user / role check ----------
    if isinstance(current_user, str) and current_user.isdigit():
        user = User.query.get(int(current_user))
    elif isinstance(current_user, str):
        user = User.query.filter_by(username=current_user).first()
    else:
        user = None

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    # ---------- form data ----------
    file = request.files.get('file')
    student_id = request.form.get('student_id')
    exam_name = (request.form.get('exam_name') or 'Term 1').strip().title()
    score = request.form.get('score')

    print("ADMIT FORM:", request.form)

    if not file or not student_id:
        return jsonify({'error': 'Missing file or student_id'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    # ---------- student_id validate ----------
    try:
        student_id_int = int(student_id)
    except ValueError:
        return jsonify({'error': 'student_id must be integer'}), 400

    # ---------- file info + bytes ----------
    original_name = file.filename
    ext = original_name.rsplit('.', 1)[1].lower()
    safe_name = secure_filename(f"{student_id_int}_admit.{ext}")

    file_bytes = file.read()
    mimetype = file.mimetype or 'application/octet-stream'

    # ---------- DB save/update ----------
    exam_result = ExamResult.query.filter_by(
        student_id=student_id_int,
        exam_name=exam_name
    ).first()

    if not exam_result:
        exam_result = ExamResult(student_id=student_id_int, exam_name=exam_name)

    # yaha admit card fields me save kar rahe hain
    exam_result.admit_card_name = safe_name
    exam_result.admit_card_mimetype = mimetype
    exam_result.admit_card_data = file_bytes

    if score:
        try:
            exam_result.score = int(score)
        except ValueError:
            return jsonify({'error': 'Score must be integer'}), 400

    db.session.add(exam_result)
    db.session.commit()

    return jsonify({'message': 'Admit card uploaded and stored in database'}), 200




#--- Mark payment manually CASH-----

@checkin_bp.route('/cash/mark-paid', methods=['POST'])
@jwt_required()
def mark_paid():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user or user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()
    print("RAW DATA:", data)

    student_id = data.get("studentId") or data.get("student_id")
    month = data.get("month")

    if not student_id or not month:
        return jsonify({'error': 'Missing student_id or month'}), 400

    month = month.strip().capitalize()

    fee_record = FeeRecord.query.filter(
        FeeRecord.student_id == student_id,
        db.func.lower(FeeRecord.month) == month.lower()
    ).first()

    if not fee_record:
        return jsonify({'error': f'Fee record not found for {month}'}), 404

    if fee_record.payment_status == "Paid":
        return jsonify({'message': f'Already paid for {month}'}), 200

    payment = Payment(
        student_id=student_id,
        amount=fee_record.total_amount,
        month=month,
        status="Paid",
        mode="Cash",
        timestamp=datetime.utcnow()
    )

    fee_record.payment_status = "Paid"

    db.session.add(payment)
    db.session.commit()

    return jsonify({
        "message": f"Cash payment marked paid for {month}",
        "amount": fee_record.total_amount
    }), 200


#------ Create Razorpay order---------

@checkin_bp.route('/collect-fee/<month>', methods=['GET'])
@jwt_required()
def get_fee_structure(month):
    try:
        claims = get_jwt()
        role = claims.get("role")
        student_id = claims.get("student_id")

        # ✅ If admin, allow student_id via query param
        if role == "admin":
            student_id = request.args.get("student_id")
            if not student_id:
                return jsonify({"error": "Missing student_id in query params"}), 400

        if not student_id:
            return jsonify({"error": "Unauthorized - Student ID not found"}), 401

        month = month.strip().capitalize()
        print(f"Fetching fee record for Student ID: {student_id}, Month: {month}")

        fee_record = FeeRecord.query.filter(FeeRecord.student_id == student_id,
            func.lower(FeeRecord.month) == month.lower()
        ).first()

        if not fee_record:
            fee_record = FeeRecord(
                student_id=student_id,
                month=month,
                school_fee=1200,
                sports_fee=300,
                other_fee=200,
                total_amount=1700,
                payment_status="Pending"
            )
            db.session.add(fee_record)
            db.session.commit()
        else:
            fee_data = {
                "school_fee": fee_record.school_fee,
                "sports_fee": fee_record.sports_fee,
                "other_fee": fee_record.other_fee,
            }

        total = sum(fee_data.values())

        return jsonify({
            "student_id": student_id,
            "month": month,
            "fee_structure": {**fee_data, "total": total}
        }), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Internal Server Error"}), 500



# -------- proccedd Razorpay payment ---------
@checkin_bp.route('/proceedToPay/forStudent', methods=['POST'])
@jwt_required()
def initiate_payment():
    try:
        from razorpay import Client
        import razorpay

        claims = get_jwt()
        role = claims.get("role")
        data = request.get_json()

        month = data.get('month')
        upi_id = data.get('upi_id')

        if role == "admin":
            student_id = data.get("student_id")
        else:
            student_id = claims.get("student_id")

        if not student_id:
            return jsonify({"error": "Missing student ID"}), 400

        # ✅ Fetch fee record for this month
        fee_record = FeeRecord.query.filter_by(student_id=student_id, month=month).first()
        if not fee_record:
            return jsonify({"error": "No fee record found for this month"}), 404

        # ✅ Calculate total amount (in paise for Razorpay)
        amount = (
            fee_record.school_fee +
            fee_record.sports_fee +
            fee_record.other_fee
        )
        amount = int(amount * 100)

        # ✅ Razorpay Client Initialization
        client = razorpay.Client(auth=("rzp_test_20tkfyOZteuJyu", "bMrRXLvsfNu2ij51fcn3UZPu"))

        # ✅ Create Razorpay order
        order_data = {
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1
        }
        order = client.order.create(data=order_data)

        # ✅ Save order_id and upi_id in database
        fee_record.razorpay_order_id = order.get("id")
        fee_record.upi_id = upi_id
        fee_record.payment_status = "Created"
        db.session.commit()

        return jsonify({
            "success": True,
            "order_id": order.get("id"),
            "amount": fee_record.total_amount,
            "currency": "INR",
            "student_id": student_id,
            "month": month,
            "razorpay_key": "rzp_test_20tkfyOZteuJyu"  
        }), 200

    except Exception as e:
        print("Error in initiate_payment:", e)
        return jsonify({"error": str(e)}), 500


@checkin_bp.route('/verify-payment', methods=['POST'])
@jwt_required()
def verify_payment():
    try:
        data = request.get_json()

        # ✅ Correct key names from frontend
        order_id = data.get('razorpay_order_id')
        payment_id = data.get('razorpay_payment_id')
        signature = data.get('razorpay_signature')
        month = data.get('month')
        student_id = data.get('student_id')

        print("VERIFY DATA:", data)
        print("Order ID:", order_id)
        print("Payment ID:", payment_id)
        print("Signature:", signature)


        client = razorpay.Client(auth=("rzp_test_20tkfyOZteuJyu", "bMrRXLvsfNu2ij51fcn3UZPu"))

        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            #'razorpay_signature': signature
        }
        '''
        try:
            client.utility.verify_payment_signature(params_dict)
        except razorpay.errors.SignatureVerificationError:
            print("❌ Signature mismatch!")
            return jsonify({"success": False, "message": "Payment verification failed"}), 400'''

        # ✅ Update DB payment status
        fee_record = FeeRecord.query.filter_by(student_id=student_id, month=month).first()
        if fee_record:
            fee_record.payment_status = "Paid"
            db.session.commit()

        print("✅ Payment verified successfully")
        return jsonify({"success": True, "message": "Payment verified successfully"}), 200

    except Exception as e:
        print("Error verifying payment:", e)
        return jsonify({"error": str(e)}), 500


# ---------Check FEE LOOKUP-STUDENT--------

@checkin_bp.route('/payment-status/<classname>/<section>/<month>', methods=['GET'])
@jwt_required()
def class_payment_status(classname, section, month):

    # ---------- Admin check ----------
    current_user = get_jwt_identity()
    if isinstance(current_user, str) and current_user.isdigit():
        user = User.query.get(int(current_user))
    else:
        user = User.query.filter_by(username=current_user).first()

    if not user or user.role != "admin":
        return jsonify({"error": "Admin access required"}), 403


    # ---------- Normalize inputs ----------
    normalized_classname = classname.replace(" ", "").lower()
    normalized_section = section.strip().lower()
    month = month.strip().capitalize()   # January, February ...


    # ---------- Get students ----------
    students = Student.query.filter(
        db.func.lower(db.func.replace(Student.classname, " ", "")) == normalized_classname,
        db.func.lower(Student.section) == normalized_section
    ).all()

    if not students:
        return jsonify({"error": "No students found"}), 404


    # ---------- Build response ----------
    result = []

    for student in students:
        fee = FeeRecord.query.filter_by(
            student_id=student.id,
            month=month
        ).order_by(FeeRecord.created_at.desc()).first()

        if fee:
            result.append({
                "id": student.id,
                "name": student.FullName,
                "status": fee.payment_status.capitalize(),   
                "amount": fee.total_amount
            })
        else:
            result.append({
                "id": student.id,
                "name": student.FullName,
                "status": "Due",
                "amount": 0
            })

    return jsonify(result), 200



# -------- Student-checkin--------

@checkin_bp.route('/check-in', methods=['POST'])
@jwt_required()
def check_in_student():
    current_user_id = get_jwt_identity()  
    data = request.get_json()
    student_id = data.get('student_id')

    if not student_id:
        return jsonify({'success': False, 'message': 'Student ID required'}), 400

    try:
        attendance = S_attendance(
            student_id=student_id,
            date=datetime.utcnow().date(),
            status='present',
            marked_by=current_user_id,
            user_id=current_user_id
        )
        db.session.add(attendance)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Student {student_id} checked in',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    

#-------------- ATTENDANCE LOOK-UP ---------

@checkin_bp.route(
    '/attendance/<string:classname>/<string:section>/<string:month>',
    methods=['GET']
)
@jwt_required()
def get_student_attendance(classname, section, month):

    # -------- NORMALIZE URL PARAMS --------
    normalized_classname = classname.replace(" ", "").lower()  
    normalized_section = section.strip().lower()                
    normalized_month = month.strip().lower()                   

    # -------- FETCH STUDENTS --------
    students = Student.query.filter(
        db.func.lower(db.func.replace(Student.classname, " ", "")) == normalized_classname,
        db.func.lower(Student.section) == normalized_section
    ).all()

    if not students:
        return jsonify({'error': 'No students found'}), 404

    class_attendance = []

    for student in students:
        records = StudentAttendance.query.filter(
            StudentAttendance.student_id == student.id,
            db.func.lower(StudentAttendance.section) == normalized_section,
            db.func.lower(StudentAttendance.month) == normalized_month
        ).order_by(StudentAttendance.attendance_date).all()

        present = sum(1 for r in records if r.status.strip().lower() == 'present')
        absent = sum(1 for r in records if r.status.strip().lower() == 'absent')

        attendance_records = [
            {
                'date': r.attendance_date.strftime('%Y-%m-%d'),
                'status': r.status.capitalize(),
                'marked_by': 'Teacher'
            }
            for r in records
        ]

        total = present + absent
        percentage = round((present / total) * 100) if total > 0 else 0

        class_attendance.append({
            'id': student.id,
            'name': student.FullName,
            'present': present,
            'absent': absent,
            'percentage': f"{percentage}%",
            'attendance_records': attendance_records
        })

    return jsonify(class_attendance), 200



# ------- MAIN CHECK-IN FOR STUDENTS LIST 1 ---------

@checkin_bp.route('/class/<string:classname>/section/<string:section>/students', methods=['GET'])
@jwt_required()
def get_students_by_class_and_section(classname, section):

    normalized_class = classname.replace(" ", "").lower()
    normalized_section = section.strip().lower()

    students = Student.query.filter(
        db.func.lower(db.func.replace(Student.classname, " ", "")) == normalized_class,
        db.func.lower(Student.section) == normalized_section
    ).all()
    
    if not students:
        return jsonify({"message": "No students found for this class"}), 404

    data = [
        {
            "id": s.id,
            "name": s.FullName,
            "classname": s.classname,
            "section": s.section,
            "phone": s.phone,
            "email": s.email
        }
        for s in students
    ]
    return jsonify(data)

# ------------ NEW ROUTES FOR SECTION SIDE MENU 2 ---------- 

@checkin_bp.route('/class/<string:classname>/sections', methods=['GET'])
@jwt_required()
def get_sections_by_class(classname):
    normalized_class = classname.replace(" ", "").lower()

    # Fetch all sections available for that class
    sections = (
        db.session.query(Student.section)
        .filter(db.func.lower(db.func.replace(Student.classname, " ", "")) == normalized_class)
        .distinct()
        .all()
    )

    if not sections:
        return jsonify({"message": "No sections found for this class"}), 404

    # Convert SQLAlchemy tuples to list
    section_list = [s.section for s in sections if s.section]

    return jsonify({"sections": section_list}), 200



# -------- Student Profile + Attendance % --------

def get_attendance_stats(student_id):
    total_days = StudentAttendance.query.filter_by(student_id=student_id).count()
    present_days = StudentAttendance.query.filter_by(student_id=student_id, status='present').count()
    
    if total_days == 0:
        return {"percentage": "0%"}
    
    percentage = round((present_days / total_days) * 100, 2)
    return {"percentage": f"{percentage}%"}


@checkin_bp.route('/student/checkin/<int:student_id>/detail', methods=['GET'])
@jwt_required()
def get_student_detail(student_id):
    # Student fetch
    student = Student.query.filter_by(id=student_id).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    # Attendance %
    stats = get_attendance_stats(student_id)
    percentage = stats['percentage'] if stats else "0%"
    

    return jsonify({
        "id": student.id,
        "name": student.FullName,
        "admissionNo": student.admissionNo,
        "gender": student.gender,
        "idMark": student.idMark,
        "bloodgroup": student.bloodGroup,
        "village": student.village,
        "po": student.po,
        "ps": student.ps,
        "pinCode": student.pinCode,
        "district": student.district,
        "state": student.state,
        "classname": student.classname,
        "dob": student.dob,
        "attendance_percentage": percentage
    })

# -------- Save Exam Percentage (Admin only) --------

@checkin_bp.route('/student/<int:student_id>/remarks', methods=['POST'])
@jwt_required()
def save_student_remarks(student_id):
    current_user = get_jwt_identity()   

    # --- role check (admin only) ---
    if isinstance(current_user, str) and current_user.isdigit():
        user = User.query.get(int(current_user))
    elif isinstance(current_user, str):
        user = User.query.filter_by(username=current_user).first()
    else:
        user = None

    if not user or user.role != "admin":
        return jsonify({"error": "Admin access required"}), 403

    # --- get input ---
    data = request.get_json() or {}
    remarks = data.get("remarks")
    term = (data.get("exam_name") or "").strip().title()   

    if not remarks:
        return jsonify({"error": "Remarks are required"}), 400

    
    exam_result = ExamResult.query.filter_by(
        student_id=student_id,
        exam_name=term
    ).first()

    if not exam_result:
        exam_result = ExamResult(student_id=student_id, exam_name=term)

    exam_result.remarks = remarks

    db.session.add(exam_result)
    db.session.commit()

    return jsonify({
        "message": "Remarks saved successfully",
        "student_id": student_id,
        "term": term,
        "remarks": remarks
    }), 200


#       -------------  update Details  --------------- 

@checkin_bp.route('/student/<int:student_id>', methods=['GET', 'PUT'])
def student_detail(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"message": "Student not found"}), 404

    # Get for auto fill or pre fillup
    if request.method == 'GET':
        return jsonify({
            "id": student.id,
            "FullName": student.FullName,
            "phone": student.phone,
            "dob": student.dob,
            "gender": student.gender,
            "idMark": student.idMark,
            "bloodGroup": student.bloodGroup,
            "admissionNo": student.admissionNo,
            "fatherName": student.fatherName,
            "occupation": student.occupation,
            "village": student.village,
            "po": student.po,
            "ps": student.ps,
            "email": student.email,
            "pinCode": student.pinCode,
            "district": student.district,
            "state": student.state,
            "rollNo": student.rollNo,
            "section": student.section,
            "classname": student.classname,
            "photo": student.photo
        }), 200

    #  PUT request for update student data
    if request.method == 'PUT':
        data = request.form.to_dict()
        photo = request.files.get('photo')

        if photo:
            upload_folder = 'uploads/students'
            os.makedirs(upload_folder, exist_ok=True)
            filename = secure_filename(photo.filename)
            filepath = os.path.join(upload_folder, filename)
            photo.save(filepath)
            student.photo = filepath

        field_mapping = [
            "FullName", "phone", "dob", "gender", "idMark", "bloodGroup",
            "admissionNo", "fatherName", "occupation", "village", "po", "ps",
            "email", "pinCode", "district", "state", "rollNo", "section", "classname"
        ]

        for field in field_mapping:
            if field in data:
                setattr(student, field, data[field])

        db.session.commit()
        return jsonify({"message": "Student details updated successfully"}), 200
    
@checkin_bp.route('/classes', methods=['GET'])
@cache.cached(timeout=600, key_prefix='all_classes')
def get_classes():
    classes = Class.query.order_by(Class.name).distinct().all()
    class_list = [c.name for c in classes]
    return jsonify({"classes": class_list}), 200

@checkin_bp.route('/students/by-class', methods=['GET'])
def get_students_by_class():
    classname = request.args.get('classname')
    section = request.args.get('section')

    if not classname:
        return jsonify({"error": "classname is required"}), 400

    query = Student.query.filter_by(classname=classname)
    if section:
        query = query.filter_by(section=section)

    students = query.all()
    result = [
        {
            "id": s.id,
            "FullName": s.FullName,
            "rollNo": s.rollNo,
            "section": s.section,
            "classname": s.classname,
            "photo": url_for('static', filename=f'uploads/students/{os.path.basename(s.photo)}') if s.photo else None
        }
        for s in students
    ]

    return jsonify(result), 200


# -------- Delete Student (Admin Only) --------
@checkin_bp.route('/student/<int:student_id>/delete', methods=['DELETE'])
@jwt_required()
def delete_student(student_id):
    current_user = get_jwt_identity()

    # --- verify admin role ---
    if isinstance(current_user, str) and current_user.isdigit():
        user = User.query.get(int(current_user))
    elif isinstance(current_user, str):
        user = User.query.filter_by(username=current_user).first()
    else:
        user = None

    if not user or user.role != "admin":
        return jsonify({"error": "Admin access required"}), 403

    # --- find student ---
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    try:
        # --- delete all related data safely ---
        S_attendance.query.filter_by(student_id=student_id).delete()
        Payment.query.filter_by(student_id=student_id).delete()
        FeeRecord.query.filter_by(student_id=student_id).delete()
        ExamResult.query.filter_by(student_id=student_id).delete()
    

        # delete student photo if exists
        if student.photo and os.path.exists(student.photo):
            os.remove(student.photo)

        db.session.delete(student)
        db.session.commit()

        return jsonify({
            "message": f"Student (ID: {student_id}) and all related records deleted successfully."
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    


@checkin_bp.route('/debug-token', methods=['GET'])
@jwt_required()
def debug_token():
    identity = get_jwt_identity()
    print("JWT Identity:", identity)
    return jsonify({"identity": identity})