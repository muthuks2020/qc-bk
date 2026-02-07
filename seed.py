"""
Seed script for local development.
Run: python seed.py
Safe to re-run — uses INSERT ... ON CONFLICT DO NOTHING.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db

app = create_app()


def seed():
    with app.app_context():
        print("Seeding database...")

        # Check connection
        try:
            db.session.execute(db.text("SELECT 1"))
            print("✓ Database connected")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            print("  Make sure PostgreSQL is running and the database exists.")
            print("  Run: createdb appasamy_qc")
            sys.exit(1)

        # The schema SQL already contains INSERT statements for seed data.
        # This script is a safety net for any additional dev-only data.

        # Ensure we have the admin user for testing
        result = db.session.execute(db.text(
            "SELECT COUNT(*) FROM qc_users WHERE user_code = 'USR-008'"
        )).scalar()

        if result == 0:
            print("  Adding admin user...")
            db.session.execute(db.text("""
                INSERT INTO qc_users (user_code, user_name, email, phone, department_id, designation, employee_id)
                VALUES ('USR-008', 'System Admin', 'admin@appasamy.com', '9876543200', 1, 'System Administrator', 'EMP-001')
                ON CONFLICT (user_code) DO NOTHING
            """))

        # Ensure system config defaults exist
        configs = [
            ('app.name', 'Appasamy QC Application', 'string', 'system', 'Application name'),
            ('app.version', '1.0.0', 'string', 'system', 'Current version'),
            ('odoo.api_mode', 'mock', 'string', 'integration', 'API mode: mock or real'),
            ('grn.auto_quarantine', 'true', 'boolean', 'grn', 'Auto-move QC items to quarantine'),
            ('grn.fifo_enabled', 'true', 'boolean', 'grn', 'FIFO ordering for GRN processing'),
            ('inspection.overdue_days', '7', 'number', 'inspection', 'Days before marked overdue'),
            ('inspection.skip_lot_enabled', 'true', 'boolean', 'inspection', 'Enable skip lot logic'),
            ('return.auto_approve_limit', '5000', 'number', 'return', 'Auto-approve below this INR'),
            ('notification.email_enabled', 'true', 'boolean', 'notification', 'Enable email notifications'),
            ('auth.session_timeout_mins', '480', 'number', 'auth', 'Session timeout in minutes'),
        ]
        for key, value, ctype, module, desc in configs:
            db.session.execute(db.text("""
                INSERT INTO qc_system_config (config_key, config_value, config_type, module, description)
                VALUES (:key, :value, :ctype, :module, :desc)
                ON CONFLICT (config_key) DO NOTHING
            """), {'key': key, 'value': value, 'ctype': ctype, 'module': module, 'desc': desc})

        db.session.commit()
        print("✓ Seed data applied successfully")
        print()
        print("Test with:")
        print('  curl http://localhost:5000/api/v1/health')
        print('  curl -H "Authorization: Bearer local-dev-token-2026" \\')
        print('       -H "X-User-Id: 1" -H "X-User-Name: Admin" -H "X-User-Role: admin" \\')
        print('       http://localhost:5000/api/v1/lookups/categories')


if __name__ == '__main__':
    seed()
