import traceback
from flask import jsonify, current_app
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError


def register_error_handlers(app):

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            'success': False,
            'message': str(e.description) if hasattr(e, 'description') else 'Bad request',
            'errors': [],
        }), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({
            'success': False,
            'message': 'Unauthorized',
            'errors': [],
        }), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({
            'success': False,
            'message': 'Forbidden',
            'errors': [],
        }), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            'success': False,
            'message': 'Resource not found',
            'errors': [],
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({
            'success': False,
            'message': 'Method not allowed',
            'errors': [],
        }), 405

    @app.errorhandler(409)
    def conflict(e):
        return jsonify({
            'success': False,
            'message': str(e.description) if hasattr(e, 'description') else 'Conflict',
            'errors': [],
        }), 409

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({
            'success': False,
            'message': 'Request entity too large. Max 5MB for JSON, 10MB for file uploads.',
            'errors': [],
        }), 413

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({
            'success': False,
            'message': str(e.description) if hasattr(e, 'description') else 'Unprocessable entity',
            'errors': [],
        }), 422

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({
            'success': False,
            'message': 'Rate limit exceeded. Please slow down.',
            'errors': [],
        }), 429

    @app.errorhandler(ValidationError)
    def marshmallow_validation_error(e):
        errors = []
        for field, messages in e.messages.items():
            if isinstance(messages, list):
                for msg in messages:
                    errors.append({'field': field, 'message': msg})
            else:
                errors.append({'field': field, 'message': str(messages)})
        return jsonify({
            'success': False,
            'message': 'Validation failed',
            'errors': errors,
        }), 400

    @app.errorhandler(IntegrityError)
    def db_integrity_error(e):
        from app.extensions import db
        db.session.rollback()
        current_app.logger.error(f'IntegrityError: {str(e)}')

        msg = 'A database constraint was violated'
        if 'unique' in str(e.orig).lower() or 'duplicate' in str(e.orig).lower():
            msg = 'A record with this value already exists'
        elif 'foreign key' in str(e.orig).lower():
            msg = 'Referenced record does not exist'
        elif 'not-null' in str(e.orig).lower():
            msg = 'A required field is missing'

        if current_app.debug:
            msg = f'{msg}: {str(e.orig)}'

        return jsonify({
            'success': False,
            'message': msg,
            'errors': [],
        }), 409

    @app.errorhandler(OperationalError)
    def db_operational_error(e):
        from app.extensions import db
        db.session.rollback()
        current_app.logger.error(f'OperationalError: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Database connection error' if not current_app.debug else str(e),
            'errors': [],
        }), 500

    @app.errorhandler(500)
    def internal_error(e):
        current_app.logger.error(f'500 Error: {str(e)}\n{traceback.format_exc()}')
        return jsonify({
            'success': False,
            'message': 'Something went wrong' if not current_app.debug else str(e),
            'error_code': 'ERR_500',
            'errors': [],
        }), 500

    @app.errorhandler(Exception)
    def unhandled_exception(e):
        from app.extensions import db
        db.session.rollback()
        current_app.logger.error(f'Unhandled Exception: {str(e)}\n{traceback.format_exc()}')
        return jsonify({
            'success': False,
            'message': 'Something went wrong' if not current_app.debug else f'{type(e).__name__}: {str(e)}',
            'error_code': 'ERR_500',
            'errors': [],
        }), 500
