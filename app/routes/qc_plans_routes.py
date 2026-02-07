from flask import Blueprint, request, g
from app.extensions import db
from app.models.qc_plans import QCPlan, QCPlanStage, QCPlanParameter
from app.models.sampling import SamplingPlan
from app.models.masters import Unit, Instrument
from app.models.components import ComponentMaster
from app.models.audit import AuditLog
from app.schemas.qc_plans_schema import QCPlanSchema
from app.middleware.auth_middleware import token_required, role_required
from app.utils.responses import success_response, error_response, validation_error
from app.utils.pagination import get_pagination_params, paginate_query
from marshmallow import ValidationError

qc_plans_bp = Blueprint('qc_plans', __name__)
plan_schema = QCPlanSchema()


def _serialize_param(p):
    unit = None
    if p.unit:
        unit = {'id': p.unit.id, 'unit_code': p.unit.unit_code, 'unit_name': p.unit.unit_name}
    instrument = None
    if p.instrument:
        instrument = {'id': p.instrument.id, 'instrument_code': p.instrument.instrument_code,
                       'instrument_name': p.instrument.instrument_name}
    return {
        'id': p.id, 'parameter_code': p.parameter_code, 'parameter_name': p.parameter_name,
        'parameter_sequence': p.parameter_sequence, 'checking_type': p.checking_type,
        'specification': p.specification,
        'nominal_value': str(p.nominal_value) if p.nominal_value is not None else None,
        'tolerance_min': str(p.tolerance_min) if p.tolerance_min is not None else None,
        'tolerance_max': str(p.tolerance_max) if p.tolerance_max is not None else None,
        'unit_id': p.unit_id, 'unit': unit,
        'instrument_id': p.instrument_id, 'instrument': instrument,
        'input_type': p.input_type, 'is_mandatory': p.is_mandatory,
        'acceptance_criteria': p.acceptance_criteria,
    }


def _serialize_stage(s):
    sp = None
    if s.sampling_plan:
        sp = {'id': s.sampling_plan.id, 'plan_code': s.sampling_plan.plan_code,
              'plan_name': s.sampling_plan.plan_name}
    params = [_serialize_param(p) for p in s.parameters.all()]
    return {
        'id': s.id, 'stage_code': s.stage_code, 'stage_name': s.stage_name,
        'stage_type': s.stage_type, 'stage_sequence': s.stage_sequence,
        'inspection_type': s.inspection_type, 'sampling_plan_id': s.sampling_plan_id,
        'sampling_plan': sp, 'is_mandatory': s.is_mandatory,
        'requires_instrument': s.requires_instrument,
        'parameters': params, 'parameters_count': len(params),
    }


def _serialize_plan(p, full=False):
    result = {
        'id': p.id, 'plan_code': p.plan_code, 'plan_name': p.plan_name,
        'plan_type': p.plan_type, 'revision': p.revision,
        'revision_date': p.revision_date.isoformat() if p.revision_date else None,
        'effective_date': p.effective_date.isoformat() if p.effective_date else None,
        'requires_visual': p.requires_visual, 'requires_functional': p.requires_functional,
        'status': p.status, 'is_active': p.is_active,
        'stages_count': p.stages.count(),
        'parameters_count': sum(s.parameters.count() for s in p.stages.all()),
        'components_using': ComponentMaster.query.filter_by(qc_plan_id=p.id, is_deleted=False).count(),
        'created_at': p.created_at.isoformat() if p.created_at else None,
        'updated_at': p.updated_at.isoformat() if p.updated_at else None,
    }
    if full:
        result['stages'] = [_serialize_stage(s) for s in p.stages.order_by(QCPlanStage.stage_sequence).all()]
    return result


@qc_plans_bp.route('/qc-plans', methods=['GET'])
@token_required
def get_qc_plans():
    query = QCPlan.query
    if request.args.get('status'):
        query = query.filter_by(status=request.args['status'])
    search = request.args.get('search')
    if search:
        query = query.filter(db.or_(
            QCPlan.plan_code.ilike(f'%{search}%'),
            QCPlan.plan_name.ilike(f'%{search}%')))
    page, per_page = get_pagination_params()
    items, meta = paginate_query(query.order_by(QCPlan.plan_code), page, per_page)
    return success_response(data=[_serialize_plan(p) for p in items], meta=meta)


@qc_plans_bp.route('/qc-plans/<int:id>', methods=['GET'])
@token_required
def get_qc_plan(id):
    plan = QCPlan.query.get_or_404(id, description='QC Plan not found')
    return success_response(data=_serialize_plan(plan, full=True))


@qc_plans_bp.route('/qc-plans', methods=['POST'])
@token_required
@role_required('admin')
def create_qc_plan():
    try:
        data = plan_schema.load(request.get_json())
    except ValidationError as e:
        return validation_error(e.messages if isinstance(e.messages, dict) else e.messages)
    if not data.get('stages'):
        return validation_error({'stages': 'At least 1 stage required'})
    if QCPlan.query.filter(db.func.lower(QCPlan.plan_code) == data['plan_code'].lower()).first():
        return error_response('Plan code already exists', 409)
    # Validate FK references
    errors = []
    for i, stage in enumerate(data.get('stages', [])):
        if stage.get('sampling_plan_id'):
            sp = SamplingPlan.query.filter_by(id=stage['sampling_plan_id'], is_active=True).first()
            if not sp:
                errors.append({'field': f'stages[{i}].sampling_plan_id', 'message': 'Invalid or inactive sampling plan'})
        if not stage.get('parameters'):
            errors.append({'field': f'stages[{i}].parameters', 'message': 'At least 1 parameter required per stage'})
        for j, param in enumerate(stage.get('parameters', [])):
            if param.get('unit_id') and not Unit.query.filter_by(id=param['unit_id'], is_active=True).first():
                errors.append({'field': f'stages[{i}].parameters[{j}].unit_id', 'message': 'Invalid or inactive unit'})
            if param.get('instrument_id') and not Instrument.query.filter_by(id=param['instrument_id'], is_active=True).first():
                errors.append({'field': f'stages[{i}].parameters[{j}].instrument_id', 'message': 'Invalid instrument'})
    if errors:
        return validation_error(errors)

    plan = QCPlan(
        plan_code=data['plan_code'], plan_name=data['plan_name'],
        plan_type=data.get('plan_type', 'standard'), revision=data.get('revision'),
        revision_date=data.get('revision_date'), effective_date=data.get('effective_date'),
        requires_visual=data.get('requires_visual', True),
        requires_functional=data.get('requires_functional', False),
        document_number=data.get('document_number'),
        status='active', inspection_stages=len(data['stages']))
    db.session.add(plan)
    db.session.flush()

    for stage_data in data['stages']:
        stage_code = stage_data.get('stage_code') or f'STG-{stage_data["stage_sequence"]:02d}'
        stage = QCPlanStage(
            qc_plan_id=plan.id, stage_code=stage_code,
            stage_name=stage_data['stage_name'], stage_type=stage_data['stage_type'],
            stage_sequence=stage_data['stage_sequence'],
            inspection_type=stage_data.get('inspection_type', 'sampling'),
            sampling_plan_id=stage_data.get('sampling_plan_id'),
            is_mandatory=stage_data.get('is_mandatory', True),
            requires_instrument=stage_data.get('requires_instrument', False))
        db.session.add(stage)
        db.session.flush()
        for p_data in stage_data.get('parameters', []):
            param = QCPlanParameter(
                qc_plan_stage_id=stage.id,
                parameter_code=p_data.get('parameter_code'),
                parameter_name=p_data['parameter_name'],
                parameter_sequence=p_data.get('parameter_sequence', 0),
                checking_type=p_data['checking_type'],
                specification=p_data.get('specification'),
                unit_id=p_data.get('unit_id'),
                nominal_value=p_data.get('nominal_value'),
                tolerance_min=p_data.get('tolerance_min'),
                tolerance_max=p_data.get('tolerance_max'),
                instrument_id=p_data.get('instrument_id'),
                input_type=p_data.get('input_type', 'measurement'),
                is_mandatory=p_data.get('is_mandatory', True),
                acceptance_criteria=p_data.get('acceptance_criteria'))
            db.session.add(param)

    AuditLog.log('qc_plans', plan.id, 'INSERT')
    db.session.commit()
    return success_response(data=_serialize_plan(plan, full=True), message='QC Plan created', status_code=201)


@qc_plans_bp.route('/qc-plans/<int:id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_qc_plan(id):
    plan = QCPlan.query.get_or_404(id, description='QC Plan not found')
    try:
        data = plan_schema.load(request.get_json(), partial=True)
    except ValidationError as e:
        return validation_error(e.messages if isinstance(e.messages, dict) else e.messages)
    if 'plan_code' in data and data['plan_code'].lower() != plan.plan_code.lower():
        if QCPlan.query.filter(db.func.lower(QCPlan.plan_code) == data['plan_code'].lower(), QCPlan.id != id).first():
            return error_response('Plan code already exists', 409)
    for k in ('plan_code', 'plan_name', 'plan_type', 'revision', 'revision_date',
              'effective_date', 'requires_visual', 'requires_functional', 'document_number'):
        if k in data:
            setattr(plan, k, data[k])
    if 'stages' in data:
        # Delete old stages (cascade deletes params)
        QCPlanStage.query.filter_by(qc_plan_id=id).delete()
        plan.inspection_stages = len(data['stages'])
        for stage_data in data['stages']:
            stage_code = stage_data.get('stage_code') or f'STG-{stage_data["stage_sequence"]:02d}'
            stage = QCPlanStage(
                qc_plan_id=id, stage_code=stage_code,
                stage_name=stage_data['stage_name'], stage_type=stage_data['stage_type'],
                stage_sequence=stage_data['stage_sequence'],
                inspection_type=stage_data.get('inspection_type', 'sampling'),
                sampling_plan_id=stage_data.get('sampling_plan_id'),
                is_mandatory=stage_data.get('is_mandatory', True),
                requires_instrument=stage_data.get('requires_instrument', False))
            db.session.add(stage)
            db.session.flush()
            for p_data in stage_data.get('parameters', []):
                param = QCPlanParameter(
                    qc_plan_stage_id=stage.id, parameter_code=p_data.get('parameter_code'),
                    parameter_name=p_data['parameter_name'],
                    parameter_sequence=p_data.get('parameter_sequence', 0),
                    checking_type=p_data['checking_type'],
                    specification=p_data.get('specification'),
                    unit_id=p_data.get('unit_id'),
                    nominal_value=p_data.get('nominal_value'),
                    tolerance_min=p_data.get('tolerance_min'),
                    tolerance_max=p_data.get('tolerance_max'),
                    instrument_id=p_data.get('instrument_id'),
                    input_type=p_data.get('input_type', 'measurement'),
                    is_mandatory=p_data.get('is_mandatory', True),
                    acceptance_criteria=p_data.get('acceptance_criteria'))
                db.session.add(param)
    AuditLog.log('qc_plans', plan.id, 'UPDATE')
    db.session.commit()
    return success_response(data=_serialize_plan(plan, full=True), message='QC Plan updated')


@qc_plans_bp.route('/qc-plans/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_qc_plan(id):
    plan = QCPlan.query.get_or_404(id, description='QC Plan not found')
    if plan.status != 'draft':
        return error_response('Only draft plans can be deleted', 409)
    if ComponentMaster.query.filter_by(qc_plan_id=id, is_deleted=False).count() > 0:
        return error_response('Cannot delete: referenced by components', 409)
    plan.is_active = False
    plan.status = 'superseded'
    db.session.commit()
    return success_response(message='QC Plan deactivated')
