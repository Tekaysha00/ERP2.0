from flask import Blueprint, request, jsonify, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.fees_model import FeeRecord
from app.models.student_model import Student
from razorpay_config import razorpay_client
from app import db
from datetime import datetime
from app.utils.helpers import format_classname


payment_bp = Blueprint('payment_bp', __name__, url_prefix='/api/student')


@payment_bp.route('/payment/fee-structure/<month>', methods=['GET'])
@jwt_required()
def get_fee_structure(month):
    # Get current student ID from JWT
    claims = get_jwt()
    student_id = claims.get("student_id")
    print("JWT Claims:", claims)
    print("Looking for:", student_id, month)

    student = Student.query.filter_by(id=student_id).first()

    photo_url = None
    if student and getattr(student, "photo", None):
        photo_url = url_for('static', filename=f'uploads/students/{student.photo}', _external=True)

       

    if not student:
        # Dummy student if no record found
        student_data = {
            "FullName": "Tausif Kamal",
            "email": "tausifkamal@example.com",
            ("classname"): "Class 1",
            "phone": "8906428140"
        }
    else:
        student_data = {
            "FullName": student.FullName,
            "photo": photo_url,
             "rollNo": student.rollNo,
            "classname": format_classname(student.classname),
            "phone": student.phone
        }

    fee_record = FeeRecord.query.filter_by(student_id=student_id, month=month).first()

    # ✅ Use dummy fee data if no fee record found
    if not fee_record:
        print(f"No fee record found for {month}, using dummy data")
        fee_data = {
            "school_fee": 1200,
            "sports_fee": 300,
            "other_fee": 200,
        }
    else:
        fee_data = {
            "school_fee": fee_record.school_fee,
            "sports_fee": fee_record.sports_fee,
            "other_fee": fee_record.other_fee,
            # "total_amount": fee_record.total_amount
        }

    total_amount = (
        fee_data["school_fee"] + fee_data["sports_fee"] + fee_data["other_fee"]
    )

    def format_key(key):
        return key.replace("_", " ").title()
    
    response = {
        "student": student_data,
        "fee_structure": {
            format_key("school_fee"): fee_data["school_fee"],   # School Fee
            format_key("sports_fee"): fee_data["sports_fee"],   # Sports Fee
            format_key("other_fee"): fee_data["other_fee"],     # Other Fee
            "Total": total_amount
        }
    }
    print(response)

    return jsonify(response)


@payment_bp.route('/pay-now/initiate-payment', methods=['POST'])
@jwt_required()
def initiate_payment():
    # ✅ Same as get_fee_structure
    claims = get_jwt()
    student_id = claims.get("student_id")
    print("INITIATE PAYMENT -> student_id from JWT claims:", student_id)

    if not student_id:
        return jsonify({"error": "Student ID missing in token"}), 400

    try:
        student_id_int = int(student_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid student ID"}), 400

    # ✅ Make sure student actually exists
    student = Student.query.get(student_id_int)
    if not student:
        return jsonify({"error": f"Student with ID {student_id_int} not found"}), 404

    data = request.json
    month = data["month"]
    upi_id = data["upi_id"]

    # ✅ Use int student_id everywhere
    fee_record = FeeRecord.query.filter_by(
        student_id=student_id_int, month=month
    ).first()

    if fee_record:
        total_amount = (
            fee_record.school_fee + fee_record.sports_fee + fee_record.other_fee
        )
    else:
        total_amount = 1700  # dummy paisa

    razorpay_order = razorpay_client.order.create({
        "amount": total_amount * 100,  # paise
        "currency": "INR",
        "payment_capture": 1
    })

    try:
        if not fee_record:
            fee_record = FeeRecord(
                student_id=student_id_int,
                month=month,
                school_fee=1200,
                sports_fee=300,
                other_fee=200,
                total_amount=total_amount,
                upi_id=upi_id,
                razorpay_order_id=razorpay_order["id"],
                payment_status="Pending",
            )
            db.session.add(fee_record)
        else:
            fee_record.razorpay_order_id = razorpay_order["id"]
            fee_record.upi_id = upi_id
            fee_record.total_amount = total_amount

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("DB ERROR IN initiate_payment:", e)
        return jsonify({"error": "Database error while creating fee record"}), 500

    return jsonify({
        "order_id": razorpay_order["id"],
        "amount": total_amount,
        "currency": "INR",
        "upi_id": upi_id,
        "razorpay_key": "rzp_test_20tkfyOZteuJyu"
    })



@payment_bp.route('/payment-status', methods=['POST'])
@jwt_required()
def update_payment_status():
    data = request.json

    order_id = data.get('order_id')
    payment_result = data.get('status')  # Success / Failed

    record = FeeRecord.query.filter_by(razorpay_order_id=order_id).first()

    if not record:
        return jsonify({'message': 'Order not found'}), 404

    if payment_result == "Success":
        record.payment_status = "Paid"
        record.payment_date = datetime.now()
    else:
        record.payment_status = "Due"

    db.session.commit()

    return jsonify({'message': 'Payment status updated successfully'})


