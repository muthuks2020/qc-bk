from flask import Blueprint, request
from app.extensions import db
from app.models.masters import Location
from app.models.audit import AuditLog
from app.schemas.masters_schema import LocationSchema
from app.middleware.auth_middleware import token_required, role_required
from app.utils.responses import success_response, error_response, validation_error
from marshmallow import ValidationError

location_bp = Blueprint('locations', __name__)


@location_bp.route('/locations', methods=['GET'])
@token_required
def get_locations():
    query = Location.query
    if request.args.get('is_active', '').lower() == 'true':
        query = query.filter_by(is_active=True)
    if request.args.get('location_type'):
        query = query.filter_by(location_type=request.args['location_type'])
    items = query.order_by(Location.location_name).all()
    return success_response(data=[{
        'id': l.id, 'location_code': l.location_code, 'location_name': l.location_name,
        'location_type': l.location_type, 'warehouse_name': l.warehouse_name,
        'is_quarantine': l.is_quarantine, 'is_restricted': l.is_restricted,
        'odoo_location_id': l.odoo_location_id, 'is_active': l.is_active,
    } for l in items])


@location_bp.route('/locations', methods=['POST'])
@token_required
@role_required('admin')
def create_location():
    try:
        data = LocationSchema().load(request.get_json())
    except ValidationError as e:
        return validation_error(e.messages)
    if Location.query.filter(db.func.lower(Location.location_code) == data['location_code'].lower()).first():
        return error_response('Location code already exists', 409)
    loc = Location(**{k: v for k, v in data.items() if hasattr(Location, k)})
    db.session.add(loc)
    db.session.flush()
    AuditLog.log('qc_locations', loc.id, 'INSERT', new_data=data)
    db.session.commit()
    return success_response(data={'id': loc.id, 'location_code': loc.location_code}, message='Location created', status_code=201)


@location_bp.route('/locations/<int:id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_location(id):
    loc = Location.query.get_or_404(id, description='Location not found')
    try:
        data = LocationSchema().load(request.get_json(), partial=True)
    except ValidationError as e:
        return validation_error(e.messages)
    if 'location_code' in data and data['location_code'].lower() != loc.location_code.lower():
        if Location.query.filter(db.func.lower(Location.location_code) == data['location_code'].lower(), Location.id != id).first():
            return error_response('Location code already exists', 409)
    for k, v in data.items():
        if hasattr(loc, k): setattr(loc, k, v)
    db.session.commit()
    return success_response(message='Location updated')


@location_bp.route('/locations/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_location(id):
    loc = Location.query.get_or_404(id, description='Location not found')
    loc.is_active = False
    db.session.commit()
    return success_response(message='Location deactivated')
