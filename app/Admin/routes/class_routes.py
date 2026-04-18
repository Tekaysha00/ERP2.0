from flask import Blueprint, jsonify

class_bp = Blueprint('class_bp', __name__, url_prefix='/api/classes')

@class_bp.route('/list', methods=['GET'])
def list_classes():
    classes = [
        {"id": 1, "name": "Class 1"},
        {"id": 2, "name": "Class 2"},
        {"id": 3, "name": "Class 3"}
    ]
    return jsonify({"classes": classes})