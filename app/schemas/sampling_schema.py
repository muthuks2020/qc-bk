from marshmallow import Schema, fields, validate, validates_schema, ValidationError, pre_load
from app.utils.validators import sanitize_string


class SamplingPlanDetailSchema(Schema):
    id = fields.Int(dump_only=True)
    lot_size_min = fields.Int(required=True, validate=validate.Range(min=0))
    lot_size_max = fields.Int(required=True, validate=validate.Range(min=1))
    sample_size = fields.Int(required=True, validate=validate.Range(min=1))
    accept_number = fields.Int(required=True, validate=validate.Range(min=0))
    reject_number = fields.Int(required=True, validate=validate.Range(min=1))

    @validates_schema
    def validate_row(self, data, **kwargs):
        if data.get('lot_size_max') is not None and data.get('lot_size_min') is not None:
            if data['lot_size_max'] <= data['lot_size_min']:
                raise ValidationError('lot_size_max must be > lot_size_min', 'lot_size_max')
        if data.get('reject_number') is not None and data.get('accept_number') is not None:
            if data['reject_number'] <= data['accept_number']:
                raise ValidationError('reject_number must be > accept_number', 'reject_number')


class SamplingPlanSchema(Schema):
    id = fields.Int(dump_only=True)
    plan_code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    plan_name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    plan_type = fields.Str(load_default='aql_based', validate=validate.OneOf([
        'aql_based', 'fixed', 'custom',                      # Postman / frontend values
        'normal', 'tightened', 'reduced',                     # Legacy values
        'sp0', 'sp1', 'sp2', 'sp3'                           # DB comment values
    ]))
    aql_level = fields.Str(validate=validate.Length(max=50), load_default=None)
    inspection_level = fields.Str(validate=validate.Length(max=50), load_default=None)
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    # Nested
    details = fields.List(fields.Nested(SamplingPlanDetailSchema), load_default=[])
    details_count = fields.Int(dump_only=True)
    referenced_by_components = fields.Int(dump_only=True)

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('plan_code', 'plan_name', 'aql_level', 'inspection_level'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        return data
