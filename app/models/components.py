from app.extensions import db
from datetime import datetime, timezone


class ComponentMaster(db.Model):
    __tablename__ = 'qc_component_master'

    id = db.Column(db.Integer, primary_key=True)
    component_code = db.Column(db.String(50), unique=True, nullable=False)
    part_code = db.Column(db.String(100), unique=True, nullable=False)
    part_name = db.Column(db.String(300), nullable=False)
    part_description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('qc_product_categories.id'))
    product_group_id = db.Column(db.Integer, db.ForeignKey('qc_product_groups.id'))
    qc_required = db.Column(db.Boolean, default=True)
    qc_plan_id = db.Column(db.Integer, db.ForeignKey('qc_plans.id'))
    default_inspection_type = db.Column(db.String(20), default='sampling')
    default_sampling_plan_id = db.Column(db.Integer, db.ForeignKey('qc_sampling_plans.id'))
    drawing_no = db.Column(db.String(100))
    drawing_revision = db.Column(db.String(20))
    test_cert_required = db.Column(db.Boolean, default=False)
    spec_required = db.Column(db.Boolean, default=False)
    fqir_required = db.Column(db.Boolean, default=False)
    coc_required = db.Column(db.Boolean, default=False)
    pr_process_code = db.Column(db.String(50))
    pr_process_name = db.Column(db.String(200))
    lead_time_days = db.Column(db.Integer)
    primary_vendor_id = db.Column(db.Integer, db.ForeignKey('qc_vendors.id'))
    odoo_product_id = db.Column(db.Integer)
    odoo_product_tmpl_id = db.Column(db.Integer)
    skip_lot_enabled = db.Column(db.Boolean, default=False)
    skip_lot_count = db.Column(db.Integer, default=0)
    skip_lot_threshold = db.Column(db.Integer, default=5)
    status = db.Column(db.String(20), default='draft')
    department_id = db.Column(db.Integer, db.ForeignKey('qc_departments.id'))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.String(100))
    updated_by = db.Column(db.String(100))
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime(timezone=True))
    deleted_by = db.Column(db.String(100))

    # Relationships
    category = db.relationship('ProductCategory', backref='components', lazy='joined')
    product_group = db.relationship('ProductGroup', backref='components', lazy='joined')
    qc_plan = db.relationship('QCPlan', backref='components', lazy='joined')
    sampling_plan = db.relationship('SamplingPlan', backref='components', lazy='joined')
    primary_vendor = db.relationship('Vendor', backref='primary_components', lazy='joined')
    dept = db.relationship('Department', backref='components', lazy='joined')

    checking_params = db.relationship('ComponentCheckingParam', backref='component',
                                      lazy='dynamic', cascade='all, delete-orphan',
                                      order_by='ComponentCheckingParam.sort_order')
    specifications = db.relationship('ComponentSpecification', backref='component',
                                     lazy='dynamic', cascade='all, delete-orphan',
                                     order_by='ComponentSpecification.sort_order')
    documents = db.relationship('ComponentDocument', backref='component',
                                lazy='dynamic', cascade='all, delete-orphan')
    component_vendors = db.relationship('ComponentVendor', backref='component',
                                        lazy='dynamic', cascade='all, delete-orphan')


class ComponentCheckingParam(db.Model):
    __tablename__ = 'qc_component_checking_params'

    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey('qc_component_master.id', ondelete='CASCADE'), nullable=False)
    qc_plan_stage_id = db.Column(db.Integer, db.ForeignKey('qc_plan_stages.id'))
    checking_type = db.Column(db.String(20), nullable=False)
    checking_point = db.Column(db.String(200), nullable=False)
    specification = db.Column(db.String(500))
    unit_id = db.Column(db.Integer, db.ForeignKey('qc_units.id'))
    unit_code = db.Column(db.String(20))
    nominal_value = db.Column(db.Numeric(15, 4))
    tolerance_min = db.Column(db.Numeric(15, 4))
    tolerance_max = db.Column(db.Numeric(15, 4))
    instrument_id = db.Column(db.Integer, db.ForeignKey('qc_instruments.id'))
    instrument_name = db.Column(db.String(200))
    input_type = db.Column(db.String(20), default='measurement')
    sort_order = db.Column(db.Integer, default=0)
    is_mandatory = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    unit = db.relationship('Unit', lazy='joined')
    instrument = db.relationship('Instrument', lazy='joined')


class ComponentSpecification(db.Model):
    __tablename__ = 'qc_component_specifications'

    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey('qc_component_master.id', ondelete='CASCADE'), nullable=False)
    spec_key = db.Column(db.String(100), nullable=False)
    spec_value = db.Column(db.String(500))
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ComponentDocument(db.Model):
    __tablename__ = 'qc_component_documents'

    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey('qc_component_master.id', ondelete='CASCADE'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    file_name = db.Column(db.String(300), nullable=False)
    original_name = db.Column(db.String(300))
    file_path = db.Column(db.String(500))
    file_url = db.Column(db.String(500))
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    version = db.Column(db.String(20), default='1.0')
    is_current = db.Column(db.Boolean, default=True)
    uploaded_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    uploaded_by = db.Column(db.String(100))


class ComponentVendor(db.Model):
    __tablename__ = 'qc_component_vendors'

    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey('qc_component_master.id', ondelete='CASCADE'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('qc_vendors.id', ondelete='CASCADE'), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    approval_date = db.Column(db.Date)
    vendor_part_code = db.Column(db.String(100))
    unit_price = db.Column(db.Numeric(15, 2))
    currency = db.Column(db.String(10), default='INR')
    lead_time_days = db.Column(db.Integer)
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    vendor = db.relationship('Vendor', lazy='joined')
