from app.extensions import db
from datetime import datetime, timezone


class Department(db.Model):
    __tablename__ = 'qc_departments'

    id = db.Column(db.Integer, primary_key=True)
    department_code = db.Column(db.String(50), unique=True, nullable=False)
    department_name = db.Column(db.String(200), nullable=False)
    pass_source_location = db.Column(db.String(200))
    pass_source_location_odoo_id = db.Column(db.Integer)
    pass_destination_location = db.Column(db.String(200))
    pass_destination_location_odoo_id = db.Column(db.Integer)
    fail_source_location = db.Column(db.String(200))
    fail_source_location_odoo_id = db.Column(db.Integer)
    fail_destination_location = db.Column(db.String(200))
    fail_destination_location_odoo_id = db.Column(db.Integer)
    manager_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    users = db.relationship('User', backref='department', lazy='dynamic')


class User(db.Model):
    __tablename__ = 'qc_users'

    id = db.Column(db.Integer, primary_key=True)
    user_code = db.Column(db.String(50), unique=True, nullable=False)
    user_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    phone = db.Column(db.String(50))
    department_id = db.Column(db.Integer, db.ForeignKey('qc_departments.id'))
    designation = db.Column(db.String(100))
    employee_id = db.Column(db.String(50))
    office365_id = db.Column(db.String(200))
    password_hash = db.Column(db.String(500))
    avatar_url = db.Column(db.String(500))
    last_login_at = db.Column(db.DateTime(timezone=True))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user_roles = db.relationship('UserRole', backref='user', lazy='dynamic')


class Role(db.Model):
    __tablename__ = 'qc_roles'

    id = db.Column(db.Integer, primary_key=True)
    role_code = db.Column(db.String(50), unique=True, nullable=False)
    role_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_system_role = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class UserRole(db.Model):
    __tablename__ = 'qc_user_roles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('qc_users.id', ondelete='CASCADE'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('qc_roles.id', ondelete='CASCADE'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('qc_departments.id'))
    is_active = db.Column(db.Boolean, default=True)
    assigned_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    assigned_by = db.Column(db.String(100))

    role = db.relationship('Role', backref='user_roles', lazy='joined')


class Permission(db.Model):
    __tablename__ = 'qc_permissions'

    id = db.Column(db.Integer, primary_key=True)
    permission_code = db.Column(db.String(100), unique=True, nullable=False)
    permission_name = db.Column(db.String(200), nullable=False)
    module = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class RolePermission(db.Model):
    __tablename__ = 'qc_role_permissions'

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('qc_roles.id', ondelete='CASCADE'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('qc_permissions.id', ondelete='CASCADE'), nullable=False)
    can_create = db.Column(db.Boolean, default=False)
    can_read = db.Column(db.Boolean, default=True)
    can_update = db.Column(db.Boolean, default=False)
    can_delete = db.Column(db.Boolean, default=False)
    can_approve = db.Column(db.Boolean, default=False)


class UserProductAccess(db.Model):
    __tablename__ = 'qc_user_product_access'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('qc_users.id', ondelete='CASCADE'), nullable=False)
    component_id = db.Column(db.Integer)
    category_id = db.Column(db.Integer)
    access_type = db.Column(db.String(20), default='full')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SystemConfig(db.Model):
    __tablename__ = 'qc_system_config'

    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False)
    config_value = db.Column(db.Text, nullable=False)
    config_type = db.Column(db.String(20), default='string')
    module = db.Column(db.String(50))
    description = db.Column(db.Text)
    is_editable = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_by = db.Column(db.String(100))


class UserSession(db.Model):
    __tablename__ = 'qc_user_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('qc_users.id'), nullable=False)
    session_token = db.Column(db.String(500), nullable=False)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.Text)
    login_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    logout_at = db.Column(db.DateTime(timezone=True))
    is_active = db.Column(db.Boolean, default=True)


# ─── M2 Master Tables ───

class ProductCategory(db.Model):
    __tablename__ = 'qc_product_categories'

    id = db.Column(db.Integer, primary_key=True)
    category_code = db.Column(db.String(50), unique=True, nullable=False)
    category_name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(20))
    description = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.String(100))
    updated_by = db.Column(db.String(100))

    groups = db.relationship('ProductGroup', backref='category', lazy='dynamic')


class ProductGroup(db.Model):
    __tablename__ = 'qc_product_groups'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('qc_product_categories.id'), nullable=False)
    group_code = db.Column(db.String(50), unique=True, nullable=False)
    group_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Unit(db.Model):
    __tablename__ = 'qc_units'

    id = db.Column(db.Integer, primary_key=True)
    unit_code = db.Column(db.String(20), unique=True, nullable=False)
    unit_name = db.Column(db.String(100), nullable=False)
    unit_symbol = db.Column(db.String(20))
    unit_type = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Instrument(db.Model):
    __tablename__ = 'qc_instruments'

    id = db.Column(db.Integer, primary_key=True)
    instrument_code = db.Column(db.String(50), unique=True, nullable=False)
    instrument_name = db.Column(db.String(200), nullable=False)
    instrument_type = db.Column(db.String(100))
    make = db.Column(db.String(100))
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    calibration_due_date = db.Column(db.Date)
    calibration_frequency_days = db.Column(db.Integer, default=365)
    last_calibration_date = db.Column(db.Date)
    calibration_certificate_no = db.Column(db.String(100))
    location = db.Column(db.String(200))
    department_id = db.Column(db.Integer, db.ForeignKey('qc_departments.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    dept = db.relationship('Department', backref='instruments', lazy='joined')

    @property
    def calibration_status(self):
        from datetime import date
        if not self.calibration_due_date:
            return 'unknown'
        today = date.today()
        days = (self.calibration_due_date - today).days
        if days < 0:
            return 'overdue'
        elif days <= 30:
            return 'due_soon'
        return 'valid'

    @property
    def days_until_due(self):
        from datetime import date
        if not self.calibration_due_date:
            return None
        return (self.calibration_due_date - date.today()).days


class Vendor(db.Model):
    __tablename__ = 'qc_vendors'

    id = db.Column(db.Integer, primary_key=True)
    vendor_code = db.Column(db.String(50), unique=True, nullable=False)
    vendor_name = db.Column(db.String(200), nullable=False)
    vendor_type = db.Column(db.String(50), default='supplier')
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    mobile = db.Column(db.String(50))
    address_line1 = db.Column(db.Text)
    address_line2 = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100), default='India')
    pincode = db.Column(db.String(20))
    gst_number = db.Column(db.String(50))
    pan_number = db.Column(db.String(20))
    is_approved = db.Column(db.Boolean, default=False)
    approval_date = db.Column(db.Date)
    approved_by = db.Column(db.String(100))
    quality_rating = db.Column(db.Numeric(3, 2))
    delivery_rating = db.Column(db.Numeric(3, 2))
    odoo_partner_id = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class DefectType(db.Model):
    __tablename__ = 'qc_defect_types'

    id = db.Column(db.Integer, primary_key=True)
    defect_code = db.Column(db.String(50), unique=True, nullable=False)
    defect_name = db.Column(db.String(200), nullable=False)
    defect_category = db.Column(db.String(50))
    severity_level = db.Column(db.Integer, default=1)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class RejectionReason(db.Model):
    __tablename__ = 'qc_rejection_reasons'

    id = db.Column(db.Integer, primary_key=True)
    reason_code = db.Column(db.String(50), unique=True, nullable=False)
    reason_name = db.Column(db.String(200), nullable=False)
    reason_category = db.Column(db.String(50))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Location(db.Model):
    __tablename__ = 'qc_locations'

    id = db.Column(db.Integer, primary_key=True)
    location_code = db.Column(db.String(50), unique=True, nullable=False)
    location_name = db.Column(db.String(200), nullable=False)
    location_type = db.Column(db.String(50))
    parent_location_id = db.Column(db.Integer, db.ForeignKey('qc_locations.id'))
    warehouse_name = db.Column(db.String(200))
    odoo_location_id = db.Column(db.Integer)
    is_quarantine = db.Column(db.Boolean, default=False)
    is_restricted = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
