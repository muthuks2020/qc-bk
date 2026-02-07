import json
from flask import g, request
from app.extensions import db


def log_audit(table_name, record_id, action, old_data=None, new_data=None):
    try:
        user = getattr(g, 'current_user', {})
        changed_fields = []
        if old_data and new_data and isinstance(old_data, dict) and isinstance(new_data, dict):
            for key in set(list(old_data.keys()) + list(new_data.keys())):
                if str(old_data.get(key)) != str(new_data.get(key)):
                    changed_fields.append(key)
        sql = db.text("""
            INSERT INTO qc_audit_log
                (table_name, record_id, action, old_data, new_data, changed_fields, user_id, user_name, user_role, user_ip)
            VALUES (:t, :r, :a, :od, :nd, :cf, :uid, :un, :ur, :ip)
        """)
        db.session.execute(sql, {
            't': table_name, 'r': record_id, 'a': action,
            'od': json.dumps(old_data, default=str) if old_data else None,
            'nd': json.dumps(new_data, default=str) if new_data else None,
            'cf': changed_fields or None,
            'uid': user.get('user_id'), 'un': user.get('user_name'),
            'ur': user.get('role'), 'ip': request.remote_addr if request else None,
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'Audit log failed: {e}')


def log_component_history(component_id, action, field_name=None, old_value=None, new_value=None, reason=None):
    try:
        user = getattr(g, 'current_user', {})
        sql = db.text("""
            INSERT INTO qc_component_history (component_id, action, field_name, old_value, new_value, change_reason, changed_by)
            VALUES (:cid, :a, :fn, :ov, :nv, :r, :cb)
        """)
        db.session.execute(sql, {
            'cid': component_id, 'a': action, 'fn': field_name,
            'ov': str(old_value) if old_value is not None else None,
            'nv': str(new_value) if new_value is not None else None,
            'r': reason, 'cb': user.get('user_name'),
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'Component history log failed: {e}')
