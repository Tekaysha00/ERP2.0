import os
import logging
from datetime import timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from app.extensions import cache


from dotenv import load_dotenv
load_dotenv()  # loads .env into os.environ (must be called before Config reads env)

from .extensions import db, bcrypt, jwt, cors, migrate
from .Admin.checkin_routes import checkin_bp
from .Admin.attendance_routes import attendance_bp
from app.auth.admin_auth import create_default_admin
from .Admin.main_routes import class_bp
from config import Config
from app.auth.admin_auth import admin_auth_bp
from .auth.user_auth import user_auth_bp

from app.students.register_routes import student_register_bp
from app.students.dashboard import student_dashboard_bp
from .Admin.students_routes import student_bp_admin
from app.Admin.teacher_checkin_routes import teacher_checkin_bp
from app.students.student_routes import student_bp_view
from app.Teachers.routes import teacher_bp_view
from app.Admin.academic_routes import academic_bp
from app.Teachers.Teachers_dashboard import teacher_dashboard_bp
from app.students.routes import students_bp
from app.students.payment_routes import payment_bp
from app.Admin.admin_dashboard import dashboard_bp

# Ensure logging prints to console for CLI visibility
logging.basicConfig(level=logging.DEBUG)

def create_app():
    
    from app.models import User, Student, FeeRecord

    app = Flask(__name__, template_folder='templates')

    # Load default config from Config class (which reads os.environ)
    app.config.from_object(Config)

    # ================= REDIS CACHE CONFIG =================
    app.config.update({
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_HOST": "localhost",
    "CACHE_REDIS_PORT": 6379,
    "CACHE_REDIS_DB": 0,
    "CACHE_DEFAULT_TIMEOUT": 300
})
# =====================================================


    
    env_db = os.environ.get('DATABASE_URL')  # <- read DATABASE_URL (not SQLALCHEMY_DATABASE_URI)
    if env_db:
        # set/override config from environment (only if provided)
        app.config['SQLALCHEMY_DATABASE_URI'] = env_db
        app.logger.debug("Set app.config['SQLALCHEMY_DATABASE_URI'] from ENV (DATABASE_URL).")
    else:
        app.logger.debug("ENV DATABASE_URL not set; using config object or fallback.")

    # Show current DB URI (masked for safety in logs if needed)
    db_uri_preview = app.config.get('SQLALCHEMY_DATABASE_URI')
    if db_uri_preview:
        # mask password portion for safety when logging
        try:
            # crude mask: keep scheme+host, hide password if present
            if "@" in db_uri_preview and "://" in db_uri_preview:
                scheme, rest = db_uri_preview.split("://", 1)
                creds_host = rest.split("@", 1)
                if len(creds_host) == 2:
                    creds, hostpart = creds_host
                    if ":" in creds:
                        user, pw = creds.split(":", 1)
                        masked = f"{scheme}://{user}:***@{hostpart}"
                    else:
                        masked = f"{scheme}://***@{hostpart}"
                else:
                    masked = db_uri_preview
            else:
                masked = db_uri_preview
        except Exception:
            masked = "REDACTED"
    else:
        masked = None

    app.logger.debug("app.config SQLALCHEMY_DATABASE_URI (preview) = %s", masked)

    # JWT config
    app.config["JWT_SECRET_KEY"] = "replace-with-strong-secret"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=8)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
    app.config["JWT_DECODE_LEEWAY"] = 30

    

    @app.before_request
    def debug_request():
       
        app.logger.debug("PATH: %s", request.path)
      

    # CORS
    CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}}, supports_credentials=True)

    # Initialize extensions (db.init_app after config)
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    cache.init_app(app)
    cors.init_app(app, supports_credentials=True)


    # Register blueprints
    app.register_blueprint(admin_auth_bp)
    app.register_blueprint(checkin_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(user_auth_bp, url_prefix="/user_auth")
    app.register_blueprint(class_bp)
    app.register_blueprint(student_register_bp)
    app.register_blueprint(student_dashboard_bp)
    app.register_blueprint(student_bp_admin)
    app.register_blueprint(teacher_checkin_bp)
    app.register_blueprint(teacher_bp_view)
    app.register_blueprint(student_bp_view)
    app.register_blueprint(academic_bp)
    app.register_blueprint(teacher_dashboard_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(dashboard_bp)

    app.logger.debug("Blueprints registered.")

    # Create DB tables & default admin (only when running app normally)
    with app.app_context():
        db.create_all()
        try:
            create_default_admin()
        except Exception as e:
            app.logger.debug("create_default_admin() raised: %s", str(e))

    @app.route('/')
    def home():
        return jsonify({"message": "Backend is running!"})

    return app
