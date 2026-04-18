from flask import Blueprint, jsonify, render_template, request
from sqlalchemy.exc import SQLAlchemyError
from app.models.user_model import User
from app.extensions import bcrypt, db
from app.auth.auth import _do_login

# ------------------ USER LOGIN ------------------

user_auth_bp = Blueprint("user_auth", __name__)


@user_auth_bp.route("/login2", methods=["POST"], endpoint="user_login_api")
def user_login():
   
    return _do_login(
        allowed_roles=["student", "teacher", "staff"],
        use_dob_as_password=True
    )