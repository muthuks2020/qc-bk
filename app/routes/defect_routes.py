from flask import Blueprint, request
from app.extensions import db
from app.models.masters import DefectType, RejectionReason
from app.models.audit import AuditLog
from app.schemas.masters_schema import DefectTypeSchema, RejectionReasonSchema
from app.middleware.auth_middleware import token_required, role_required
from app.utils.responses import success_response, error_response, validation_error
from marshmallow import ValidationError

defect_bp = Blueprint('defects', __name__)


@defect_bp.route('/defect-types', methods=['GET'])
@token_required
def get_defect_types():
    query = DefectType.query
    if request.args.get('is_active', '').lower() == 'true':
        query = query.filter_by(is_active=True)
    if request.args.get('severity_level'):
        query = query.filter_by(severity_level=int(request.args['severity_level']))
    if request.args.get('defect_category'):
        query = query.filter_by(defect_category=request.args['defect_category'])
    items = query.order_by(DefectType.severity_level.desc(), DefectType.defect_name).all()
    return success_response(data=[{
        'id': d.id, 'defect_code': d.defect_code, 'defect_name': d.defect_name,
        'defect_category': d.defect_category, 'severity_level': d.severity_level,
        'description': d.description, 'is_active': d.is_active,
    } for d in items])


@defect_bp.route('/defect-types', methods=['POST'])
@token_required
@role_required('admin')
def create_defect_type():
    try:
        data = DefectTypeSchema().load(request.get_json())
    except ValidationError as e:
        return validation_error(e.messages)
    if DefectType.query.filter(db.func.lower(DefectType.defect_code) == data['defect_code'].lower()).first():
        return error_response('Defect code already exists', 409)
    dt = DefectType(**{k: v for k, v in data.items() if hasattr(DefectType, k)})
    db.session.add(dt)
    db.session.flush()
    AuditLog.log('qc_defect_types', dt.id, 'INSERT', new_data=data)
    db.session.commit()
    return success_response(data={'id': dt.id, 'defect_code': dt.defect_code}, message='Defect type created', status_code=201)


@defect_bp.route('/defect-types/<int:id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_defect_type(id):
    dt = DefectType.query.get_or_404(id, description='Defect type not found')
    try:
        data = DefectTypeSchema().load(request.get_json(), partial=True)
    except ValidationError as e:
        return validation_error(e.messages)
    if 'defect_code' in data and data['defect_code'].lower() != dt.defect_code.lower():
        if DefectType.query.filter(db.func.lower(DefectType.defect_code) == data['defect_code'].lower(), DefectType.id != id).first():
            return error_response('Defect code already exists', 409)
    for k, v in data.items():
        if hasattr(dt, k): setattr(dt, k, v)
    db.session.commit()
    return success_response(message='Defect type updated')


@defect_bp.route('/defect-types/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_defect_type(id):
    dt = DefectType.query.get_or_404(id, description='Defect type not found')
    dt.is_active = False
    db.session.commit()
    return success_response(message='Defect type deactivated')


# ══════ REJECTION REASONS ══════

@defect_bp.route('/rejection-reasons', methods=['GET'])
@token_required
def get_rejection_reasons():
    query = RejectionReason.query
    if request.args.get('is_active', '').lower() == 'true':
        query = query.filter_by(is_active=True)
    if request.args.get('reason_category'):
        query = query.filter_by(reason_category=request.args['reason_category'])
    items = query.order_by(RejectionReason.reason_name).all()
    return success_response(data=[{
        'id': r.id, 'reason_code': r.reason_code, 'reason_name': r.reason_name,
        'reason_category': r.reason_category, 'description': r.description, 'is_active': r.is_active,
    } for r in items])


@defect_bp.route('/rejection-reasons', methods=['POST'])
@token_required
@role_required('admin')
def create_rejection_reason():
    try:
        data = RejectionReasonSchema().load(request.get_json())
    except ValidationError as e:
        return validation_error(e.messages)
    if RejectionReason.query.filter(db.func.lower(RejectionReason.reason_code) == data['reason_code'].lower()).first():
        return error_response('Reason code already exists', 409)
    rr = RejectionReason(**{k: v for k, v in data.items() if hasattr(RejectionReason, k)})
    db.session.add(rr)
    db.session.flush()
    AuditLog.log('qc_rejection_reasons', rr.id, 'INSERT', new_data=data)
    db.session.commit()
    return success_response(data={'id': rr.id, 'reason_code': rr.reason_code}, message='Rejection reason created', status_code=201)


@defect_bp.route('/rejection-reasons/<int:id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_rejection_reason(id):
    rr = RejectionReason.query.get_or_404(id, description='Rejection reason not found')
    try:
        data = RejectionReasonSchema().load(request.get_json(), partial=True)
    except ValidationError as e:
        return validation_error(e.messages)
    for k, v in data.items():
        if hasattr(rr, k): setattr(rr, k, v)
    db.session.commit()
    return success_response(message='Rejection reason updated')


@defect_bp.route('/rejection-reasons/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_rejection_reason(id):
    rr = RejectionReason.query.get_or_404(id, description='Rejection reason not found')
    rr.is_active = False
    db.session.commit()
    return success_response(message='Rejection reason deactivated')
