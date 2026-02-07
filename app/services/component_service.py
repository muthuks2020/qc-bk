"""Component service for complex CRUD operations."""
from flask import g
from app.extensions import db
from app.models.components import (ComponentMaster, ComponentCheckingParam,
                                    ComponentSpecification, ComponentVendor)
from app.models.masters import (ProductCategory, ProductGroup, Vendor, Department,
                                 Unit, Instrument)
from app.models.sampling import SamplingPlan
from app.models.qc_plans import QCPlan
from app.models.audit import AuditLog, ComponentHistory


def validate_component_refs(data, component_id=None):
    """Validate all FK references. Returns list of error dicts."""
    errors = []

    # Category
    cat = ProductCategory.query.filter_by(id=data['category_id'], is_active=True).first()
    if not cat:
        errors.append({'field': 'category_id', 'message': 'Invalid or inactive category'})

    # Group must belong to category
    grp = ProductGroup.query.filter_by(id=data['product_group_id'], is_active=True).first()
    if not grp:
        errors.append({'field': 'product_group_id', 'message': 'Invalid or inactive product group'})
    elif grp.category_id != data['category_id']:
        errors.append({'field': 'product_group_id',
                       'message': f'Group does not belong to category_id {data["category_id"]}'})

    # QC Plan
    if data.get('qc_plan_id'):
        if not QCPlan.query.filter_by(id=data['qc_plan_id'], is_active=True).first():
            errors.append({'field': 'qc_plan_id', 'message': 'Invalid or inactive QC plan'})

    # Sampling plan
    if data.get('default_sampling_plan_id'):
        if not SamplingPlan.query.filter_by(id=data['default_sampling_plan_id'], is_active=True).first():
            errors.append({'field': 'default_sampling_plan_id', 'message': 'Invalid or inactive sampling plan'})

    # Department
    if data.get('department_id'):
        if not Department.query.filter_by(id=data['department_id'], is_active=True).first():
            errors.append({'field': 'department_id', 'message': 'Invalid or inactive department'})

    # Primary vendor
    if data.get('primary_vendor_id'):
        if not Vendor.query.filter_by(id=data['primary_vendor_id'], is_active=True).first():
            errors.append({'field': 'primary_vendor_id', 'message': 'Invalid or inactive vendor'})

    # Unique part_code
    query = ComponentMaster.query.filter(
        db.func.lower(ComponentMaster.part_code) == data['part_code'].lower(),
        ComponentMaster.is_deleted == False
    )
    if component_id:
        query = query.filter(ComponentMaster.id != component_id)
    if query.first():
        errors.append({'field': 'part_code', 'message': f'Part code {data["part_code"]} already exists'})

    # Validate checking params refs
    for i, param in enumerate(data.get('checking_parameters', [])):
        if param.get('unit_id') and not Unit.query.filter_by(id=param['unit_id'], is_active=True).first():
            errors.append({'field': f'checking_parameters[{i}].unit_id', 'message': 'Invalid unit'})
        if param.get('instrument_id') and not Instrument.query.filter_by(id=param['instrument_id'], is_active=True).first():
            errors.append({'field': f'checking_parameters[{i}].instrument_id', 'message': 'Invalid instrument'})

    # Validate vendor refs
    for i, v in enumerate(data.get('approved_vendors', [])):
        if not Vendor.query.filter_by(id=v['vendor_id'], is_active=True).first():
            errors.append({'field': f'approved_vendors[{i}].vendor_id', 'message': 'Invalid or inactive vendor'})

    return errors


def create_component(data):
    """Create component with children. Returns (component, errors)."""
    user = g.current_user

    comp = ComponentMaster(
        part_code=data['part_code'], part_name=data['part_name'],
        part_description=data.get('part_description'),
        category_id=data['category_id'], product_group_id=data['product_group_id'],
        qc_required=data.get('qc_required', True),
        qc_plan_id=data.get('qc_plan_id'),
        default_inspection_type=data['default_inspection_type'],
        default_sampling_plan_id=data.get('default_sampling_plan_id'),
        drawing_no=data.get('drawing_no'), drawing_revision=data.get('drawing_revision'),
        test_cert_required=data.get('test_cert_required', False),
        spec_required=data.get('spec_required', False),
        fqir_required=data.get('fqir_required', False),
        coc_required=data.get('coc_required', False),
        pr_process_code=data.get('pr_process_code'),
        pr_process_name=data.get('pr_process_name'),
        skip_lot_enabled=data.get('skip_lot_enabled', False),
        skip_lot_count=data.get('skip_lot_count', 0),
        skip_lot_threshold=data.get('skip_lot_threshold', 5),
        department_id=data.get('department_id'),
        primary_vendor_id=data.get('primary_vendor_id'),
        odoo_product_id=data.get('odoo_product_id'),
        lead_time_days=data.get('lead_time_days'),
        status='active',
        created_by=user.get('user_name'),
    )
    db.session.add(comp)
    db.session.flush()  # Get ID

    # Add checking params
    _save_children(comp.id, data)

    AuditLog.log('qc_component_master', comp.id, 'INSERT')
    return comp


def update_component(comp, data):
    """Update component, replace children, log changes."""
    user = g.current_user
    fields_to_track = [
        'part_code', 'part_name', 'category_id', 'product_group_id',
        'qc_required', 'qc_plan_id', 'default_inspection_type',
        'default_sampling_plan_id', 'department_id', 'primary_vendor_id',
        'skip_lot_enabled', 'status',
    ]
    for field in fields_to_track:
        if field in data:
            old_val = getattr(comp, field)
            new_val = data[field]
            if str(old_val) != str(new_val):
                ComponentHistory.log_change(comp.id, 'UPDATE', field, old_val, new_val)

    # Update scalar fields
    scalar_fields = [
        'part_code', 'part_name', 'part_description', 'category_id', 'product_group_id',
        'qc_required', 'qc_plan_id', 'default_inspection_type', 'default_sampling_plan_id',
        'drawing_no', 'drawing_revision', 'test_cert_required', 'spec_required',
        'fqir_required', 'coc_required', 'pr_process_code', 'pr_process_name',
        'skip_lot_enabled', 'skip_lot_count', 'skip_lot_threshold',
        'department_id', 'primary_vendor_id', 'odoo_product_id', 'lead_time_days',
    ]
    for field in scalar_fields:
        if field in data:
            setattr(comp, field, data[field])

    comp.updated_by = user.get('user_name')

    # Replace children
    if 'checking_parameters' in data or 'specifications' in data or 'approved_vendors' in data:
        ComponentCheckingParam.query.filter_by(component_id=comp.id).delete()
        ComponentSpecification.query.filter_by(component_id=comp.id).delete()
        ComponentVendor.query.filter_by(component_id=comp.id).delete()
        _save_children(comp.id, data)

    AuditLog.log('qc_component_master', comp.id, 'UPDATE')


def _save_children(component_id, data):
    """Save checking params, specs, and vendor mappings."""
    for cp in data.get('checking_parameters', []):
        param = ComponentCheckingParam(
            component_id=component_id,
            checking_type=cp['checking_type'],
            checking_point=cp['checking_point'],
            specification=cp.get('specification'),
            unit_id=cp.get('unit_id'),
            unit_code=cp.get('unit_code'),
            nominal_value=cp.get('nominal_value'),
            tolerance_min=cp.get('tolerance_min'),
            tolerance_max=cp.get('tolerance_max'),
            instrument_id=cp.get('instrument_id'),
            instrument_name=cp.get('instrument_name'),
            input_type=cp.get('input_type', 'measurement'),
            sort_order=cp.get('sort_order', 0),
            is_mandatory=cp.get('is_mandatory', True),
        )
        db.session.add(param)

    for sp in data.get('specifications', []):
        spec = ComponentSpecification(
            component_id=component_id,
            spec_key=sp['spec_key'],
            spec_value=sp['spec_value'],
            sort_order=sp.get('sort_order', 0),
        )
        db.session.add(spec)

    for av in data.get('approved_vendors', []):
        cv = ComponentVendor(
            component_id=component_id,
            vendor_id=av['vendor_id'],
            is_primary=av.get('is_primary', False),
            is_approved=av.get('is_approved', False),
            vendor_part_code=av.get('vendor_part_code'),
            unit_price=av.get('unit_price'),
            lead_time_days=av.get('lead_time_days'),
            remarks=av.get('remarks'),
        )
        db.session.add(cv)
