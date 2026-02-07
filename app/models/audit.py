from app.extensions import db
from datetime import datetime, timezone
from flask import g, request
import json


class AuditLog(db.Model):
    __tablename__ = 'qc_audit_log'

    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(100), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(20), nullable=False)
    old_data = db.Column(db.JSON)
    new_data = db.Column(db.JSON)
    changed_fields = db.Column(db.ARRAY(db.Text))
    user_id = db.Column(db.String(100))
    user_name = db.Column(db.String(200))
    user_role = db.Column(db.String(50))
    user_ip = db.Column(db.String(50))
    action_timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    @staticmethod
    def log(table_name, record_id, action, old_data=None, new_data=None, changed_fields=None):
        """Log an audit entry. Call within request context."""
        user = getattr(g, 'current_user', {})
        entry = AuditLog(
            table_name=table_name,
            record_id=record_id,
            action=action,
            old_data=old_data,
            new_data=new_data,
            changed_fields=changed_fields,
            user_id=user.get('user_id'),
            user_name=user.get('user_name'),
            user_role=user.get('role'),
            user_ip=request.remote_addr if request else None,
        )
        db.session.add(entry)


class ApprovalHistory(db.Model):
    __tablename__ = 'qc_approval_history'

    id = db.Column(db.Integer, primary_key=True)
    module = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(50), nullable=False)
    from_status = db.Column(db.String(50))
    to_status = db.Column(db.String(50))
    action_by = db.Column(db.String(100), nullable=False)
    action_by_name = db.Column(db.String(200))
    action_role = db.Column(db.String(50))
    action_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    remarks = db.Column(db.Text)
    action_data = db.Column(db.JSON)


class ComponentHistory(db.Model):
    __tablename__ = 'qc_component_history'

    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey('qc_component_master.id', ondelete='CASCADE'), nullable=False)
    action = db.Column(db.String(20), nullable=False)
    field_name = db.Column(db.String(100))
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    change_reason = db.Column(db.Text)
    changed_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    changed_by = db.Column(db.String(100))

    @staticmethod
    def log_change(component_id, action, field_name=None, old_value=None, new_value=None):
        user = getattr(g, 'current_user', {})
        entry = ComponentHistory(
            component_id=component_id,
            action=action,
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            changed_by=user.get('user_name', 'system'),
        )
        db.session.add(entry)
