from app.models.fees_model import FeeRecord
from app.extensions import db

def ensure_fee_records_for_student(student_id):
    months = [
        "January","February","March","April","May","June",
        "July","August","September","October","November","December"
    ]

    for month in months:
        existing = FeeRecord.query.filter_by(
            student_id=student_id,
            month=month
        ).first()

        if not existing:
            fee = FeeRecord(
                student_id=student_id,
                month=month,
                school_fee=1200,
                sports_fee=300,
                other_fee=200,
                total_amount=1700,
                payment_status="Due"
            )
            db.session.add(fee)

    print(f"✅ Fee created for student {student_id}")