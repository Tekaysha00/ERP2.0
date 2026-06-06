from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user_model import User
from app.extensions import db
from app.utils.fcm_service import send_notification
from app.models.user_model import User

reminder_bp = Blueprint(
    "reminder_bp",
    __name__,
    url_prefix="/api/notifications"
)

@reminder_bp.route("/save-fcm-token", methods=["POST"])
@jwt_required()
def save_fcm_token():

    user_id = int(get_jwt_identity())

    data = request.get_json()
    fcm_token = data.get("token")

    if not fcm_token:
        return jsonify({"error": "Token required"}), 400

    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    user.fcm_token = fcm_token

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "FCM token saved"
    })



# test reminder 
@reminder_bp.route("/test-notification", methods=["GET"])
def test_notification():

    user = User.query.filter(
        User.fcm_token.isnot(None)
    ).first()

    if not user:
        return jsonify({
            "error": "No FCM token found"
        }), 404

    response = send_notification(
        user.fcm_token,
        "ERP Test",
        "Notification working successfully"
    )

    return jsonify({
        "message_id": response
    })