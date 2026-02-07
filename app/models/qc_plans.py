from app.extensions import db
from datetime import datetime, timezone


class QCPlan(db.Model):
    __tablename__ = 'qc_plans'

    id = db.Column(db.Integer, primary_key=True)
    plan_code = db.Column(db.String(50), unique=True, nullable=False)
    plan_name = db.Column(db.String(200), nullable=False)
    revision = db.Column(db.String(20))
    revision_date = db.Column(db.Date)
    effective_date = db.Column(db.Date)
    plan_type = db.Column(db.String(50), default='standard')
    inspection_stages = db.Column(db.Integer, default=1)
    requires_visual = db.Column(db.Boolean, default=True)
    requires_functional = db.Column(db.Boolean, default=False)
    document_number = db.Column(db.String(100))
    document_path = db.Column(db.String(500))
    approved_by = db.Column(db.String(100))
    approved_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='draft')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    stages = db.relationship('QCPlanStage', backref='qc_plan',
                             lazy='dynamic', cascade='all, delete-orphan',
                             order_by='QCPlanStage.stage_sequence')


class QCPlanStage(db.Model):
    __tablename__ = 'qc_plan_stages'

    id = db.Column(db.Integer, primary_key=True)
    qc_plan_id = db.Column(db.Integer, db.ForeignKey('qc_plans.id', ondelete='CASCADE'), nullable=False)
    stage_code = db.Column(db.String(50), nullable=False)
    stage_name = db.Column(db.String(100), nullable=False)
    stage_type = db.Column(db.String(20), nullable=False)
    stage_sequence = db.Column(db.Integer, nullable=False)
    inspection_type = db.Column(db.String(20), default='sampling')
    sampling_plan_id = db.Column(db.Integer, db.ForeignKey('qc_sampling_plans.id'))
    is_mandatory = db.Column(db.Boolean, default=True)
    requires_instrument = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    parameters = db.relationship('QCPlanParameter', backref='stage',
                                 lazy='dynamic', cascade='all, delete-orphan',
                                 order_by='QCPlanParameter.parameter_sequence')
    sampling_plan = db.relationship('SamplingPlan', lazy='joined')


class QCPlanParameter(db.Model):
    __tablename__ = 'qc_plan_parameters'

    id = db.Column(db.Integer, primary_key=True)
    qc_plan_stage_id = db.Column(db.Integer, db.ForeignKey('qc_plan_stages.id', ondelete='CASCADE'), nullable=False)
    parameter_code = db.Column(db.String(50))
    parameter_name = db.Column(db.String(200), nullable=False)
    parameter_sequence = db.Column(db.Integer, default=0)
    checking_type = db.Column(db.String(20), nullable=False)
    specification = db.Column(db.Text)
    unit_id = db.Column(db.Integer, db.ForeignKey('qc_units.id'))
    nominal_value = db.Column(db.Numeric(15, 4))
    tolerance_min = db.Column(db.Numeric(15, 4))
    tolerance_max = db.Column(db.Numeric(15, 4))
    instrument_id = db.Column(db.Integer, db.ForeignKey('qc_instruments.id'))
    input_type = db.Column(db.String(20), default='measurement')
    is_mandatory = db.Column(db.Boolean, default=True)
    acceptance_criteria = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    unit = db.relationship('Unit', lazy='joined')
    instrument = db.relationship('Instrument', lazy='joined')


# Import for relationships
from app.models.sampling import SamplingPlan  # noqa: E402, F401
