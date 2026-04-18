from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from ..extensions import db, bcrypt
from app.models.user_model import User

# routes.py
#admin_core_bp = Blueprint('admin_core_bp', __name__, url_prefix='/admin-api')
class_bp = Blueprint('class_bp', __name__, url_prefix='/api/classes')



@class_bp.route('/list', methods=['GET'])
def list_classes():
    classes = [
        {"id": 1, "name": "Class 1"},
        {"id": 2, "name": "Class 2"},
        {"id": 3, "name": "Class 3"}
    ]
    return jsonify({"classes": classes})