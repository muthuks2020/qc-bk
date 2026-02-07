import json
from flask import Blueprint, request, g
from app.extensions import db
from app.models.masters import SystemConfig
from app.models.audit import AuditLog
from app.middleware.auth_middleware import token_required, role_required
from app.utils.responses import success_response, error_response

system_config_bp = Blueprint('system_config', __name__)


@system_config_bp.route('/system-config', methods=['GET'])
@token_required
@role_required('admin', 'checker')
def get_system_config():
    query = SystemConfig.query
    modules = request.args.getlist('module')
    if modules:
        query = query.filter(SystemConfig.module.in_(modules))
    items = query.order_by(SystemConfig.module, SystemConfig.config_key).all()
    return success_response(data=[{
        'id': c.id, 'config_key': c.config_key, 'config_value': c.config_value,
        'config_type': c.config_type, 'module': c.module, 'description': c.description,
        'is_editable': c.is_editable,
        'updated_at': c.updated_at.isoformat() if c.updated_at else None,
        'updated_by': c.updated_by,
    } for c in items])


@system_config_bp.route('/system-config/<config_key>', methods=['PUT'])
@token_required
@role_required('admin')
def update_system_config(config_key):
    cfg = SystemConfig.query.filter_by(config_key=config_key).first()
    if not cfg:
        return error_response(f'Config key "{config_key}" not found', 404)
    if not cfg.is_editable:
        return error_response('This configuration is not editable', 403)
    data = request.get_json()
    new_value = data.get('config_value')
    new_type = data.get('config_type', cfg.config_type)
    if new_value is None:
        return error_response('config_value is required', 400)
    # Validate by type
    if new_type == 'number':
        try:
            float(new_value)
        except (ValueError, TypeError):
            return error_response('config_value must be a valid number for type "number"', 400)
    elif new_type == 'boolean':
        if new_value.lower() not in ('true', 'false'):
            return error_response('config_value must be "true" or "false" for type "boolean"', 400)
    elif new_type == 'json':
        try:
            json.loads(new_value)
        except (json.JSONDecodeError, TypeError):
            return error_response('config_value must be valid JSON for type "json"', 400)

    old_value = cfg.config_value
    cfg.config_value = str(new_value)
    cfg.config_type = new_type
    cfg.updated_by = g.current_user.get('user_name')
    AuditLog.log('qc_system_config', cfg.id, 'UPDATE',
                 old_data={'config_value': old_value},
                 new_data={'config_value': new_value})
    db.session.commit()
    return success_response(message=f'Config "{config_key}" updated')
