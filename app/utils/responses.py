from flask import jsonify


def success_response(data=None, message='Success', status_code=200, meta=None):
    """Standard success response."""
    response = {
        'success': True,
        'message': message,
    }
    if data is not None:
        response['data'] = data
    if meta is not None:
        response['meta'] = meta
    return jsonify(response), status_code


def error_response(message='An error occurred', status_code=400, errors=None):
    """Standard error response."""
    return jsonify({
        'success': False,
        'message': message,
        'errors': errors or [],
    }), status_code


def validation_error(errors, message='Validation failed'):
    """Validation error with field-level errors."""
    formatted = []
    if isinstance(errors, dict):
        for field, msgs in errors.items():
            if isinstance(msgs, list):
                for msg in msgs:
                    formatted.append({'field': field, 'message': msg})
            else:
                formatted.append({'field': field, 'message': str(msgs)})
    elif isinstance(errors, list):
        formatted = errors
    return jsonify({
        'success': False,
        'message': message,
        'errors': formatted,
    }), 400
