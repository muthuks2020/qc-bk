from flask import Blueprint, request, g
from app.extensions import db
from app.models.masters import Department, User
from app.models.audit import AuditLog
from app.schemas.masters_schema import DepartmentSchema
from app.middleware.auth_middleware import token_required, role_required
from app.utils.responses import success_response, error_response, validation_error
from marshmallow import ValidationError

department_bp = Blueprint('departments', __name__)
dept_schema = DepartmentSchema()


def _serialize_dept(d):
    manager = None
    if d.manager_id:
        u = User.query.get(d.manager_id)
        if u:
            manager = {'id': u.id, 'user_name': u.user_name}
    return {
        'id': d.id, 'department_code': d.department_code,
        'department_name': d.department_name,
        'pass_source_location': d.pass_source_location,
        'pass_source_location_odoo_id': d.pass_source_location_odoo_id,
        'pass_destination_location': d.pass_destination_location,
        'pass_destination_location_odoo_id': d.pass_destination_location_odoo_id,
        'fail_source_location': d.fail_source_location,
        'fail_source_location_odoo_id': d.fail_source_location_odoo_id,
        'fail_destination_location': d.fail_destination_location,
        'fail_destination_location_odoo_id': d.fail_destination_location_odoo_id,
        'manager_id': d.manager_id, 'manager': manager,
        'description': d.description, 'is_active': d.is_active,
        'users_count': d.users.filter_by(is_active=True).count(),
        'created_at': d.created_at.isoformat() if d.created_at else None,
        'updated_at': d.updated_at.isoformat() if d.updated_at else None,
    }


@department_bp.route('/departments', methods=['GET'])
@token_required
def get_departments():
    query = Department.query
    if request.args.get('is_active', '').lower() == 'true':
        query = query.filter_by(is_active=True)
    search = request.args.get('search')
    if search:
        query = query.filter(db.or_(
            Department.department_code.ilike(f'%{search}%'),
            Department.department_name.ilike(f'%{search}%')))
    return success_response(data=[_serialize_dept(d) for d in query.order_by(Department.department_name).all()])


@department_bp.route('/departments', methods=['POST'])
@token_required
@role_required('admin')
def create_department():
    try:
        data = dept_schema.load(request.get_json())
    except ValidationError as e:
        return validation_error(e.messages)
    if Department.query.filter(db.func.lower(Department.department_code) == data['department_code'].lower()).first():
        return error_response('Department code already exists', 409)
    if data.get('manager_id'):
        if not User.query.filter_by(id=data['manager_id'], is_active=True).first():
            return validation_error({'manager_id': 'Invalid or inactive user'})
    dept = Department(**{k: v for k, v in data.items() if hasattr(Department, k)})
    db.session.add(dept)
    db.session.flush()
    AuditLog.log('qc_departments', dept.id, 'INSERT', new_data=data)
    db.session.commit()
    return success_response(data=_serialize_dept(dept), message='Department created', status_code=201)


@department_bp.route('/departments/<int:id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_department(id):
    dept = Department.query.get_or_404(id, description='Department not found')
    try:
        data = dept_schema.load(request.get_json(), partial=True)
    except ValidationError as e:
        return validation_error(e.messages)
    if 'department_code' in data and data['department_code'].lower() != dept.department_code.lower():
        if Department.query.filter(db.func.lower(Department.department_code) == data['department_code'].lower(), Department.id != id).first():
            return error_response('Department code already exists', 409)
    if data.get('manager_id') and not User.query.filter_by(id=data['manager_id'], is_active=True).first():
        return validation_error({'manager_id': 'Invalid or inactive user'})
    for k, v in data.items():
        if hasattr(dept, k):
            setattr(dept, k, v)
    AuditLog.log('qc_departments', dept.id, 'UPDATE', new_data=data)
    db.session.commit()
    return success_response(data=_serialize_dept(dept), message='Department updated')


@department_bp.route('/departments/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_department(id):
    dept = Department.query.get_or_404(id, description='Department not found')
    cnt = dept.users.filter_by(is_active=True).count()
    if cnt > 0:
        return error_response(f'Cannot deactivate: {cnt} active users assigned', 409)
    dept.is_active = False
    AuditLog.log('qc_departments', dept.id, 'DELETE')
    db.session.commit()
    return success_response(message='Department deactivated')
