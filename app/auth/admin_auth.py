from flask import Blueprint, jsonify, render_template, request, redirect, url_for
from sqlalchemy.exc import SQLAlchemyError
from ..models.user_model import User
from app.extensions import db, bcrypt
from app.auth.auth import _do_login

# Initialize blueprint with prefix
admin_auth_bp = Blueprint("admin_auth_bp", __name__, url_prefix="/admin_auth")

# Web Login (GET + POST)
@admin_auth_bp.route("/login", methods=["GET", "POST"])
def admin_login_web():
    if request.method == "GET":
        return render_template("login.html")
    return _do_login(allowed_roles=["admin"], use_dob_as_password=False)

@admin_auth_bp.route("/registerstudent", methods=["GET"])
def register_student():
    if not request.cookies.get('access_token'):
        return redirect(url_for("admin_auth_bp.admin_login_web"))  # Must match blueprint name
    return render_template("register_student.html")

# API Login (POST only)
@admin_auth_bp.route("/login2", methods=["POST"])
def admin_login_api():
    """Handle admin API login"""
    return _do_login(allowed_roles=["admin"], use_dob_as_password=False)


def create_default_admin():
    """
    Create a default admin if one doesn't exist.
    Phone: 1234567890 | Password: adminpass
    """
    phone = '1234567890'
    username = 'admin'
    default_password = 'adminpass'

    try:
        # Debug: Print hashed password for verification
        hashed_pw = bcrypt.generate_password_hash(default_password).decode('utf-8')
        print(f" [DEBUG] Generated admin hash: {hashed_pw}")  

        # Check if admin already exists
        existing_admin = User.query.filter_by(phone=phone, role='admin').first()
        if existing_admin:
            print(f" [DEBUG] Admin exists → Phone: {phone} | Hash: {existing_admin.password}")  
            return

        # Create new admin
        admin = User(
            username=username,
            phone=phone,
            mobile=phone,
            role='admin',
            password=hashed_pw
        )
        db.session.add(admin)
        db.session.commit()

        print(f" [DEBUG] Admin created → Phone: {phone} | Pass: {default_password} | Hash: {hashed_pw}")  

    except SQLAlchemyError as e: 
        db.session.rollback()
        print(f" [DEBUG] Admin creation failed: {str(e)}")  