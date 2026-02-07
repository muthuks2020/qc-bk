from flask import Blueprint, request
from app.extensions import db
from app.models.masters import (ProductCategory, ProductGroup, Unit, Instrument,
                                 Vendor, DefectType, RejectionReason, Location,
                                 Department, User, Role, UserRole)
from app.models.sampling import SamplingPlan
from app.models.qc_plans import QCPlan
from app.middleware.auth_middleware import token_required
from app.utils.responses import success_response

lookup_bp = Blueprint('lookups', __name__)


@lookup_bp.route('/lookups/categories', methods=['GET'])
@token_required
def lookup_categories():
    items = ProductCategory.query.filter_by(is_active=True).order_by(ProductCategory.sort_order).all()
    return success_response(data=[{
        'id': i.id, 'category_code': i.category_code, 'category_name': i.category_name
    } for i in items])


@lookup_bp.route('/lookups/groups', methods=['GET'])
@token_required
def lookup_groups():
    query = ProductGroup.query.filter_by(is_active=True)
    if request.args.get('category_id'):
        query = query.filter_by(category_id=int(request.args['category_id']))
    items = query.order_by(ProductGroup.sort_order).all()
    return success_response(data=[{
        'id': i.id, 'group_code': i.group_code, 'group_name': i.group_name,
        'category_id': i.category_id
    } for i in items])


@lookup_bp.route('/lookups/units', methods=['GET'])
@token_required
def lookup_units():
    query = Unit.query.filter_by(is_active=True)
    if request.args.get('unit_type'):
        query = query.filter_by(unit_type=request.args['unit_type'])
    items = query.order_by(Unit.unit_name).all()
    return success_response(data=[{
        'id': i.id, 'unit_code': i.unit_code, 'unit_name': i.unit_name,
        'unit_symbol': i.unit_symbol, 'unit_type': i.unit_type
    } for i in items])


@lookup_bp.route('/lookups/instruments', methods=['GET'])
@token_required
def lookup_instruments():
    items = Instrument.query.filter_by(is_active=True).order_by(Instrument.instrument_name).all()
    return success_response(data=[{
        'id': i.id, 'instrument_code': i.instrument_code,
        'instrument_name': i.instrument_name, 'instrument_type': i.instrument_type
    } for i in items])


@lookup_bp.route('/lookups/vendors', methods=['GET'])
@token_required
def lookup_vendors():
    query = Vendor.query.filter_by(is_active=True)
    if request.args.get('approved_only', '').lower() == 'true':
        query = query.filter_by(is_approved=True)
    items = query.order_by(Vendor.vendor_name).all()
    return success_response(data=[{
        'id': i.id, 'vendor_code': i.vendor_code, 'vendor_name': i.vendor_name,
        'is_approved': i.is_approved
    } for i in items])


@lookup_bp.route('/lookups/sampling-plans', methods=['GET'])
@token_required
def lookup_sampling_plans():
    items = SamplingPlan.query.filter_by(is_active=True).order_by(SamplingPlan.plan_code).all()
    return success_response(data=[{
        'id': i.id, 'plan_code': i.plan_code, 'plan_name': i.plan_name,
        'plan_type': i.plan_type
    } for i in items])


@lookup_bp.route('/lookups/qc-plans', methods=['GET'])
@token_required
def lookup_qc_plans():
    items = QCPlan.query.filter_by(status='active', is_active=True).order_by(QCPlan.plan_code).all()
    return success_response(data=[{
        'id': i.id, 'plan_code': i.plan_code, 'plan_name': i.plan_name,
        'inspection_stages': i.inspection_stages
    } for i in items])


@lookup_bp.route('/lookups/departments', methods=['GET'])
@token_required
def lookup_departments():
    items = Department.query.filter_by(is_active=True).order_by(Department.department_name).all()
    return success_response(data=[{
        'id': i.id, 'department_code': i.department_code, 'department_name': i.department_name
    } for i in items])


@lookup_bp.route('/lookups/defect-types', methods=['GET'])
@token_required
def lookup_defect_types():
    items = DefectType.query.filter_by(is_active=True).order_by(DefectType.defect_name).all()
    return success_response(data=[{
        'id': i.id, 'defect_code': i.defect_code, 'defect_name': i.defect_name,
        'defect_category': i.defect_category, 'severity_level': i.severity_level
    } for i in items])


@lookup_bp.route('/lookups/rejection-reasons', methods=['GET'])
@token_required
def lookup_rejection_reasons():
    items = RejectionReason.query.filter_by(is_active=True).order_by(RejectionReason.reason_name).all()
    return success_response(data=[{
        'id': i.id, 'reason_code': i.reason_code, 'reason_name': i.reason_name,
        'reason_category': i.reason_category
    } for i in items])


@lookup_bp.route('/lookups/locations', methods=['GET'])
@token_required
def lookup_locations():
    query = Location.query.filter_by(is_active=True)
    if request.args.get('location_type'):
        query = query.filter_by(location_type=request.args['location_type'])
    if request.args.get('is_quarantine', '').lower() == 'true':
        query = query.filter_by(is_quarantine=True)
    items = query.order_by(Location.location_name).all()
    return success_response(data=[{
        'id': i.id, 'location_code': i.location_code, 'location_name': i.location_name,
        'location_type': i.location_type, 'is_quarantine': i.is_quarantine
    } for i in items])


@lookup_bp.route('/lookups/users', methods=['GET'])
@token_required
def lookup_users():
    query = User.query.filter_by(is_active=True)
    role_filter = request.args.get('role')
    if role_filter:
        query = query.join(UserRole).join(Role).filter(
            Role.role_code == role_filter, UserRole.is_active == True
        )
    dept_filter = request.args.get('department_id')
    if dept_filter:
        query = query.filter_by(department_id=int(dept_filter))
    items = query.order_by(User.user_name).all()
    return success_response(data=[{
        'id': i.id, 'user_code': i.user_code, 'user_name': i.user_name,
        'email': i.email, 'designation': i.designation,
        'department_id': i.department_id
    } for i in items])


@lookup_bp.route('/lookups/roles', methods=['GET'])
@token_required
def lookup_roles():
    items = Role.query.filter_by(is_active=True).order_by(Role.role_name).all()
    return success_response(data=[{
        'id': i.id, 'role_code': i.role_code, 'role_name': i.role_name,
        'is_system_role': i.is_system_role
    } for i in items])
