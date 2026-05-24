from flask import Blueprint, request, jsonify, url_for
from flask_jwt_extended import jwt_required, get_jwt
from app.models.fees_model import FeeRecord
from app.models.student_model import Student
from app import db
import os
from datetime import datetime
from app.utils.helpers import format_classname

# =====================================================
# STRIPE
# =====================================================

import stripe

from stripe_config import (
    STRIPE_SECRET_KEY,
    STRIPE_PUBLISHABLE_KEY
)

stripe.api_key = STRIPE_SECRET_KEY

# =====================================================
# RAZORPAY
# =====================================================

import razorpay

from razorpay_config import (
    RAZORPAY_KEY_ID,
    RAZORPAY_SECRET
)

razorpay_client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET)
)

# =====================================================
# BLUEPRINT
# =====================================================

payment_bp = Blueprint(
    'payment_bp',
    __name__,
    url_prefix='/api/student'
)

# =====================================================
# GET FEE STRUCTURE
# =====================================================

@payment_bp.route('/payment/fee-structure/<month>', methods=['GET'])
@jwt_required()
def get_fee_structure(month):

    claims = get_jwt()

    student_id = claims.get("student_id")

    print("JWT Claims:", claims)
    print("Looking for:", student_id, month)

    student = Student.query.filter_by(
        id=student_id
    ).first()

    photo_url = None

    if student and getattr(student, "photo", None):

        photo_url = url_for(
            'static',
            filename=f'uploads/students/{student.photo}',
            _external=True
        )

    if not student:

        student_data = {
            "FullName": "Tausif Kamal",
            "email": "tausifkamal@example.com",
            "classname": "Class 1",
            "phone": "8906428140"
        }

    else:

        student_data = {

            "FullName": student.FullName,

            "photo": photo_url,

            "rollNo": student.rollNo,

            "classname": format_classname(
                student.classname
            ),

            "phone": student.phone
        }

    fee_record = FeeRecord.query.filter_by(
        student_id=student_id,
        month=month
    ).first()

    # =====================================================
    # DUMMY FEE
    # =====================================================

    if not fee_record:

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
        }

    total_amount = (

        fee_data["school_fee"] +

        fee_data["sports_fee"] +

        fee_data["other_fee"]
    )

    def format_key(key):

        return key.replace("_", " ").title()

    response = {

        "student": student_data,

        "fee_structure": {

            format_key("school_fee"): fee_data["school_fee"],

            format_key("sports_fee"): fee_data["sports_fee"],

            format_key("other_fee"): fee_data["other_fee"],

            "Total": total_amount
        }
    }

    return jsonify(response)

# =====================================================
# INITIATE PAYMENT
# =====================================================

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
    # CALCULATE TOTAL
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

    try:

        # =====================================================
        # UAE = STRIPE
        # =====================================================

        if payment_for == "uae":

            currency = "aed"

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

            payment_gateway = "stripe"

            gateway_order_id = session.id

            checkout_url = session.url

        # =====================================================
        # INDIA = RAZORPAY
        # =====================================================

        else:

            currency = "inr"

            razorpay_order = razorpay_client.order.create({

                "amount": int(total_amount * 100),

                "currency": "INR",

                "payment_capture": 1
            })

            payment_gateway = "razorpay"

            gateway_order_id = razorpay_order["id"]

            checkout_url = None

        # =====================================================
        # CREATE / UPDATE FEE RECORD
        # =====================================================

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

                stripe_session_id=gateway_order_id,

                payment_gateway=payment_gateway,

                payment_for=payment_for,

                currency=currency
            )

            db.session.add(fee_record)

        else:

            fee_record.total_amount = total_amount

            fee_record.payment_gateway = payment_gateway

            fee_record.payment_for = payment_for

            fee_record.currency = currency

            fee_record.stripe_session_id = gateway_order_id

            if screenshot_path:

                fee_record.payment_screenshot = screenshot_path

            fee_record.approval_status = "Pending"

            fee_record.payment_status = "Pending"

        db.session.commit()

        return jsonify({

            "success": True,

            "payment_gateway": payment_gateway,

            "checkout_url": checkout_url,

            "session_id": gateway_order_id,

            "amount": total_amount,

            "currency": currency,

            "screenshot": screenshot_path,

            "publishable_key": STRIPE_PUBLISHABLE_KEY,

            "razorpay_key": RAZORPAY_KEY_ID
        })

    except Exception as e:

        db.session.rollback()

        print("PAYMENT ERROR:", e)

        return jsonify({
            "error": str(e)
        }), 500

# =====================================================
# UPDATE PAYMENT STATUS
# =====================================================

@payment_bp.route('/payment-status', methods=['POST'])
@jwt_required()
def update_payment_status():

    data = request.json

    order_id = data.get('order_id')

    payment_result = data.get('status')

    record = FeeRecord.query.filter_by(
        stripe_session_id=order_id
    ).first()

    if not record:

        return jsonify({
            'message': 'Order not found'
        }), 404

    if payment_result == "Success":

        record.payment_status = "Paid"

        record.payment_date = datetime.now()

    else:

        record.payment_status = "Due"

    db.session.commit()

    return jsonify({
        'message': 'Payment status updated successfully'
    })