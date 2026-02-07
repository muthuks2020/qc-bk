from marshmallow import Schema, fields, validate, validates_schema, ValidationError, pre_load
from app.utils.validators import sanitize_string


class QCPlanParameterSchema(Schema):
    id = fields.Int(dump_only=True)
    parameter_code = fields.Str(validate=validate.Length(max=50), load_default=None)
    parameter_name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    parameter_sequence = fields.Int(load_default=0)
    checking_type = fields.Str(required=True, validate=validate.OneOf([
        'visual', 'functional', 'dimensional', 'electrical', 'weight'
    ]))
    specification = fields.Str(validate=validate.Length(max=500), load_default=None)
    unit_id = fields.Int(load_default=None, allow_none=True)
    nominal_value = fields.Decimal(load_default=None, allow_none=True, as_string=True)
    tolerance_min = fields.Decimal(load_default=None, allow_none=True, as_string=True)
    tolerance_max = fields.Decimal(load_default=None, allow_none=True, as_string=True)
    instrument_id = fields.Int(load_default=None, allow_none=True)
    input_type = fields.Str(load_default='measurement', validate=validate.OneOf([
        'measurement', 'pass_fail', 'yes_no', 'text'
    ]))
    is_mandatory = fields.Bool(load_default=True)
    acceptance_criteria = fields.Str(validate=validate.Length(max=500), load_default=None)
    is_active = fields.Bool(dump_only=True)

    # Response-only
    unit = fields.Dict(dump_only=True)
    instrument = fields.Dict(dump_only=True)

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('parameter_name', 'parameter_code', 'specification', 'acceptance_criteria'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        return data


class QCPlanStageSchema(Schema):
    id = fields.Int(dump_only=True)
    stage_code = fields.Str(validate=validate.Length(max=50), load_default=None)
    stage_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    stage_type = fields.Str(required=True, validate=validate.OneOf(['visual', 'functional']))
    stage_sequence = fields.Int(required=True, validate=validate.Range(min=1))
    inspection_type = fields.Str(load_default='sampling', validate=validate.OneOf([
        'sampling', '100_percent'
    ]))
    sampling_plan_id = fields.Int(load_default=None, allow_none=True)
    is_mandatory = fields.Bool(load_default=True)
    requires_instrument = fields.Bool(load_default=False)
    is_active = fields.Bool(dump_only=True)

    parameters = fields.List(fields.Nested(QCPlanParameterSchema), load_default=[])

    # Response-only
    sampling_plan = fields.Dict(dump_only=True)
    parameters_count = fields.Int(dump_only=True)

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('stage_code', 'stage_name'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        return data


class QCPlanSchema(Schema):
    id = fields.Int(dump_only=True)
    plan_code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    plan_name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    plan_type = fields.Str(load_default='standard', validate=validate.OneOf(['standard', 'custom']))
    revision = fields.Str(validate=validate.Length(max=50), load_default=None)
    revision_date = fields.Date(load_default=None, allow_none=True)
    effective_date = fields.Date(load_default=None, allow_none=True)
    requires_visual = fields.Bool(load_default=True)
    requires_functional = fields.Bool(load_default=False)
    document_number = fields.Str(validate=validate.Length(max=100), load_default=None)
    status = fields.Str(dump_only=True)
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    stages = fields.List(fields.Nested(QCPlanStageSchema), load_default=[])

    # Response-only
    stages_count = fields.Int(dump_only=True)
    parameters_count = fields.Int(dump_only=True)
    components_using = fields.Int(dump_only=True)

    @pre_load
    def sanitize(self, data, **kwargs):
        for key in ('plan_code', 'plan_name', 'revision', 'document_number'):
            if key in data and data[key]:
                data[key] = sanitize_string(data[key])
        return data

    @validates_schema
    def validate_stages(self, data, **kwargs):
        stages = data.get('stages', [])
        if not stages:
            return

        errors = []
        sequences = []
        has_visual = False
        has_functional = False

        for i, stage in enumerate(stages):
            seq = stage.get('stage_sequence')
            if seq in sequences:
                errors.append({'field': f'stages[{i}].stage_sequence',
                               'message': f'Duplicate stage_sequence: {seq}'})
            sequences.append(seq)

            if stage.get('stage_type') == 'visual':
                has_visual = True
            if stage.get('stage_type') == 'functional':
                has_functional = True

        if data.get('requires_visual') and not has_visual:
            errors.append({'field': 'stages',
                           'message': 'At least one visual stage required when requires_visual=true'})
        if data.get('requires_functional') and not has_functional:
            errors.append({'field': 'stages',
                           'message': 'At least one functional stage required when requires_functional=true'})

        if errors:
            raise ValidationError(errors)
