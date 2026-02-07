from flask import Blueprint, request, g
from app.extensions import db
from app.models.sampling import SamplingPlan, SamplingPlanDetail
from app.models.components import ComponentMaster
from app.models.qc_plans import QCPlanStage
from app.models.audit import AuditLog
from app.schemas.sampling_schema import SamplingPlanSchema
from app.middleware.auth_middleware import token_required, role_required
from app.utils.responses import success_response, error_response, validation_error
from marshmallow import ValidationError

sampling_bp = Blueprint('sampling', __name__)
plan_schema = SamplingPlanSchema()


def _serialize_plan(p, include_details=True):
    result = {
        'id': p.id, 'plan_code': p.plan_code, 'plan_name': p.plan_name,
        'plan_type': p.plan_type, 'aql_level': p.aql_level,
        'inspection_level': p.inspection_level, 'is_active': p.is_active,
        'details_count': p.details.count(),
        'referenced_by_components': ComponentMaster.query.filter_by(
            default_sampling_plan_id=p.id, is_deleted=False).count(),
        'created_at': p.created_at.isoformat() if p.created_at else None,
        'updated_at': p.updated_at.isoformat() if p.updated_at else None,
    }
    if include_details:
        result['details'] = [{
            'id': d.id, 'lot_size_min': d.lot_size_min, 'lot_size_max': d.lot_size_max,
            'sample_size': d.sample_size, 'accept_number': d.accept_number,
            'reject_number': d.reject_number,
        } for d in p.details.order_by(SamplingPlanDetail.lot_size_min).all()]
    return result


@sampling_bp.route('/sampling-plans', methods=['GET'])
@token_required
def get_sampling_plans():
    query = SamplingPlan.query
    if request.args.get('is_active', '').lower() == 'true':
        query = query.filter_by(is_active=True)
    if request.args.get('plan_type'):
        query = query.filter_by(plan_type=request.args['plan_type'])
    search = request.args.get('search')
    if search:
        query = query.filter(db.or_(
            SamplingPlan.plan_code.ilike(f'%{search}%'),
            SamplingPlan.plan_name.ilike(f'%{search}%')))
    plans = query.order_by(SamplingPlan.plan_code).all()
    return success_response(data=[_serialize_plan(p) for p in plans])


@sampling_bp.route('/sampling-plans/<int:id>', methods=['GET'])
@token_required
def get_sampling_plan(id):
    plan = SamplingPlan.query.get_or_404(id, description='Sampling plan not found')
    return success_response(data=_serialize_plan(plan))


@sampling_bp.route('/sampling-plans', methods=['POST'])
@token_required
@role_required('admin')
def create_sampling_plan():
    try:
        data = plan_schema.load(request.get_json())
    except ValidationError as e:
        return validation_error(e.messages)
    if not data.get('details'):
        return validation_error({'details': 'At least 1 detail row required'})
    if SamplingPlan.query.filter(db.func.lower(SamplingPlan.plan_code) == data['plan_code'].lower()).first():
        return error_response('Plan code already exists', 409)
    plan = SamplingPlan(
        plan_code=data['plan_code'], plan_name=data['plan_name'],
        plan_type=data.get('plan_type'), aql_level=data.get('aql_level'),
        inspection_level=data.get('inspection_level'))
    db.session.add(plan)
    db.session.flush()
    for d in data['details']:
        detail = SamplingPlanDetail(sampling_plan_id=plan.id, **d)
        db.session.add(detail)
    AuditLog.log('qc_sampling_plans', plan.id, 'INSERT', new_data=data)
    db.session.commit()
    return success_response(data=_serialize_plan(plan), message='Sampling plan created', status_code=201)


@sampling_bp.route('/sampling-plans/<int:id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_sampling_plan(id):
    plan = SamplingPlan.query.get_or_404(id, description='Sampling plan not found')
    try:
        data = plan_schema.load(request.get_json(), partial=True)
    except ValidationError as e:
        return validation_error(e.messages)
    if 'plan_code' in data and data['plan_code'].lower() != plan.plan_code.lower():
        if SamplingPlan.query.filter(db.func.lower(SamplingPlan.plan_code) == data['plan_code'].lower(), SamplingPlan.id != id).first():
            return error_response('Plan code already exists', 409)
    for k in ('plan_code', 'plan_name', 'plan_type', 'aql_level', 'inspection_level'):
        if k in data:
            setattr(plan, k, data[k])
    if 'details' in data:
        SamplingPlanDetail.query.filter_by(sampling_plan_id=id).delete()
        for d in data['details']:
            db.session.add(SamplingPlanDetail(sampling_plan_id=id, **d))
    AuditLog.log('qc_sampling_plans', plan.id, 'UPDATE', new_data=data)
    db.session.commit()
    return success_response(data=_serialize_plan(plan), message='Sampling plan updated')


@sampling_bp.route('/sampling-plans/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_sampling_plan(id):
    plan = SamplingPlan.query.get_or_404(id, description='Sampling plan not found')
    if QCPlanStage.query.filter_by(sampling_plan_id=id).count() > 0:
        return error_response('Cannot delete: referenced by QC plan stages', 409)
    if ComponentMaster.query.filter_by(default_sampling_plan_id=id, is_deleted=False).count() > 0:
        return error_response('Cannot delete: referenced by components', 409)
    plan.is_active = False
    db.session.commit()
    return success_response(message='Sampling plan deactivated')


@sampling_bp.route('/sampling-plans/<int:id>/calculate-sample', methods=['GET'])
@token_required
def calculate_sample(id):
    plan = SamplingPlan.query.get_or_404(id, description='Sampling plan not found')
    try:
        lot_size = int(request.args.get('lot_size', 0))
    except (ValueError, TypeError):
        return error_response('lot_size must be a valid integer', 400)
    if lot_size < 1:
        return error_response('lot_size must be >= 1', 400)
    detail = SamplingPlanDetail.query.filter(
        SamplingPlanDetail.sampling_plan_id == id,
        SamplingPlanDetail.lot_size_min <= lot_size,
        SamplingPlanDetail.lot_size_max >= lot_size
    ).first()
    if not detail:
        max_range = db.session.query(db.func.max(SamplingPlanDetail.lot_size_max)).filter_by(
            sampling_plan_id=id).scalar() or 0
        return error_response(
            f'Lot size {lot_size} exceeds maximum range ({max_range}) in plan {plan.plan_code}', 400)
    return success_response(data={
        'plan_code': plan.plan_code, 'plan_name': plan.plan_name,
        'lot_size': lot_size,
        'matched_range': {'lot_size_min': detail.lot_size_min, 'lot_size_max': detail.lot_size_max},
        'sample_size': detail.sample_size,
        'accept_number': detail.accept_number,
        'reject_number': detail.reject_number,
    })
