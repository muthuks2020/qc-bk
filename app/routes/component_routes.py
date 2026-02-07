import os
from uuid import uuid4
from flask import Blueprint, request, g, current_app, send_from_directory
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.components import (ComponentMaster, ComponentCheckingParam,
                                    ComponentSpecification, ComponentDocument, ComponentVendor)
from app.models.audit import AuditLog
from app.schemas.components_schema import ComponentSchema
from app.middleware.auth_middleware import token_required, role_required
from app.utils.responses import success_response, error_response, validation_error
from app.utils.pagination import get_pagination_params, paginate_query, get_sort_params
from app.services.component_service import validate_component_refs, create_component, update_component
from marshmallow import ValidationError

component_bp = Blueprint('components', __name__)
comp_schema = ComponentSchema()


def _serialize_component(c, full=False):
    category = None
    if c.category:
        category = {'id': c.category.id, 'category_code': c.category.category_code,
                     'category_name': c.category.category_name}
    group = None
    if c.product_group:
        group = {'id': c.product_group.id, 'group_code': c.product_group.group_code,
                 'group_name': c.product_group.group_name}
    qc_plan = None
    if c.qc_plan:
        qc_plan = {'id': c.qc_plan.id, 'plan_code': c.qc_plan.plan_code,
                    'plan_name': c.qc_plan.plan_name}
    sampling_plan = None
    if c.sampling_plan:
        sampling_plan = {'id': c.sampling_plan.id, 'plan_code': c.sampling_plan.plan_code,
                          'plan_name': c.sampling_plan.plan_name}
    primary_vendor = None
    if c.primary_vendor:
        primary_vendor = {'id': c.primary_vendor.id, 'vendor_code': c.primary_vendor.vendor_code,
                           'vendor_name': c.primary_vendor.vendor_name}
    department = None
    if c.dept:
        department = {'id': c.dept.id, 'department_name': c.dept.department_name}

    result = {
        'id': c.id, 'component_code': c.component_code, 'part_code': c.part_code,
        'part_name': c.part_name, 'part_description': c.part_description,
        'category': category, 'group': group, 'qc_plan': qc_plan,
        'qc_required': c.qc_required,
        'default_inspection_type': c.default_inspection_type,
        'sampling_plan': sampling_plan,
        'test_cert_required': c.test_cert_required, 'spec_required': c.spec_required,
        'fqir_required': c.fqir_required, 'coc_required': c.coc_required,
        'skip_lot_enabled': c.skip_lot_enabled,
        'skip_lot_count': c.skip_lot_count, 'skip_lot_threshold': c.skip_lot_threshold,
        'pr_process_code': c.pr_process_code, 'pr_process_name': c.pr_process_name,
        'drawing_no': c.drawing_no,
        'department': department, 'primary_vendor': primary_vendor,
        'checking_params_count': c.checking_params.count(),
        'specifications_count': c.specifications.count(),
        'documents_count': c.documents.count(),
        'vendors_count': c.component_vendors.count(),
        'status': c.status, 'is_deleted': c.is_deleted,
        'created_at': c.created_at.isoformat() if c.created_at else None,
        'updated_at': c.updated_at.isoformat() if c.updated_at else None,
        'created_by': c.created_by, 'updated_by': c.updated_by,
    }

    if full:
        result['checking_parameters'] = []
        for p in c.checking_params.filter_by(is_active=True).order_by(ComponentCheckingParam.sort_order).all():
            unit = {'id': p.unit.id, 'unit_code': p.unit.unit_code, 'unit_name': p.unit.unit_name} if p.unit else None
            inst = {'id': p.instrument.id, 'instrument_code': p.instrument.instrument_code,
                     'instrument_name': p.instrument.instrument_name} if p.instrument else None
            result['checking_parameters'].append({
                'id': p.id, 'checking_type': p.checking_type, 'checking_point': p.checking_point,
                'specification': p.specification,
                'nominal_value': str(p.nominal_value) if p.nominal_value is not None else None,
                'tolerance_min': str(p.tolerance_min) if p.tolerance_min is not None else None,
                'tolerance_max': str(p.tolerance_max) if p.tolerance_max is not None else None,
                'unit_id': p.unit_id, 'unit': unit,
                'instrument_id': p.instrument_id, 'instrument': inst,
                'input_type': p.input_type, 'sort_order': p.sort_order, 'is_mandatory': p.is_mandatory,
            })
        result['specifications'] = [
            {'id': s.id, 'spec_key': s.spec_key, 'spec_value': s.spec_value, 'sort_order': s.sort_order}
            for s in c.specifications.order_by(ComponentSpecification.sort_order).all()
        ]
        result['documents'] = [
            {'id': d.id, 'document_type': d.document_type, 'file_name': d.original_name or d.file_name,
             'file_path': d.file_path, 'file_size': d.file_size, 'mime_type': d.mime_type,
             'uploaded_by': d.uploaded_by,
             'uploaded_at': d.uploaded_at.isoformat() if d.uploaded_at else None}
            for d in c.documents.filter_by(is_current=True).all()
        ]
        result['approved_vendors'] = []
        for cv in c.component_vendors.all():
            v = cv.vendor
            result['approved_vendors'].append({
                'id': cv.id, 'vendor_id': cv.vendor_id,
                'vendor': {'id': v.id, 'vendor_code': v.vendor_code, 'vendor_name': v.vendor_name} if v else None,
                'is_primary': cv.is_primary, 'is_approved': cv.is_approved,
                'unit_price': str(cv.unit_price) if cv.unit_price is not None else None,
                'lead_time_days': cv.lead_time_days,
            })
    return result


@component_bp.route('/components', methods=['GET'])
@token_required
def get_components():
    query = ComponentMaster.query.filter_by(is_deleted=False)
    if request.args.get('category_id'):
        query = query.filter_by(category_id=int(request.args['category_id']))
    if request.args.get('group_id'):
        query = query.filter_by(product_group_id=int(request.args['group_id']))
    if request.args.get('status'):
        query = query.filter_by(status=request.args['status'])
    if request.args.get('qc_required', '').lower() == 'true':
        query = query.filter_by(qc_required=True)
    if request.args.get('inspection_type'):
        query = query.filter_by(default_inspection_type=request.args['inspection_type'])
    if request.args.get('department_id'):
        query = query.filter_by(department_id=int(request.args['department_id']))
    search = request.args.get('search')
    if search:
        query = query.filter(db.or_(
            ComponentMaster.part_code.ilike(f'%{search}%'),
            ComponentMaster.part_name.ilike(f'%{search}%'),
            ComponentMaster.component_code.ilike(f'%{search}%')))
    sort_by, sort_order = get_sort_params(
        ['part_code', 'part_name', 'component_code', 'created_at', 'updated_at'], 'created_at', 'desc')
    col = getattr(ComponentMaster, sort_by)
    query = query.order_by(col.asc() if sort_order == 'asc' else col.desc())
    page, per_page = get_pagination_params()
    items, meta = paginate_query(query, page, per_page)
    return success_response(data=[_serialize_component(c) for c in items], meta=meta)


@component_bp.route('/components/<int:id>', methods=['GET'])
@token_required
def get_component(id):
    comp = ComponentMaster.query.filter_by(id=id, is_deleted=False).first()
    if not comp:
        return error_response('Component not found', 404)
    return success_response(data=_serialize_component(comp, full=True))


@component_bp.route('/components', methods=['POST'])
@token_required
@role_required('admin')
def create_comp():
    try:
        data = comp_schema.load(request.get_json())
    except ValidationError as e:
        return validation_error(e.messages if isinstance(e.messages, dict) else e.messages)

    errors = validate_component_refs(data)
    if data.get('qc_required') and not data.get('checking_parameters'):
        errors.append({'field': 'checking_parameters', 'message': 'At least 1 checking parameter required when qc_required=true'})
    if errors:
        return validation_error(errors)

    comp = create_component(data)
    db.session.commit()
    return success_response(data=_serialize_component(comp, full=True), message='Component created', status_code=201)


@component_bp.route('/components/<int:id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_comp(id):
    comp = ComponentMaster.query.filter_by(id=id, is_deleted=False).first()
    if not comp:
        return error_response('Component not found', 404)
    try:
        data = comp_schema.load(request.get_json(), partial=True)
    except ValidationError as e:
        return validation_error(e.messages if isinstance(e.messages, dict) else e.messages)
    if 'part_code' not in data:
        data['part_code'] = comp.part_code
    if 'category_id' not in data:
        data['category_id'] = comp.category_id
    if 'product_group_id' not in data:
        data['product_group_id'] = comp.product_group_id
    if 'default_inspection_type' not in data:
        data['default_inspection_type'] = comp.default_inspection_type

    errors = validate_component_refs(data, component_id=id)
    if errors:
        return validation_error(errors)
    update_component(comp, data)
    db.session.commit()
    return success_response(data=_serialize_component(comp, full=True), message='Component updated')


@component_bp.route('/components/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_comp(id):
    comp = ComponentMaster.query.filter_by(id=id, is_deleted=False).first()
    if not comp:
        return error_response('Component not found', 404)
    from datetime import datetime, timezone
    comp.is_deleted = True
    comp.deleted_at = datetime.now(timezone.utc)
    comp.deleted_by = g.current_user.get('user_name')
    comp.status = 'inactive'
    AuditLog.log('qc_component_master', comp.id, 'DELETE')
    db.session.commit()
    return success_response(message='Component deleted')


@component_bp.route('/components/<int:id>/duplicate', methods=['POST'])
@token_required
@role_required('admin')
def duplicate_comp(id):
    comp = ComponentMaster.query.filter_by(id=id, is_deleted=False).first()
    if not comp:
        return error_response('Component not found', 404)
    # Generate new part_code
    new_code = f'{comp.part_code}-COPY'
    suffix = 2
    while ComponentMaster.query.filter_by(part_code=new_code, is_deleted=False).first():
        new_code = f'{comp.part_code}-COPY-{suffix}'
        suffix += 1

    new_comp = ComponentMaster(
        part_code=new_code, part_name=f'{comp.part_name} (Copy)',
        part_description=comp.part_description, category_id=comp.category_id,
        product_group_id=comp.product_group_id, qc_required=comp.qc_required,
        qc_plan_id=comp.qc_plan_id, default_inspection_type=comp.default_inspection_type,
        default_sampling_plan_id=comp.default_sampling_plan_id,
        test_cert_required=comp.test_cert_required, spec_required=comp.spec_required,
        fqir_required=comp.fqir_required, coc_required=comp.coc_required,
        pr_process_code=comp.pr_process_code, pr_process_name=comp.pr_process_name,
        skip_lot_enabled=comp.skip_lot_enabled,
        skip_lot_count=comp.skip_lot_count, skip_lot_threshold=comp.skip_lot_threshold,
        department_id=comp.department_id, primary_vendor_id=comp.primary_vendor_id,
        status='draft', created_by=g.current_user.get('user_name'))
    db.session.add(new_comp)
    db.session.flush()

    # Copy checking params
    for p in comp.checking_params.filter_by(is_active=True).all():
        db.session.add(ComponentCheckingParam(
            component_id=new_comp.id, checking_type=p.checking_type,
            checking_point=p.checking_point, specification=p.specification,
            unit_id=p.unit_id, unit_code=p.unit_code,
            nominal_value=p.nominal_value, tolerance_min=p.tolerance_min,
            tolerance_max=p.tolerance_max, instrument_id=p.instrument_id,
            instrument_name=p.instrument_name, input_type=p.input_type,
            sort_order=p.sort_order, is_mandatory=p.is_mandatory))
    for s in comp.specifications.all():
        db.session.add(ComponentSpecification(
            component_id=new_comp.id, spec_key=s.spec_key, spec_value=s.spec_value, sort_order=s.sort_order))
    for cv in comp.component_vendors.all():
        db.session.add(ComponentVendor(
            component_id=new_comp.id, vendor_id=cv.vendor_id,
            is_primary=cv.is_primary, unit_price=cv.unit_price, lead_time_days=cv.lead_time_days))
    db.session.commit()
    return success_response(data=_serialize_component(new_comp, full=True), message='Component duplicated', status_code=201)


@component_bp.route('/components/validate-part-code', methods=['GET'])
@token_required
def validate_part_code():
    part_code = request.args.get('part_code', '').strip().upper()
    if not part_code:
        return error_response('part_code parameter required', 400)
    exists = ComponentMaster.query.filter(
        db.func.lower(ComponentMaster.part_code) == part_code.lower(),
        ComponentMaster.is_deleted == False).first() is not None
    return success_response(data={
        'available': not exists,
        'message': f'Part code {part_code} {"already exists" if exists else "is available"}'
    })


@component_bp.route('/components/upload-document', methods=['POST'])
@token_required
@role_required('admin')
def upload_document():
    component_id = request.form.get('component_id')
    document_type = request.form.get('document_type')
    file = request.files.get('file')
    if not all([component_id, document_type, file]):
        return error_response('component_id, document_type, and file are required', 400)
    comp = ComponentMaster.query.filter_by(id=int(component_id), is_deleted=False).first()
    if not comp:
        return error_response('Component not found', 404)
    valid_types = ['drawing', 'test_cert', 'fqir', 'coc', 'specification', 'other', 'spec_sheet']
    if document_type not in valid_types:
        return error_response(f'Invalid document_type. Must be one of: {", ".join(valid_types)}', 400)
    # File validation
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'jpg', 'jpeg', 'png', 'xlsx', 'docx'})
    if ext not in allowed:
        return error_response(f'File type .{ext} not allowed', 400)
    # Save locally
    upload_dir = os.path.join(current_app.config['UPLOAD_DIR'], 'components', str(component_id))
    os.makedirs(upload_dir, exist_ok=True)
    stored_name = f'{uuid4().hex}_{filename}'
    filepath = os.path.join(upload_dir, stored_name)
    file.save(filepath)
    file_size = os.path.getsize(filepath)

    doc = ComponentDocument(
        component_id=int(component_id), document_type=document_type,
        file_name=stored_name, original_name=file.filename,
        file_path=filepath, file_size=file_size,
        mime_type=file.content_type, uploaded_by=g.current_user.get('user_name'))
    db.session.add(doc)
    db.session.commit()
    return success_response(data={
        'id': doc.id, 'component_id': doc.component_id, 'document_type': doc.document_type,
        'file_name': doc.original_name, 'file_path': doc.file_path,
        'file_size': doc.file_size, 'mime_type': doc.mime_type,
        'uploaded_by': doc.uploaded_by,
        'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None,
    }, message='Document uploaded', status_code=201)


@component_bp.route('/components/documents/<int:doc_id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_document(doc_id):
    doc = ComponentDocument.query.get_or_404(doc_id, description='Document not found')
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    db.session.delete(doc)
    db.session.commit()
    return success_response(message='Document deleted')


@component_bp.route('/components/export', methods=['POST'])
@token_required
@role_required('admin', 'checker')
def export_components():
    from openpyxl import Workbook
    from io import BytesIO
    from flask import send_file

    filters = request.get_json() or {}
    query = ComponentMaster.query.filter_by(is_deleted=False)
    if filters.get('category_id'):
        query = query.filter_by(category_id=filters['category_id'])
    if filters.get('status'):
        query = query.filter_by(status=filters['status'])
    if filters.get('qc_required') is not None:
        query = query.filter_by(qc_required=filters['qc_required'])

    components = query.order_by(ComponentMaster.part_code).all()
    wb = Workbook()
    ws = wb.active
    ws.title = 'Components'
    headers = ['Component Code', 'Part Code', 'Part Name', 'Category', 'Group',
               'QC Required', 'Inspection Type', 'QC Plan', 'Status']
    ws.append(headers)
    for c in components:
        ws.append([
            c.component_code, c.part_code, c.part_name,
            c.category.category_name if c.category else '',
            c.product_group.group_name if c.product_group else '',
            'Yes' if c.qc_required else 'No',
            c.default_inspection_type,
            c.qc_plan.plan_code if c.qc_plan else '',
            c.status])
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='components_export.xlsx')
