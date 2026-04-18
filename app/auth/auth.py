from flask import request, jsonify, render_template, redirect, url_for
from flask_bcrypt import check_password_hash
from app.models.student_model import Student
from app.models.teacher_model import Teacher
from flask_jwt_extended import create_access_token
from app.models import User
from datetime import datetime
from app.extensions import bcrypt
from sqlalchemy import or_

def _do_login(allowed_roles=None, use_dob_as_password=False):

    if request.is_json or request.method == 'POST':
        # 1️⃣ Get data from JSON body or form
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = {
                "phone": request.form.get("phone"),
                "username": request.form.get("username"),
                "password": request.form.get("password"),
                "dob": request.form.get("dob")
            }

        print("🔍 [DEBUG] Request data:", data)

        # 2️⃣ Extract identifier (phone or username)
        identifier = (data.get("phone") or data.get("username") or "").strip()
        print(f"📱 [DEBUG] Login attempt → Identifier: '{identifier}'")

        if not identifier:
            msg = "Phone or username is required"
            return (jsonify({"error": msg}), 400) if request.is_json else render_template("login.html", error=msg)

        # 3️⃣ Get the password from request
        password_input = data.get("password")

        # 4️⃣ Find user in DB
        print(f"[DEBUG] Fetching user details from DB")
        user = User.query.filter(or_(User.phone == identifier, User.username == identifier)).first()
        if not user:
            msg = "User not found"
            print(f" [DEBUG] USER NOT FOUND WITH THIS IDENTIFIER : '{identifier}'")
            return (jsonify({"error": msg}), 401) if request.is_json else render_template("login.html", error=msg)

        # 5️⃣ Check if user role is allowed
        if allowed_roles and user.role not in allowed_roles:
            msg = f"Access denied for role {user.role}"
            return (jsonify({"error": msg}), 403) if request.is_json else render_template("login.html", error=msg)

        # 6️⃣ Verify password
        if use_dob_as_password:
            # --- For Students/Teachers/Staff using DOB ---
            dob_value = str(user.dob)
            print("🧾 [DEBUG] Raw DOB from DB →", dob_value)

            if "T" in dob_value:
                dob_value = dob_value.split("T")[0]
            elif " " in dob_value:
                dob_value = dob_value.split(" ")[0]

            try:
                dob_string = datetime.strptime(dob_value, "%Y-%m-%d").strftime("%d%m%Y")
            except ValueError as e:
                print("❌ [DEBUG] DOB format invalid:", e)
                msg = "Invalid DOB format"
                return (jsonify({"error": msg}), 400) if request.is_json else render_template("login.html", error=msg)

            if password_input != dob_string:
                print(f"❌ [DEBUG] DOB mismatch → Expected: {dob_string}, Got: {password_input}")
                msg = "Invalid credentials"
                return (jsonify({"error": msg}), 401) if request.is_json else render_template("login.html", error=msg)

        else:
            # --- For Admin using bcrypt password ---
            if not bcrypt.check_password_hash(user.password, password_input):
                print(f"❌ [DEBUG] Password mismatch for admin → DB Hash: {user.password}")
                msg = "Invalid credentials"
                return (jsonify({"error": msg}), 401) if request.is_json else render_template("login.html", error=msg)

        # 7️⃣ Create JWT on success
        print(f"✅ [DEBUG] Login successful → User: {user.username} | Role: {user.role}")

        # ---------------- TOKEN CREATION ----------------
        token_data = {"token": None, "role": user.role, "user_id": user.id}

        if user.role == "student":
            student = Student.query.filter_by(user_id=user.id).first()
            token = create_access_token(
                identity=str(user.id),
                additional_claims={"role": user.role, "student_id": student.id if student else None}
            )
            token_data.update({"student_id": student.id if student else None})

        elif user.role in ["teacher", "staff"]:
            teacher = Teacher.query.filter_by(user_id=user.id).first()
            token = create_access_token(
                identity=str(user.id),
                additional_claims={"role": user.role, "teacher_id": teacher.id if teacher else None}
            )
            token_data.update({"teacher_id": teacher.id if teacher else None})

        else:  # Admin
            token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
            token_data.update({"name": user.username, "email": "admin@admin.com"})

        token_data["token"] = token

        # ---------------- RETURN RESPONSE ----------------
        if request.is_json:
            return jsonify(token_data), 200
        else:
            response = redirect(url_for("admin_auth_bp.register_student"))
            response.set_cookie("access_token", token, httponly=True, secure=False, samesite="Lax")
            return response
