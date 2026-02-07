from marshmallow import Schema, fields, validate, validates_schema, ValidationError, pre_load
from app.utils.validators import sanitize_string


class DepartmentSchema(Schema):
    id = fields.Int(dump_only=True)
    department_code = fields.Str(required=True, validate=[
        validate.Length(min=1, max=50),
        validate.Regexp(r'^[A-Za-z0-9\-]+$', error='Only alphanumeric and hyphens allowed')
    ])
    department_name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    pass_source_location = fields.Str(validate=validate.Length(max=200), load_default=None)
    pass_source_location_odoo_id = fields.Int(load_default=None, allow_none=True)
    pass_destination_location = fields.Str(validate=validate.Length(max=200), load_default=None)
    pass_destination_location_odoo_id = fields.Int(load_default=None, allow_none=True)
    fail_source_location = fields.Str(validate=validate.Length(max=200), load_default=None)
    fail_source_location_odoo_id = fields.Int(load_default=None, allow_none=True)
    fail_destination_location = fields.Str(validate=validate.Length(max=200), load_default=None)
    fail_destination_location_odoo_id = fields.Int(load_default=None, allow_none=True)
    manager_id = fields.Int(load_default=None, allow_none=True)
    description = fields.Str(validate=validate.Length(max=2000), load_default=None)
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    manager = fields.Dict(dump_only=True)
    users_count = fields.Int(dump_only=True)

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('department_code', 'department_name', 'description',
                     'pass_source_location', 'pass_destination_location',
                     'fail_source_location', 'fail_destination_location'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        return data


class CategorySchema(Schema):
    id = fields.Int(dump_only=True)
    category_code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    category_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    icon = fields.Str(validate=validate.Length(max=20), load_default=None)
    description = fields.Str(validate=validate.Length(max=500), load_default=None)
    sort_order = fields.Int(load_default=0)
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    groups_count = fields.Int(dump_only=True)
    components_count = fields.Int(dump_only=True)
    groups = fields.List(fields.Dict(), dump_only=True)

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('category_code', 'category_name', 'description'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        return data


class ProductGroupSchema(Schema):
    id = fields.Int(dump_only=True)
    category_id = fields.Int(dump_only=True)
    group_code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    group_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    description = fields.Str(validate=validate.Length(max=500), load_default=None)
    sort_order = fields.Int(load_default=0)
    is_active = fields.Bool(dump_only=True)
    components_count = fields.Int(dump_only=True)

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('group_code', 'group_name', 'description'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        return data


class UnitSchema(Schema):
    id = fields.Int(dump_only=True)
    unit_code = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    unit_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    unit_symbol = fields.Str(validate=validate.Length(max=20), load_default=None)
    unit_type = fields.Str(required=True, validate=validate.OneOf([
        'length', 'weight', 'electrical', 'frequency', 'percentage',
        'temperature', 'count', 'volume', 'pressure', 'time', 'angle', 'ratio'
    ]))
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('unit_code', 'unit_name', 'unit_symbol'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        return data


class InstrumentSchema(Schema):
    id = fields.Int(dump_only=True)
    instrument_code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    instrument_name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    instrument_type = fields.Str(validate=validate.Length(max=100), load_default=None)
    make = fields.Str(validate=validate.Length(max=100), load_default=None)
    model = fields.Str(validate=validate.Length(max=100), load_default=None)
    serial_number = fields.Str(validate=validate.Length(max=100), load_default=None)
    calibration_frequency_days = fields.Int(required=True, validate=validate.Range(min=1, max=3650))
    last_calibration_date = fields.Date(required=True)
    calibration_due_date = fields.Date(required=True)
    calibration_certificate_no = fields.Str(validate=validate.Length(max=100), load_default=None)
    location = fields.Str(validate=validate.Length(max=200), load_default=None)
    department_id = fields.Int(load_default=None, allow_none=True)
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    calibration_status = fields.Str(dump_only=True)
    days_until_due = fields.Int(dump_only=True)
    department = fields.Dict(dump_only=True)

    @validates_schema
    def validate_dates(self, data, **kwargs):
        from datetime import date
        last_cal = data.get('last_calibration_date')
        due_date = data.get('calibration_due_date')
        if last_cal and last_cal > date.today():
            raise ValidationError('Cannot be in the future', 'last_calibration_date')
        if last_cal and due_date and due_date <= last_cal:
            raise ValidationError('Must be after last calibration date', 'calibration_due_date')

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('instrument_code', 'instrument_name', 'instrument_type', 'make', 'model', 'serial_number'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        return data


class VendorSchema(Schema):
    id = fields.Int(dump_only=True)
    vendor_code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    vendor_name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    vendor_type = fields.Str(load_default='supplier', validate=validate.Length(max=50))
    contact_person = fields.Str(validate=validate.Length(max=100), load_default=None)
    email = fields.Str(validate=validate.Length(max=200), load_default=None)
    phone = fields.Str(validate=validate.Length(max=50), load_default=None)
    mobile = fields.Str(validate=validate.Length(max=50), load_default=None)
    address_line1 = fields.Str(validate=validate.Length(max=500), load_default=None)
    address_line2 = fields.Str(validate=validate.Length(max=500), load_default=None)
    city = fields.Str(validate=validate.Length(max=100), load_default=None)
    state = fields.Str(validate=validate.Length(max=100), load_default=None)
    country = fields.Str(validate=validate.Length(max=100), load_default='India')
    pincode = fields.Str(validate=validate.Length(max=20), load_default=None)
    gst_number = fields.Str(validate=validate.Length(max=50), load_default=None)
    pan_number = fields.Str(validate=validate.Length(max=20), load_default=None)
    is_approved = fields.Bool(load_default=False)
    odoo_partner_id = fields.Int(load_default=None, allow_none=True)
    is_active = fields.Bool(dump_only=True)
    quality_rating = fields.Float(dump_only=True)
    delivery_rating = fields.Float(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    components_count = fields.Int(dump_only=True)

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('vendor_code', 'vendor_name', 'contact_person', 'email', 'city', 'state'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        if data.get('gst_number'):
            data['gst_number'] = data['gst_number'].upper().strip()
        if data.get('pan_number'):
            data['pan_number'] = data['pan_number'].upper().strip()
        return data


class DefectTypeSchema(Schema):
    id = fields.Int(dump_only=True)
    defect_code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    defect_name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    defect_category = fields.Str(validate=validate.Length(max=50), load_default=None)
    severity_level = fields.Int(required=True, validate=validate.OneOf([1, 2, 3]))
    description = fields.Str(validate=validate.Length(max=1000), load_default=None)
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('defect_code', 'defect_name', 'description', 'defect_category'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        return data


class RejectionReasonSchema(Schema):
    id = fields.Int(dump_only=True)
    reason_code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    reason_name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    reason_category = fields.Str(validate=validate.Length(max=50), load_default=None)
    description = fields.Str(validate=validate.Length(max=1000), load_default=None)
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('reason_code', 'reason_name', 'description', 'reason_category'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        return data


class LocationSchema(Schema):
    id = fields.Int(dump_only=True)
    location_code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    location_name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    location_type = fields.Str(required=True, validate=validate.OneOf([
        'store', 'quarantine', 'vendor', 'production', 'scrap',
        'qc_area', 'rejection_area', 'warehouse', 'gate', 'receiving'
    ]))
    parent_location_id = fields.Int(load_default=None, allow_none=True)
    warehouse_name = fields.Str(validate=validate.Length(max=200), load_default=None)
    odoo_location_id = fields.Int(load_default=None, allow_none=True)
    is_quarantine = fields.Bool(load_default=False)
    is_restricted = fields.Bool(load_default=False)
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('location_code', 'location_name', 'warehouse_name'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        if data.get('location_type') == 'quarantine':
            data['is_quarantine'] = True
        return data


class SystemConfigSchema(Schema):
    id = fields.Int(dump_only=True)
    config_key = fields.Str(dump_only=True)
    config_value = fields.Str(required=True)
    config_type = fields.Str(validate=validate.OneOf(['string', 'number', 'boolean', 'json']),
                             load_default='string')
    module = fields.Str(dump_only=True)
    description = fields.Str(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    updated_by = fields.Str(dump_only=True)
