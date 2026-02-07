from app.extensions import db
from datetime import datetime, timezone


class SamplingPlan(db.Model):
    __tablename__ = 'qc_sampling_plans'

    id = db.Column(db.Integer, primary_key=True)
    plan_code = db.Column(db.String(50), unique=True, nullable=False)
    plan_name = db.Column(db.String(200), nullable=False)
    plan_type = db.Column(db.String(20))
    aql_level = db.Column(db.String(50))
    inspection_level = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    details = db.relationship('SamplingPlanDetail', backref='sampling_plan',
                              lazy='dynamic', cascade='all, delete-orphan',
                              order_by='SamplingPlanDetail.lot_size_min')


class SamplingPlanDetail(db.Model):
    __tablename__ = 'qc_sampling_plan_details'

    id = db.Column(db.Integer, primary_key=True)
    sampling_plan_id = db.Column(db.Integer, db.ForeignKey('qc_sampling_plans.id', ondelete='CASCADE'), nullable=False)
    lot_size_min = db.Column(db.Integer, nullable=False)
    lot_size_max = db.Column(db.Integer, nullable=False)
    sample_size = db.Column(db.Integer, nullable=False)
    accept_number = db.Column(db.Integer, nullable=False)
    reject_number = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
