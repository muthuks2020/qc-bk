import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify
from dotenv import load_dotenv

from app.config import config
from app.extensions import db, ma, cors, limiter


def create_app(config_name=None):
    load_dotenv()

    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))

    # Initialize extensions
    db.init_app(app)
    ma.init_app(app)
    cors.init_app(app, origins=app.config.get('CORS_ORIGINS', ['*']),
                  allow_headers=['Content-Type', 'Authorization',
                                 'X-User-Id', 'X-User-Name', 'X-User-Role', 'X-User-Email'],
                  methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    limiter.init_app(app)

    # Setup logging
    _setup_logging(app)

    # Ensure upload/log dirs exist
    os.makedirs(app.config['UPLOAD_DIR'], exist_ok=True)
    os.makedirs(os.path.dirname(app.config.get('LOG_FILE', './logs/app.log')), exist_ok=True)

    # Register error handlers
    from app.middleware.error_handler import register_error_handlers
    register_error_handlers(app)

    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        response.headers['Cache-Control'] = 'no-store'
        return response

    # Health check (no auth)
    @app.route('/api/v1/health', methods=['GET'])
    def health_check():
        db_status = 'connected'
        try:
            db.session.execute(db.text('SELECT 1'))
        except Exception:
            db_status = 'disconnected'
        return jsonify({
            'status': 'ok',
            'database': db_status,
            'version': '1.0.0',
            'environment': config_name,
        })

    # Register blueprints
    _register_blueprints(app)

    return app


def _register_blueprints(app):
    from app.routes.department_routes import department_bp
    from app.routes.masters_routes import masters_bp
    from app.routes.sampling_routes import sampling_bp
    from app.routes.qc_plans_routes import qc_plans_bp
    from app.routes.component_routes import component_bp
    from app.routes.defect_routes import defect_bp
    from app.routes.location_routes import location_bp
    from app.routes.system_config_routes import system_config_bp
    from app.routes.lookup_routes import lookup_bp

    app.register_blueprint(department_bp, url_prefix='/api/v1')
    app.register_blueprint(masters_bp, url_prefix='/api/v1')
    app.register_blueprint(sampling_bp, url_prefix='/api/v1')
    app.register_blueprint(qc_plans_bp, url_prefix='/api/v1')
    app.register_blueprint(component_bp, url_prefix='/api/v1')
    app.register_blueprint(defect_bp, url_prefix='/api/v1')
    app.register_blueprint(location_bp, url_prefix='/api/v1')
    app.register_blueprint(system_config_bp, url_prefix='/api/v1')
    app.register_blueprint(lookup_bp, url_prefix='/api/v1')


def _setup_logging(app):
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'DEBUG').upper(), logging.DEBUG)
    log_file = app.config.get('LOG_FILE', './logs/app.log')

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    handler = RotatingFileHandler(log_file, maxBytes=10_000_000, backupCount=5)
    handler.setLevel(log_level)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    handler.setFormatter(formatter)

    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
