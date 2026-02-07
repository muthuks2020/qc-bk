from functools import wraps
from flask import request, g, current_app
from app.utils.responses import error_response

def token_required(f):
    """Validate Bearer token and inject user context into Flask g."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Bypass auth if AUTH_ENABLED is false
        if not current_app.config.get('AUTH_ENABLED', True):
            g.current_user = {
                'user_id': request.headers.get('X-User-Id', '1'),
                'user_name': request.headers.get('X-User-Name', 'DevUser'),
                'role': request.headers.get('X-User-Role', 'admin'),
                'email': request.headers.get('X-User-Email', 'dev@appasamy.com'),
            }
            return f(*args, **kwargs)

        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''

        if not token or token != current_app.config.get('API_SECRET_TOKEN'):
            return error_response('Unauthorized - Invalid or missing token', 401)

        user_id = request.headers.get('X-User-Id')
        if not user_id:
            return error_response('Unauthorized - X-User-Id header required', 401)

        g.current_user = {
            'user_id': user_id,
            'user_name': request.headers.get('X-User-Name', 'Unknown'),
            'role': request.headers.get('X-User-Role', 'maker'),
            'email': request.headers.get('X-User-Email', ''),
        }
        return f(*args, **kwargs)
    return decorated

def role_required(*allowed_roles):
    """Check if current user has one of the allowed roles."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_role = g.current_user.get('role', '')
            if user_role not in allowed_roles:
                return error_response(
                    f'Forbidden - Role "{user_role}" does not have access. Required: {", ".join(allowed_roles)}',
                    403
                )
            return f(*args, **kwargs)
        return decorated
    return decorator
