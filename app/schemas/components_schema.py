from marshmallow import Schema, fields, validate, validates_schema, ValidationError, pre_load
from app.utils.validators import sanitize_string


class CheckingParamSchema(Schema):
    id = fields.Int(dump_only=True)
    checking_type = fields.Str(required=True, validate=validate.OneOf(['visual', 'functional']))
    checking_point = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    specification = fields.Str(validate=validate.Length(max=500), load_default=None)
    unit_id = fields.Int(load_default=None, allow_none=True)
    unit_code = fields.Str(load_default=None, allow_none=True)
    nominal_value = fields.Decimal(load_default=None, allow_none=True, as_string=True)
    tolerance_min = fields.Decimal(load_default=None, allow_none=True, as_string=True)
    tolerance_max = fields.Decimal(load_default=None, allow_none=True, as_string=True)
    instrument_id = fields.Int(load_default=None, allow_none=True)
    instrument_name = fields.Str(load_default=None, allow_none=True)
    input_type = fields.Str(load_default='measurement', validate=validate.OneOf([
        'measurement', 'pass_fail', 'yes_no', 'text'
    ]))
    sort_order = fields.Int(load_default=0)
    is_mandatory = fields.Bool(load_default=True)
    is_active = fields.Bool(load_default=True)

    # Response-only
    unit = fields.Dict(dump_only=True)
    instrument = fields.Dict(dump_only=True)

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('checking_point', 'specification', 'instrument_name'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        return data


class SpecificationSchema(Schema):
    id = fields.Int(dump_only=True)
    spec_key = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    spec_value = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    sort_order = fields.Int(load_default=0)

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('spec_key', 'spec_value'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        return data


class ComponentVendorSchema(Schema):
    id = fields.Int(dump_only=True)
    vendor_id = fields.Int(required=True)
    is_primary = fields.Bool(load_default=False)
    is_approved = fields.Bool(load_default=False)
    vendor_part_code = fields.Str(validate=validate.Length(max=100), load_default=None)
    unit_price = fields.Decimal(load_default=None, allow_none=True, as_string=True)
    lead_time_days = fields.Int(load_default=None, allow_none=True)
    remarks = fields.Str(validate=validate.Length(max=1000), load_default=None)

    # Response-only
    vendor = fields.Dict(dump_only=True)


class ComponentSchema(Schema):
    id = fields.Int(dump_only=True)
    component_code = fields.Str(dump_only=True)  # Auto-generated
    part_code = fields.Str(required=True, validate=[
        validate.Length(min=1, max=100),
        validate.Regexp(r'^[A-Za-z0-9\-]+$', error='Only alphanumeric and hyphens allowed')
    ])
    part_name = fields.Str(required=True, validate=validate.Length(min=1, max=300))
    part_description = fields.Str(validate=validate.Length(max=5000), load_default=None)
    category_id = fields.Int(required=True)
    product_group_id = fields.Int(required=True)
    qc_required = fields.Bool(load_default=True)
    qc_plan_id = fields.Int(load_default=None, allow_none=True)
    default_inspection_type = fields.Str(required=True, validate=validate.OneOf([
        'sampling', '100_percent'
    ]))
    default_sampling_plan_id = fields.Int(load_default=None, allow_none=True)
    drawing_no = fields.Str(validate=validate.Length(max=100), load_default=None)
    drawing_revision = fields.Str(validate=validate.Length(max=20), load_default=None)
    test_cert_required = fields.Bool(load_default=False)
    spec_required = fields.Bool(load_default=False)
    fqir_required = fields.Bool(load_default=False)
    coc_required = fields.Bool(load_default=False)
    pr_process_code = fields.Str(load_default=None, allow_none=True, validate=validate.OneOf([
        'direct_purchase', 'subcontract', 'in_house', 'external_job', 'internal_job', None
    ]))
    pr_process_name = fields.Str(validate=validate.Length(max=200), load_default=None)
    skip_lot_enabled = fields.Bool(load_default=False)
    skip_lot_count = fields.Int(load_default=None, allow_none=True)
    skip_lot_threshold = fields.Int(load_default=None, allow_none=True)
    department_id = fields.Int(load_default=None, allow_none=True)
    primary_vendor_id = fields.Int(load_default=None, allow_none=True)
    odoo_product_id = fields.Int(load_default=None, allow_none=True)
    lead_time_days = fields.Int(load_default=None, allow_none=True)
    status = fields.Str(dump_only=True)
    is_deleted = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    created_by = fields.Str(dump_only=True)
    updated_by = fields.Str(dump_only=True)

    # Nested for create/update
    checking_parameters = fields.List(fields.Nested(CheckingParamSchema), load_default=[])
    specifications = fields.List(fields.Nested(SpecificationSchema), load_default=[])
    approved_vendors = fields.List(fields.Nested(ComponentVendorSchema), load_default=[])

    # Response-only
    category = fields.Dict(dump_only=True)
    group = fields.Dict(dump_only=True)
    qc_plan = fields.Dict(dump_only=True)
    sampling_plan = fields.Dict(dump_only=True)
    primary_vendor = fields.Dict(dump_only=True)
    department = fields.Dict(dump_only=True)
    checking_params_count = fields.Int(dump_only=True)
    specifications_count = fields.Int(dump_only=True)
    documents_count = fields.Int(dump_only=True)
    vendors_count = fields.Int(dump_only=True)

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('part_code', 'part_name', 'part_description', 'drawing_no', 'pr_process_name'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        if data.get('part_code'):
            data['part_code'] = data['part_code'].upper().strip()
        return data

    @validates_schema
    def validate_component(self, data, **kwargs):
        errors = []

        # Sampling plan required if inspection_type is sampling
        if data.get('default_inspection_type') == 'sampling' and not data.get('default_sampling_plan_id'):
            errors.append({'field': 'default_sampling_plan_id',
                           'message': 'Sampling plan required when inspection_type is sampling'})

        if data.get('default_inspection_type') == '100_percent' and data.get('default_sampling_plan_id'):
            errors.append({'field': 'default_sampling_plan_id',
                           'message': 'Sampling plan must be null for 100_percent inspection'})

        # Skip lot validation
        if data.get('skip_lot_enabled'):
            if not data.get('skip_lot_count') or data['skip_lot_count'] < 1:
                errors.append({'field': 'skip_lot_count',
                               'message': 'Required when skip_lot_enabled is true (min 1)'})
            if not data.get('skip_lot_threshold') or data['skip_lot_threshold'] < 1:
                errors.append({'field': 'skip_lot_threshold',
                               'message': 'Required when skip_lot_enabled is true (min 1)'})

        # Validate checking params tolerances
        for i, param in enumerate(data.get('checking_parameters', [])):
            nom = param.get('nominal_value')
            tmin = param.get('tolerance_min')
            tmax = param.get('tolerance_max')
            if tmin is not None and tmax is not None and tmin >= tmax:
                errors.append({'field': f'checking_parameters[{i}].tolerance_min',
                               'message': 'tolerance_min must be < tolerance_max'})
            if nom is not None and tmin is not None and tmax is not None:
                if not (tmin < nom < tmax):
                    errors.append({'field': f'checking_parameters[{i}].nominal_value',
                                   'message': 'nominal_value must be between tolerance_min and tolerance_max'})

        # Validate no duplicate spec keys
        spec_keys = [s.get('spec_key') for s in data.get('specifications', [])]
        if len(spec_keys) != len(set(spec_keys)):
            errors.append({'field': 'specifications', 'message': 'Duplicate spec_key found'})

        # Validate no duplicate vendor_ids
        vendor_ids = [v.get('vendor_id') for v in data.get('approved_vendors', [])]
        if len(vendor_ids) != len(set(vendor_ids)):
            errors.append({'field': 'approved_vendors', 'message': 'Duplicate vendor_id found'})

        if errors:
            raise ValidationError(errors)
