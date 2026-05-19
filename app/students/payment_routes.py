from flask import Blueprint, request, jsonify, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.fees_model import FeeRecord
from app.models.student_model import Student
from app import db
import os
from datetime import datetime
from app.utils.helpers import format_classname

import stripe

from stripe_config import (
    STRIPE_SECRET_KEY,
    STRIPE_PUBLISHABLE_KEY
)

stripe.api_key = STRIPE_SECRET_KEY


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

    claims = get_jwt()

    student_id = claims.get("student_id")

    if not student_id:
        return jsonify({
            "error": "Student ID missing"
        }), 400

    try:
        student_id_int = int(student_id)

    except (TypeError, ValueError):

        return jsonify({
            "error": "Invalid student ID"
        }), 400

    student = Student.query.get(student_id_int)

    if not student:
        return jsonify({
            "error": "Student not found"
        }), 404

    # =====================================================
    # FORM DATA
    # =====================================================

    month = request.form.get("month")

    payment_for = request.form.get(
        "payment_for",
        "india"
    )

    screenshot = request.files.get("screenshot")

    if not month:
        return jsonify({
            "error": "Month is required"
        }), 400

    # =====================================================
    # FIND FEE RECORD
    # =====================================================

    fee_record = FeeRecord.query.filter_by(
        student_id=student_id_int,
        month=month
    ).first()

    # =====================================================
    # CALCULATE FEES
    # =====================================================

    if fee_record:

        total_amount = (
            fee_record.school_fee +
            fee_record.sports_fee +
            fee_record.other_fee
        )

    else:

        total_amount = 1700

    # =====================================================
    # SAVE SCREENSHOT
    # =====================================================

    screenshot_path = None

    if screenshot:

        upload_folder = "app/static/uploads/payments"

        os.makedirs(upload_folder, exist_ok=True)

        filename = (
            f"{student_id_int}_{month}_{screenshot.filename}"
        )

        filepath = os.path.join(
            upload_folder,
            filename
        )

        screenshot.save(filepath)

        screenshot_path = (
            f"/static/uploads/payments/{filename}"
        )

    # =====================================================
    # CURRENCY
    # =====================================================

    currency = (
        "aed"
        if payment_for == "uae"
        else "inr"
    )

    try:

        # =================================================
        # STRIPE SESSION
        # =================================================

        session = stripe.checkout.Session.create(

            payment_method_types=['card'],

            line_items=[{

                'price_data': {

                    'currency': currency,

                    'product_data': {
                        'name': f'School Fee - {month}'
                    },

                    'unit_amount': int(
                        total_amount * 100
                    ),
                },

                'quantity': 1,
            }],

            mode='payment',

            success_url='http://localhost:3000/payment-success',

            cancel_url='http://localhost:3000/payment-cancel',

            metadata={

                "student_id": student_id_int,

                "month": month,

                "payment_for": payment_for
            }
        )

        # =================================================
        # CREATE RECORD
        # =================================================

        if not fee_record:

            fee_record = FeeRecord(

                student_id=student_id_int,

                month=month,

                school_fee=1200,

                sports_fee=300,

                other_fee=200,

                total_amount=total_amount,

                payment_status="Pending",

                approval_status="Pending",

                payment_screenshot=screenshot_path,

                stripe_session_id=session.id,

                payment_gateway="stripe",

                payment_for=payment_for,

                currency=currency
            )

            db.session.add(fee_record)

        else:

            fee_record.total_amount = total_amount

            fee_record.payment_gateway = "stripe"

            fee_record.payment_for = payment_for

            fee_record.currency = currency

            fee_record.stripe_session_id = session.id

            # ✅ UPDATE SCREENSHOT
            if screenshot_path:
                fee_record.payment_screenshot = screenshot_path

            # ✅ RESET APPROVAL
            fee_record.approval_status = "Pending"

            fee_record.payment_status = "Pending"

        db.session.commit()

        return jsonify({

            "success": True,

            "checkout_url": session.url,

            "session_id": session.id,

            "amount": total_amount,

            "currency": currency,

            "screenshot": screenshot_path,

            "publishable_key": STRIPE_PUBLISHABLE_KEY
        })

    except Exception as e:

        db.session.rollback()

        print("STRIPE ERROR:", e)

        return jsonify({
            "error": str(e)
        }), 500



@payment_bp.route('/payment-status', methods=['POST'])
@jwt_required()
def update_payment_status():
    data = request.json

    order_id = data.get('order_id')
    payment_result = data.get('status')  # Success / Failed

    record = FeeRecord.query.filter_by(
    stripe_session_id=order_id
).first()

    if not record:
        return jsonify({'message': 'Order not found'}), 404

    if payment_result == "Success":
        record.payment_status = "Paid"
        record.payment_date = datetime.now()
    else:
        record.payment_status = "Due"

    db.session.commit()

    return jsonify({'message': 'Payment status updated successfully'})


