from flask import Blueprint, request, g
from app.extensions import db
from app.models.masters import (ProductCategory, ProductGroup, Unit, Instrument,
                                 Vendor, Department)
from app.models.components import ComponentMaster, ComponentCheckingParam
from app.models.qc_plans import QCPlanParameter
from app.models.audit import AuditLog
from app.schemas.masters_schema import (CategorySchema, ProductGroupSchema, UnitSchema,
                                         InstrumentSchema, VendorSchema)
from app.middleware.auth_middleware import token_required, role_required
from app.utils.responses import success_response, error_response, validation_error
from app.utils.pagination import get_pagination_params, paginate_query, get_sort_params
from app.utils.validators import validate_gst, validate_pan, validate_pincode, validate_email
from marshmallow import ValidationError

masters_bp = Blueprint('masters', __name__)


# ══════ CATEGORIES ══════

@masters_bp.route('/categories', methods=['GET'])
@token_required
def get_categories():
    query = ProductCategory.query
    if request.args.get('is_active', '').lower() == 'true':
        query = query.filter_by(is_active=True)
    cats = query.order_by(ProductCategory.sort_order, ProductCategory.category_name).all()
    result = []
    for c in cats:
        groups = ProductGroup.query.filter_by(category_id=c.id, is_active=True).order_by(ProductGroup.sort_order).all()
        group_list = []
        for g_item in groups:
            cnt = ComponentMaster.query.filter_by(product_group_id=g_item.id, is_deleted=False).count()
            group_list.append({'id': g_item.id, 'group_code': g_item.group_code,
                               'group_name': g_item.group_name, 'components_count': cnt})
        result.append({
            'id': c.id, 'category_code': c.category_code, 'category_name': c.category_name,
            'icon': c.icon, 'description': c.description, 'sort_order': c.sort_order,
            'is_active': c.is_active,
            'groups_count': len(groups),
            'components_count': ComponentMaster.query.filter_by(category_id=c.id, is_deleted=False).count(),
            'groups': group_list,
            'created_at': c.created_at.isoformat() if c.created_at else None,
        })
    return success_response(data=result)


@masters_bp.route('/categories', methods=['POST'])
@token_required
@role_required('admin')
def create_category():
    try:
        data = CategorySchema().load(request.get_json())
    except ValidationError as e:
        return validation_error(e.messages)
    if ProductCategory.query.filter(db.func.lower(ProductCategory.category_code) == data['category_code'].lower()).first():
        return error_response('Category code already exists', 409)
    cat = ProductCategory(**{k: v for k, v in data.items() if hasattr(ProductCategory, k)})
    cat.created_by = g.current_user.get('user_name')
    db.session.add(cat)
    db.session.flush()
    AuditLog.log('qc_product_categories', cat.id, 'INSERT', new_data=data)
    db.session.commit()
    return success_response(data={'id': cat.id, 'category_code': cat.category_code,
                                   'category_name': cat.category_name},
                            message='Category created', status_code=201)


@masters_bp.route('/categories/<int:id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_category(id):
    cat = ProductCategory.query.get_or_404(id, description='Category not found')
    try:
        data = CategorySchema().load(request.get_json(), partial=True)
    except ValidationError as e:
        return validation_error(e.messages)
    if 'category_code' in data and data['category_code'].lower() != cat.category_code.lower():
        if ProductCategory.query.filter(db.func.lower(ProductCategory.category_code) == data['category_code'].lower(), ProductCategory.id != id).first():
            return error_response('Category code already exists', 409)
    for k, v in data.items():
        if hasattr(cat, k):
            setattr(cat, k, v)
    cat.updated_by = g.current_user.get('user_name')
    AuditLog.log('qc_product_categories', cat.id, 'UPDATE', new_data=data)
    db.session.commit()
    return success_response(data={'id': cat.id, 'category_code': cat.category_code, 'category_name': cat.category_name},
                            message='Category updated')


@masters_bp.route('/categories/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_category(id):
    cat = ProductCategory.query.get_or_404(id, description='Category not found')
    if ComponentMaster.query.filter_by(category_id=id, is_deleted=False).count() > 0:
        return error_response('Cannot delete: components reference this category', 409)
    cat.is_active = False
    AuditLog.log('qc_product_categories', cat.id, 'DELETE')
    db.session.commit()
    return success_response(message='Category deactivated')


# ══════ PRODUCT GROUPS ══════

@masters_bp.route('/categories/<int:category_id>/groups', methods=['GET'])
@token_required
def get_groups(category_id):
    cat = ProductCategory.query.get_or_404(category_id, description='Category not found')
    groups = ProductGroup.query.filter_by(category_id=category_id, is_active=True).order_by(ProductGroup.sort_order).all()
    result = []
    for g_item in groups:
        result.append({
            'id': g_item.id, 'group_code': g_item.group_code, 'group_name': g_item.group_name,
            'description': g_item.description, 'sort_order': g_item.sort_order, 'is_active': g_item.is_active,
            'components_count': ComponentMaster.query.filter_by(product_group_id=g_item.id, is_deleted=False).count(),
        })
    return success_response(data=result)


@masters_bp.route('/categories/<int:category_id>/groups', methods=['POST'])
@token_required
@role_required('admin')
def create_group(category_id):
    cat = ProductCategory.query.get_or_404(category_id, description='Category not found')
    if not cat.is_active:
        return error_response('Category is inactive', 400)
    try:
        data = ProductGroupSchema().load(request.get_json())
    except ValidationError as e:
        return validation_error(e.messages)
    if ProductGroup.query.filter(db.func.lower(ProductGroup.group_code) == data['group_code'].lower()).first():
        return error_response('Group code already exists', 409)
    grp = ProductGroup(category_id=category_id, **{k: v for k, v in data.items() if hasattr(ProductGroup, k)})
    db.session.add(grp)
    db.session.flush()
    AuditLog.log('qc_product_groups', grp.id, 'INSERT', new_data=data)
    db.session.commit()
    return success_response(data={'id': grp.id, 'group_code': grp.group_code, 'group_name': grp.group_name},
                            message='Product group created', status_code=201)


@masters_bp.route('/product-groups/<int:id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_group(id):
    grp = ProductGroup.query.get_or_404(id, description='Group not found')
    try:
        data = ProductGroupSchema().load(request.get_json(), partial=True)
    except ValidationError as e:
        return validation_error(e.messages)
    if 'group_code' in data and data['group_code'].lower() != grp.group_code.lower():
        if ProductGroup.query.filter(db.func.lower(ProductGroup.group_code) == data['group_code'].lower(), ProductGroup.id != id).first():
            return error_response('Group code already exists', 409)
    for k, v in data.items():
        if hasattr(grp, k):
            setattr(grp, k, v)
    db.session.commit()
    return success_response(data={'id': grp.id, 'group_code': grp.group_code, 'group_name': grp.group_name},
                            message='Group updated')


@masters_bp.route('/product-groups/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_group(id):
    grp = ProductGroup.query.get_or_404(id, description='Group not found')
    if ComponentMaster.query.filter_by(product_group_id=id, is_deleted=False).count() > 0:
        return error_response('Cannot delete: components reference this group', 409)
    grp.is_active = False
    db.session.commit()
    return success_response(message='Group deactivated')


# ══════ UNITS ══════

@masters_bp.route('/units', methods=['GET'])
@token_required
def get_units():
    query = Unit.query
    if request.args.get('unit_type'):
        query = query.filter_by(unit_type=request.args['unit_type'])
    if request.args.get('is_active', '').lower() == 'true':
        query = query.filter_by(is_active=True)
    units = query.order_by(Unit.unit_type, Unit.unit_name).all()
    return success_response(data=[{
        'id': u.id, 'unit_code': u.unit_code, 'unit_name': u.unit_name,
        'unit_symbol': u.unit_symbol, 'unit_type': u.unit_type, 'is_active': u.is_active,
    } for u in units])


@masters_bp.route('/units', methods=['POST'])
@token_required
@role_required('admin')
def create_unit():
    try:
        data = UnitSchema().load(request.get_json())
    except ValidationError as e:
        return validation_error(e.messages)
    if Unit.query.filter(db.func.lower(Unit.unit_code) == data['unit_code'].lower()).first():
        return error_response('Unit code already exists', 409)
    unit = Unit(**{k: v for k, v in data.items() if hasattr(Unit, k)})
    db.session.add(unit)
    db.session.flush()
    AuditLog.log('qc_units', unit.id, 'INSERT', new_data=data)
    db.session.commit()
    return success_response(data={'id': unit.id, 'unit_code': unit.unit_code}, message='Unit created', status_code=201)


@masters_bp.route('/units/<int:id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_unit(id):
    unit = Unit.query.get_or_404(id, description='Unit not found')
    try:
        data = UnitSchema().load(request.get_json(), partial=True)
    except ValidationError as e:
        return validation_error(e.messages)
    if 'unit_code' in data and data['unit_code'].lower() != unit.unit_code.lower():
        if Unit.query.filter(db.func.lower(Unit.unit_code) == data['unit_code'].lower(), Unit.id != id).first():
            return error_response('Unit code already exists', 409)
    for k, v in data.items():
        if hasattr(unit, k):
            setattr(unit, k, v)
    db.session.commit()
    return success_response(message='Unit updated')


@masters_bp.route('/units/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_unit(id):
    unit = Unit.query.get_or_404(id, description='Unit not found')
    if ComponentCheckingParam.query.filter_by(unit_id=id).count() > 0:
        return error_response('Cannot delete: referenced by checking parameters', 409)
    if QCPlanParameter.query.filter_by(unit_id=id).count() > 0:
        return error_response('Cannot delete: referenced by plan parameters', 409)
    unit.is_active = False
    db.session.commit()
    return success_response(message='Unit deactivated')


# ══════ INSTRUMENTS ══════

def _serialize_instrument(i):
    dept = None
    if i.dept:
        dept = {'id': i.dept.id, 'department_name': i.dept.department_name}
    return {
        'id': i.id, 'instrument_code': i.instrument_code, 'instrument_name': i.instrument_name,
        'instrument_type': i.instrument_type, 'make': i.make, 'model': i.model,
        'serial_number': i.serial_number,
        'calibration_frequency_days': i.calibration_frequency_days,
        'last_calibration_date': i.last_calibration_date.isoformat() if i.last_calibration_date else None,
        'calibration_due_date': i.calibration_due_date.isoformat() if i.calibration_due_date else None,
        'calibration_certificate_no': i.calibration_certificate_no,
        'location': i.location, 'department_id': i.department_id, 'department': dept,
        'is_active': i.is_active,
        'calibration_status': i.calibration_status,
        'days_until_due': i.days_until_due,
        'created_at': i.created_at.isoformat() if i.created_at else None,
    }


@masters_bp.route('/instruments', methods=['GET'])
@token_required
def get_instruments():
    query = Instrument.query
    if request.args.get('department_id'):
        query = query.filter_by(department_id=int(request.args['department_id']))
    if request.args.get('is_active', '').lower() == 'true':
        query = query.filter_by(is_active=True)
    search = request.args.get('search')
    if search:
        query = query.filter(db.or_(
            Instrument.instrument_code.ilike(f'%{search}%'),
            Instrument.instrument_name.ilike(f'%{search}%')))
    page, per_page = get_pagination_params()
    items, meta = paginate_query(query.order_by(Instrument.instrument_name), page, per_page)
    result = [_serialize_instrument(i) for i in items]
    # Filter by calibration_status in Python (computed field)
    cal_status = request.args.get('calibration_status')
    if cal_status:
        result = [r for r in result if r['calibration_status'] == cal_status]
    return success_response(data=result, meta=meta)


@masters_bp.route('/instruments', methods=['POST'])
@token_required
@role_required('admin')
def create_instrument():
    try:
        data = InstrumentSchema().load(request.get_json())
    except ValidationError as e:
        return validation_error(e.messages)
    if Instrument.query.filter(db.func.lower(Instrument.instrument_code) == data['instrument_code'].lower()).first():
        return error_response('Instrument code already exists', 409)
    if data.get('department_id') and not Department.query.filter_by(id=data['department_id'], is_active=True).first():
        return validation_error({'department_id': 'Invalid or inactive department'})
    inst = Instrument(**{k: v for k, v in data.items() if hasattr(Instrument, k)})
    db.session.add(inst)
    db.session.flush()
    AuditLog.log('qc_instruments', inst.id, 'INSERT', new_data=data)
    db.session.commit()
    return success_response(data=_serialize_instrument(inst), message='Instrument created', status_code=201)


@masters_bp.route('/instruments/<int:id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_instrument(id):
    inst = Instrument.query.get_or_404(id, description='Instrument not found')
    try:
        data = InstrumentSchema().load(request.get_json(), partial=True)
    except ValidationError as e:
        return validation_error(e.messages)
    if 'instrument_code' in data and data['instrument_code'].lower() != inst.instrument_code.lower():
        if Instrument.query.filter(db.func.lower(Instrument.instrument_code) == data['instrument_code'].lower(), Instrument.id != id).first():
            return error_response('Instrument code already exists', 409)
    for k, v in data.items():
        if hasattr(inst, k):
            setattr(inst, k, v)
    db.session.commit()
    return success_response(data=_serialize_instrument(inst), message='Instrument updated')


@masters_bp.route('/instruments/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_instrument(id):
    inst = Instrument.query.get_or_404(id, description='Instrument not found')
    if ComponentCheckingParam.query.filter_by(instrument_id=id).count() > 0:
        return error_response('Cannot delete: referenced by checking parameters', 409)
    inst.is_active = False
    db.session.commit()
    return success_response(message='Instrument deactivated')


# ══════ VENDORS ══════

def _serialize_vendor(v):
    return {
        'id': v.id, 'vendor_code': v.vendor_code, 'vendor_name': v.vendor_name,
        'vendor_type': v.vendor_type, 'contact_person': v.contact_person,
        'email': v.email, 'phone': v.phone, 'mobile': v.mobile,
        'address_line1': v.address_line1, 'address_line2': v.address_line2,
        'city': v.city, 'state': v.state, 'country': v.country, 'pincode': v.pincode,
        'gst_number': v.gst_number, 'pan_number': v.pan_number,
        'is_approved': v.is_approved,
        'quality_rating': float(v.quality_rating) if v.quality_rating else None,
        'delivery_rating': float(v.delivery_rating) if v.delivery_rating else None,
        'odoo_partner_id': v.odoo_partner_id, 'is_active': v.is_active,
        'components_count': ComponentMaster.query.filter_by(primary_vendor_id=v.id, is_deleted=False).count(),
        'created_at': v.created_at.isoformat() if v.created_at else None,
    }


@masters_bp.route('/vendors', methods=['GET'])
@token_required
def get_vendors():
    query = Vendor.query
    if request.args.get('is_active', '').lower() == 'true':
        query = query.filter_by(is_active=True)
    if request.args.get('is_approved', '').lower() == 'true':
        query = query.filter_by(is_approved=True)
    search = request.args.get('search')
    if search:
        query = query.filter(db.or_(
            Vendor.vendor_code.ilike(f'%{search}%'),
            Vendor.vendor_name.ilike(f'%{search}%'),
            Vendor.city.ilike(f'%{search}%')))
    sort_by, sort_order = get_sort_params(
        ['vendor_name', 'vendor_code', 'city', 'created_at'], 'vendor_name', 'asc')
    col = getattr(Vendor, sort_by)
    query = query.order_by(col.asc() if sort_order == 'asc' else col.desc())
    page, per_page = get_pagination_params()
    items, meta = paginate_query(query, page, per_page)
    return success_response(data=[_serialize_vendor(v) for v in items], meta=meta)


@masters_bp.route('/vendors', methods=['POST'])
@token_required
@role_required('admin')
def create_vendor():
    try:
        data = VendorSchema().load(request.get_json())
    except ValidationError as e:
        return validation_error(e.messages)
    if Vendor.query.filter(db.func.lower(Vendor.vendor_code) == data['vendor_code'].lower()).first():
        return error_response('Vendor code already exists', 409)
    # Business validations
    errors = []
    if data.get('gst_number'):
        err = validate_gst(data['gst_number'])
        if err:
            errors.append({'field': 'gst_number', 'message': err})
    if data.get('pan_number'):
        err = validate_pan(data['pan_number'])
        if err:
            errors.append({'field': 'pan_number', 'message': err})
    if data.get('pincode'):
        err = validate_pincode(data['pincode'])
        if err:
            errors.append({'field': 'pincode', 'message': err})
    if data.get('email'):
        err = validate_email(data['email'])
        if err:
            errors.append({'field': 'email', 'message': err})
    if errors:
        return validation_error(errors)
    vendor = Vendor(**{k: v for k, v in data.items() if hasattr(Vendor, k)})
    db.session.add(vendor)
    db.session.flush()
    AuditLog.log('qc_vendors', vendor.id, 'INSERT', new_data=data)
    db.session.commit()
    return success_response(data=_serialize_vendor(vendor), message='Vendor created', status_code=201)


@masters_bp.route('/vendors/<int:id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_vendor(id):
    vendor = Vendor.query.get_or_404(id, description='Vendor not found')
    try:
        data = VendorSchema().load(request.get_json(), partial=True)
    except ValidationError as e:
        return validation_error(e.messages)
    if 'vendor_code' in data and data['vendor_code'].lower() != vendor.vendor_code.lower():
        if Vendor.query.filter(db.func.lower(Vendor.vendor_code) == data['vendor_code'].lower(), Vendor.id != id).first():
            return error_response('Vendor code already exists', 409)
    errors = []
    if data.get('gst_number'):
        err = validate_gst(data['gst_number'])
        if err: errors.append({'field': 'gst_number', 'message': err})
    if data.get('pan_number'):
        err = validate_pan(data['pan_number'])
        if err: errors.append({'field': 'pan_number', 'message': err})
    if errors:
        return validation_error(errors)
    for k, v in data.items():
        if hasattr(vendor, k):
            setattr(vendor, k, v)
    db.session.commit()
    return success_response(data=_serialize_vendor(vendor), message='Vendor updated')


@masters_bp.route('/vendors/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_vendor(id):
    vendor = Vendor.query.get_or_404(id, description='Vendor not found')
    vendor.is_active = False
    AuditLog.log('qc_vendors', vendor.id, 'DELETE')
    db.session.commit()
    return success_response(message='Vendor deactivated')
