-- ================================================================================
-- APPASAMY QC APPLICATION - HOLISTIC DATABASE SCHEMA (v4.0)
-- ================================================================================
-- Database: PostgreSQL 14+
-- Version: 4.0 (Complete Holistic Schema)
-- Date: February 3, 2026
-- Author: Shellkode Development Team
-- Client: Appasamy Associates - B-SCAN Product Line
--
-- ENHANCEMENTS OVER v3:
--   + Gate Entry Module (was missing in v3)
--   + Department Master & User Role Management
--   + Store Transfer Module (Screen 11)
--   + Delivery Challan Module (Screen 14)
--   + Debit Note Module (Screen 14)
--   + Notification System
--   + System Configuration
--   + Enhanced Inspection Report (IR) table
--   + Skip Lot Logic tables
--   + Odoo Sync Log
--
-- TABLE COUNT: 42 Tables | 10 Views | 8 Triggers | 8 Functions
--
-- MODULES COVERED (Mapped to 16 Screens):
--   M1. System & Auth (Departments, Users, Roles, Permissions, Config)
--   M2. Master Data (Categories, Groups, Units, Instruments, Vendors, Locations)
--   M3. QC Plans (Plans, Stages, Parameters, Sampling)
--   M4. Component Master (Components, Checking Params, Specs, Docs, Vendors)
--   M5. Gate Entry (Inward Register, Gatepass)  â€” Screen 5
--   M6. GRN (Goods Receipt Note & Items)  â€” Screen 6
--   M7. QC Inspection (Queue, Results, Details, Defects)  â€” Screens 7-9
--   M8. Inspection Reports (IR Generation)  â€” Screen 10
--   M9. Store Transfer (Acceptance Flow)  â€” Screen 11
--   M10. Vendor Returns (Return Requests, Items)  â€” Screen 12-13
--   M11. Delivery Challan & Debit Notes  â€” Screen 14
--   M12. Workflow & Audit (Approvals, History, Audit Log)
--   M13. Dashboard & Reports (Summaries, Vendor Performance)  â€” Screens 15-16
--   M14. Notifications
-- ================================================================================

BEGIN;

-- ================================================================================
-- MODULE 1: SYSTEM & AUTHENTICATION
-- ================================================================================

-- 1.1 Department Master
CREATE TABLE IF NOT EXISTS qc_departments (
    id SERIAL PRIMARY KEY,
    department_code VARCHAR(50) UNIQUE NOT NULL,
    department_name VARCHAR(200) NOT NULL,
    pass_source_location VARCHAR(200),
    pass_source_location_odoo_id INTEGER,
    pass_destination_location VARCHAR(200),
    pass_destination_location_odoo_id INTEGER,
    fail_source_location VARCHAR(200),
    fail_source_location_odoo_id INTEGER,
    fail_destination_location VARCHAR(200),
    fail_destination_location_odoo_id INTEGER,
    manager_id INTEGER,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 1.2 User Master
CREATE TABLE IF NOT EXISTS qc_users (
    id SERIAL PRIMARY KEY,
    user_code VARCHAR(50) UNIQUE NOT NULL,
    user_name VARCHAR(200) NOT NULL,
    email VARCHAR(200) UNIQUE NOT NULL,
    phone VARCHAR(50),
    department_id INTEGER REFERENCES qc_departments(id),
    designation VARCHAR(100),
    employee_id VARCHAR(50),
    office365_id VARCHAR(200),          -- SSO integration
    password_hash VARCHAR(500),
    avatar_url VARCHAR(500),
    last_login_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_usr_dept ON qc_users(department_id);
CREATE INDEX idx_usr_email ON qc_users(email);

-- 1.3 Role Master
CREATE TABLE IF NOT EXISTS qc_roles (
    id SERIAL PRIMARY KEY,
    role_code VARCHAR(50) UNIQUE NOT NULL,   -- 'admin', 'maker', 'checker', 'approver'
    role_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 1.4 User-Role Mapping (Many-to-Many)
CREATE TABLE IF NOT EXISTS qc_user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES qc_users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES qc_roles(id) ON DELETE CASCADE,
    department_id INTEGER REFERENCES qc_departments(id),
    is_active BOOLEAN DEFAULT TRUE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_by VARCHAR(100),
    UNIQUE(user_id, role_id, department_id)
);
CREATE INDEX idx_ur_user ON qc_user_roles(user_id);
CREATE INDEX idx_ur_role ON qc_user_roles(role_id);

-- 1.5 Permission Master
CREATE TABLE IF NOT EXISTS qc_permissions (
    id SERIAL PRIMARY KEY,
    permission_code VARCHAR(100) UNIQUE NOT NULL,
    permission_name VARCHAR(200) NOT NULL,
    module VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 1.6 Role-Permission Mapping
CREATE TABLE IF NOT EXISTS qc_role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES qc_roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES qc_permissions(id) ON DELETE CASCADE,
    can_create BOOLEAN DEFAULT FALSE,
    can_read BOOLEAN DEFAULT TRUE,
    can_update BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    can_approve BOOLEAN DEFAULT FALSE,
    UNIQUE(role_id, permission_id)
);

-- 1.7 User-Product Access (which products a user can inspect)
CREATE TABLE IF NOT EXISTS qc_user_product_access (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES qc_users(id) ON DELETE CASCADE,
    component_id INTEGER,   -- NULL = all products
    category_id INTEGER,    -- NULL = all categories
    access_type VARCHAR(20) DEFAULT 'full',  -- 'full', 'read_only'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, component_id)
);

-- 1.8 System Configuration
CREATE TABLE IF NOT EXISTS qc_system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    config_type VARCHAR(20) DEFAULT 'string',   -- 'string', 'number', 'boolean', 'json'
    module VARCHAR(50),
    description TEXT,
    is_editable BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100)
);

-- 1.9 User Sessions (for audit)
CREATE TABLE IF NOT EXISTS qc_user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES qc_users(id),
    session_token VARCHAR(500) NOT NULL,
    ip_address VARCHAR(50),
    user_agent TEXT,
    login_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    logout_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);


-- ================================================================================
-- MODULE 2: CORE MASTER TABLES
-- ================================================================================

-- 2.1 Product Categories
CREATE TABLE IF NOT EXISTS qc_product_categories (
    id SERIAL PRIMARY KEY,
    category_code VARCHAR(50) UNIQUE NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    icon VARCHAR(20),
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

-- 2.2 Product Groups
CREATE TABLE IF NOT EXISTS qc_product_groups (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES qc_product_categories(id),
    group_code VARCHAR(50) UNIQUE NOT NULL,
    group_name VARCHAR(100) NOT NULL,
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_pg_category ON qc_product_groups(category_id);

-- 2.3 Units of Measurement
CREATE TABLE IF NOT EXISTS qc_units (
    id SERIAL PRIMARY KEY,
    unit_code VARCHAR(20) UNIQUE NOT NULL,
    unit_name VARCHAR(100) NOT NULL,
    unit_symbol VARCHAR(20),
    unit_type VARCHAR(50),          -- 'length', 'weight', 'count', 'volume', 'electrical'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.4 Measuring Instruments
CREATE TABLE IF NOT EXISTS qc_instruments (
    id SERIAL PRIMARY KEY,
    instrument_code VARCHAR(50) UNIQUE NOT NULL,
    instrument_name VARCHAR(200) NOT NULL,
    instrument_type VARCHAR(100),
    make VARCHAR(100),
    model VARCHAR(100),
    serial_number VARCHAR(100),
    calibration_due_date DATE,
    calibration_frequency_days INTEGER DEFAULT 365,
    last_calibration_date DATE,
    calibration_certificate_no VARCHAR(100),
    location VARCHAR(200),
    department_id INTEGER REFERENCES qc_departments(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.5 Vendors/Suppliers Master
CREATE TABLE IF NOT EXISTS qc_vendors (
    id SERIAL PRIMARY KEY,
    vendor_code VARCHAR(50) UNIQUE NOT NULL,
    vendor_name VARCHAR(200) NOT NULL,
    vendor_type VARCHAR(50) DEFAULT 'supplier',
    contact_person VARCHAR(100),
    email VARCHAR(200),
    phone VARCHAR(50),
    mobile VARCHAR(50),
    address_line1 TEXT,
    address_line2 TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'India',
    pincode VARCHAR(20),
    gst_number VARCHAR(50),
    pan_number VARCHAR(20),
    is_approved BOOLEAN DEFAULT FALSE,
    approval_date DATE,
    approved_by VARCHAR(100),
    quality_rating DECIMAL(3,2),
    delivery_rating DECIMAL(3,2),
    odoo_partner_id INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.6 Sampling Plans (AQL)
CREATE TABLE IF NOT EXISTS qc_sampling_plans (
    id SERIAL PRIMARY KEY,
    plan_code VARCHAR(50) UNIQUE NOT NULL,
    plan_name VARCHAR(200) NOT NULL,
    plan_type VARCHAR(20),               -- 'sp0', 'sp1', 'sp2', 'sp3'
    aql_level VARCHAR(50),
    inspection_level VARCHAR(50),        -- 'normal', 'tightened', 'reduced'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.7 Sampling Plan Details (Lot Size â†’ Sample Size)
CREATE TABLE IF NOT EXISTS qc_sampling_plan_details (
    id SERIAL PRIMARY KEY,
    sampling_plan_id INTEGER NOT NULL REFERENCES qc_sampling_plans(id) ON DELETE CASCADE,
    lot_size_min INTEGER NOT NULL,
    lot_size_max INTEGER NOT NULL,
    sample_size INTEGER NOT NULL,
    accept_number INTEGER NOT NULL,
    reject_number INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_spd_plan ON qc_sampling_plan_details(sampling_plan_id);

-- 2.8 Defect Types Master
CREATE TABLE IF NOT EXISTS qc_defect_types (
    id SERIAL PRIMARY KEY,
    defect_code VARCHAR(50) UNIQUE NOT NULL,
    defect_name VARCHAR(200) NOT NULL,
    defect_category VARCHAR(50),        -- 'critical', 'major', 'minor'
    severity_level INTEGER DEFAULT 1,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.9 Rejection Reasons Master
CREATE TABLE IF NOT EXISTS qc_rejection_reasons (
    id SERIAL PRIMARY KEY,
    reason_code VARCHAR(50) UNIQUE NOT NULL,
    reason_name VARCHAR(200) NOT NULL,
    reason_category VARCHAR(50),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.10 Locations/Warehouses
CREATE TABLE IF NOT EXISTS qc_locations (
    id SERIAL PRIMARY KEY,
    location_code VARCHAR(50) UNIQUE NOT NULL,
    location_name VARCHAR(200) NOT NULL,
    location_type VARCHAR(50),          -- 'store', 'quarantine', 'vendor', 'production'
    parent_location_id INTEGER REFERENCES qc_locations(id),
    warehouse_name VARCHAR(200),
    odoo_location_id INTEGER,
    is_quarantine BOOLEAN DEFAULT FALSE,
    is_restricted BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- ================================================================================
-- MODULE 3: QC PLANS
-- ================================================================================

-- 3.1 QC Plan Master
CREATE TABLE IF NOT EXISTS qc_plans (
    id SERIAL PRIMARY KEY,
    plan_code VARCHAR(50) UNIQUE NOT NULL,       -- e.g., 'RD.7.3-07', 'A12'
    plan_name VARCHAR(200) NOT NULL,
    revision VARCHAR(20),
    revision_date DATE,
    effective_date DATE,
    plan_type VARCHAR(50) DEFAULT 'standard',
    inspection_stages INTEGER DEFAULT 1,
    requires_visual BOOLEAN DEFAULT TRUE,
    requires_functional BOOLEAN DEFAULT FALSE,
    document_number VARCHAR(100),
    document_path VARCHAR(500),
    approved_by VARCHAR(100),
    approved_date DATE,
    status VARCHAR(20) DEFAULT 'draft',          -- 'draft', 'active', 'superseded'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3.2 QC Plan Stages
CREATE TABLE IF NOT EXISTS qc_plan_stages (
    id SERIAL PRIMARY KEY,
    qc_plan_id INTEGER NOT NULL REFERENCES qc_plans(id) ON DELETE CASCADE,
    stage_code VARCHAR(50) NOT NULL,
    stage_name VARCHAR(100) NOT NULL,        -- 'Visual Inspection', 'Functional Test'
    stage_type VARCHAR(20) NOT NULL,         -- 'visual', 'functional'
    stage_sequence INTEGER NOT NULL,
    inspection_type VARCHAR(20) DEFAULT 'sampling', -- '100_percent', 'sampling'
    sampling_plan_id INTEGER REFERENCES qc_sampling_plans(id),
    is_mandatory BOOLEAN DEFAULT TRUE,
    requires_instrument BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(qc_plan_id, stage_code),
    UNIQUE(qc_plan_id, stage_sequence)
);
CREATE INDEX idx_qps_plan ON qc_plan_stages(qc_plan_id);

-- 3.3 QC Plan Parameters
CREATE TABLE IF NOT EXISTS qc_plan_parameters (
    id SERIAL PRIMARY KEY,
    qc_plan_stage_id INTEGER NOT NULL REFERENCES qc_plan_stages(id) ON DELETE CASCADE,
    parameter_code VARCHAR(50),
    parameter_name VARCHAR(200) NOT NULL,
    parameter_sequence INTEGER DEFAULT 0,
    checking_type VARCHAR(20) NOT NULL,      -- 'visual', 'functional'
    specification TEXT,
    unit_id INTEGER REFERENCES qc_units(id),
    nominal_value DECIMAL(15,4),
    tolerance_min DECIMAL(15,4),
    tolerance_max DECIMAL(15,4),
    instrument_id INTEGER REFERENCES qc_instruments(id),
    input_type VARCHAR(20) DEFAULT 'measurement',  -- 'measurement', 'pass_fail', 'yes_no', 'text'
    is_mandatory BOOLEAN DEFAULT TRUE,
    acceptance_criteria TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_qpp_stage ON qc_plan_parameters(qc_plan_stage_id);


-- ================================================================================
-- MODULE 4: COMPONENT MASTER
-- ================================================================================

-- 4.1 Component Master
CREATE TABLE IF NOT EXISTS qc_component_master (
    id SERIAL PRIMARY KEY,
    component_code VARCHAR(50) UNIQUE NOT NULL,
    part_code VARCHAR(100) UNIQUE NOT NULL,
    part_name VARCHAR(300) NOT NULL,
    part_description TEXT,
    category_id INTEGER REFERENCES qc_product_categories(id),
    product_group_id INTEGER REFERENCES qc_product_groups(id),
    qc_required BOOLEAN DEFAULT TRUE,
    qc_plan_id INTEGER REFERENCES qc_plans(id),
    default_inspection_type VARCHAR(20) DEFAULT 'sampling',  -- '100_percent', 'sampling'
    default_sampling_plan_id INTEGER REFERENCES qc_sampling_plans(id),
    drawing_no VARCHAR(100),
    drawing_revision VARCHAR(20),
    test_cert_required BOOLEAN DEFAULT FALSE,
    spec_required BOOLEAN DEFAULT FALSE,
    fqir_required BOOLEAN DEFAULT FALSE,
    coc_required BOOLEAN DEFAULT FALSE,
    pr_process_code VARCHAR(50),            -- 'direct_purchase', 'internal_job', 'external_job'
    pr_process_name VARCHAR(200),
    lead_time_days INTEGER,
    primary_vendor_id INTEGER REFERENCES qc_vendors(id),
    odoo_product_id INTEGER,
    odoo_product_tmpl_id INTEGER,
    skip_lot_enabled BOOLEAN DEFAULT FALSE,
    skip_lot_count INTEGER DEFAULT 0,
    skip_lot_threshold INTEGER DEFAULT 5,
    status VARCHAR(20) DEFAULT 'draft',     -- 'draft', 'active', 'inactive'
    department_id INTEGER REFERENCES qc_departments(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by VARCHAR(100)
);
CREATE INDEX idx_cm_part_code ON qc_component_master(part_code);
CREATE INDEX idx_cm_category ON qc_component_master(category_id);
CREATE INDEX idx_cm_qc_plan ON qc_component_master(qc_plan_id);
CREATE INDEX idx_cm_status ON qc_component_master(status) WHERE is_deleted = FALSE;
CREATE INDEX idx_cm_dept ON qc_component_master(department_id);

-- 4.2 Component Checking Parameters
CREATE TABLE IF NOT EXISTS qc_component_checking_params (
    id SERIAL PRIMARY KEY,
    component_id INTEGER NOT NULL REFERENCES qc_component_master(id) ON DELETE CASCADE,
    qc_plan_stage_id INTEGER REFERENCES qc_plan_stages(id),
    checking_type VARCHAR(20) NOT NULL,     -- 'visual', 'functional'
    checking_point VARCHAR(200) NOT NULL,
    specification VARCHAR(500),
    unit_id INTEGER REFERENCES qc_units(id),
    unit_code VARCHAR(20),
    nominal_value DECIMAL(15,4),
    tolerance_min DECIMAL(15,4),
    tolerance_max DECIMAL(15,4),
    instrument_id INTEGER REFERENCES qc_instruments(id),
    instrument_name VARCHAR(200),
    input_type VARCHAR(20) DEFAULT 'measurement',
    sort_order INTEGER DEFAULT 0,
    is_mandatory BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ccp_component ON qc_component_checking_params(component_id);
CREATE INDEX idx_ccp_type ON qc_component_checking_params(checking_type);

-- 4.3 Component Specifications
CREATE TABLE IF NOT EXISTS qc_component_specifications (
    id SERIAL PRIMARY KEY,
    component_id INTEGER NOT NULL REFERENCES qc_component_master(id) ON DELETE CASCADE,
    spec_key VARCHAR(100) NOT NULL,
    spec_value VARCHAR(500),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(component_id, spec_key)
);
CREATE INDEX idx_cs_component ON qc_component_specifications(component_id);

-- 4.4 Component Documents (Drawings, Test Certs, FQIR)
CREATE TABLE IF NOT EXISTS qc_component_documents (
    id SERIAL PRIMARY KEY,
    component_id INTEGER NOT NULL REFERENCES qc_component_master(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,     -- 'drawing', 'test_cert', 'fqir', 'coc', 'spec_sheet'
    file_name VARCHAR(300) NOT NULL,
    original_name VARCHAR(300),
    file_path VARCHAR(500),
    file_url VARCHAR(500),
    file_size INTEGER,
    mime_type VARCHAR(100),
    version VARCHAR(20) DEFAULT '1.0',
    is_current BOOLEAN DEFAULT TRUE,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    uploaded_by VARCHAR(100)
);
CREATE INDEX idx_cd_component ON qc_component_documents(component_id);

-- 4.5 Component-Vendor Mapping
CREATE TABLE IF NOT EXISTS qc_component_vendors (
    id SERIAL PRIMARY KEY,
    component_id INTEGER NOT NULL REFERENCES qc_component_master(id) ON DELETE CASCADE,
    vendor_id INTEGER NOT NULL REFERENCES qc_vendors(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT FALSE,
    approval_date DATE,
    vendor_part_code VARCHAR(100),
    unit_price DECIMAL(15,2),
    currency VARCHAR(10) DEFAULT 'INR',
    lead_time_days INTEGER,
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(component_id, vendor_id)
);
CREATE INDEX idx_cv_component ON qc_component_vendors(component_id);


-- ================================================================================
-- MODULE 5: GATE ENTRY (NEW - Was missing in v3)
-- ================================================================================

-- 5.1 Gate Entry / Inward Register
CREATE TABLE IF NOT EXISTS qc_gate_entries (
    id SERIAL PRIMARY KEY,
    gate_entry_number VARCHAR(50) UNIQUE NOT NULL,
    inward_register_number VARCHAR(50),
    entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
    entry_time TIME DEFAULT CURRENT_TIME,
    vendor_id INTEGER NOT NULL REFERENCES qc_vendors(id),
    po_number VARCHAR(100),
    po_date DATE,
    odoo_po_id INTEGER,
    invoice_number VARCHAR(100),
    invoice_date DATE,
    invoice_amount DECIMAL(15,2),
    dc_number VARCHAR(100),                 -- Vendor's Delivery Challan
    dc_date DATE,
    vehicle_number VARCHAR(50),
    driver_name VARCHAR(200),
    driver_contact VARCHAR(50),
    no_of_packages INTEGER,
    total_weight DECIMAL(15,3),
    inward_seal_number VARCHAR(100),
    gatepass_number VARCHAR(50),
    gatepass_generated BOOLEAN DEFAULT FALSE,
    quantity_verified BOOLEAN DEFAULT FALSE,
    quantity_match_status VARCHAR(20),       -- 'match', 'shortage', 'excess', 'invoice_mismatch'
    mismatch_remarks TEXT,
    status VARCHAR(20) DEFAULT 'pending',   -- 'pending', 'verified', 'gatepass_issued', 'grn_pending', 'completed', 'rejected'
    entry_by VARCHAR(100),
    verified_by VARCHAR(100),
    verified_date TIMESTAMP WITH TIME ZONE,
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);
CREATE INDEX idx_ge_date ON qc_gate_entries(entry_date DESC);
CREATE INDEX idx_ge_vendor ON qc_gate_entries(vendor_id);
CREATE INDEX idx_ge_status ON qc_gate_entries(status);
CREATE INDEX idx_ge_po ON qc_gate_entries(po_number);

-- 5.2 Gate Entry Items (Line items for quantity verification)
CREATE TABLE IF NOT EXISTS qc_gate_entry_items (
    id SERIAL PRIMARY KEY,
    gate_entry_id INTEGER NOT NULL REFERENCES qc_gate_entries(id) ON DELETE CASCADE,
    component_id INTEGER REFERENCES qc_component_master(id),
    part_code VARCHAR(100),
    part_name VARCHAR(300),
    po_quantity DECIMAL(15,3),
    invoice_quantity DECIMAL(15,3),
    received_quantity DECIMAL(15,3),
    uom VARCHAR(20) DEFAULT 'NOS',
    quantity_match BOOLEAN,
    mismatch_type VARCHAR(50),              -- 'quantity_shortage', 'quantity_excess', 'invoice_mismatch'
    mismatch_quantity DECIMAL(15,3),
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_gei_entry ON qc_gate_entry_items(gate_entry_id);


-- ================================================================================
-- MODULE 6: GRN (GOODS RECEIPT NOTE)
-- ================================================================================

-- 6.1 GRN Master
CREATE TABLE IF NOT EXISTS qc_grn (
    id SERIAL PRIMARY KEY,
    grn_number VARCHAR(50) UNIQUE NOT NULL,
    grn_date DATE NOT NULL DEFAULT CURRENT_DATE,
    gate_entry_id INTEGER REFERENCES qc_gate_entries(id),
    vendor_id INTEGER NOT NULL REFERENCES qc_vendors(id),
    po_number VARCHAR(100),
    po_date DATE,
    odoo_po_id INTEGER,
    invoice_number VARCHAR(100),
    invoice_date DATE,
    invoice_amount DECIMAL(15,2),
    dc_number VARCHAR(100),
    dc_date DATE,
    bill_number VARCHAR(100),
    bill_date DATE,
    vehicle_number VARCHAR(50),
    receiving_location_id INTEGER REFERENCES qc_locations(id),
    quarantine_location_id INTEGER REFERENCES qc_locations(id),
    status VARCHAR(20) DEFAULT 'draft',     -- 'draft', 'validated', 'qc_pending', 'qc_complete', 'closed'
    qc_status VARCHAR(20),                  -- 'pending', 'in_progress', 'passed', 'failed', 'partial'
    has_alternate_material BOOLEAN DEFAULT FALSE,
    alternate_material_remarks TEXT,
    maker_id VARCHAR(100),
    maker_date TIMESTAMP WITH TIME ZONE,
    checker_id VARCHAR(100),
    checker_date TIMESTAMP WITH TIME ZONE,
    approver_id VARCHAR(100),
    approver_date TIMESTAMP WITH TIME ZONE,
    odoo_picking_id INTEGER,
    odoo_sync_status VARCHAR(20),
    odoo_sync_date TIMESTAMP WITH TIME ZONE,
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);
CREATE INDEX idx_grn_date ON qc_grn(grn_date DESC);
CREATE INDEX idx_grn_vendor ON qc_grn(vendor_id);
CREATE INDEX idx_grn_status ON qc_grn(status);
CREATE INDEX idx_grn_qc_status ON qc_grn(qc_status);
CREATE INDEX idx_grn_gate_entry ON qc_grn(gate_entry_id);

-- 6.2 GRN Line Items
CREATE TABLE IF NOT EXISTS qc_grn_items (
    id SERIAL PRIMARY KEY,
    grn_id INTEGER NOT NULL REFERENCES qc_grn(id) ON DELETE CASCADE,
    po_line_number INTEGER,
    odoo_po_line_id INTEGER,
    component_id INTEGER NOT NULL REFERENCES qc_component_master(id),
    part_code VARCHAR(100) NOT NULL,
    part_name VARCHAR(300),
    po_quantity DECIMAL(15,3),
    received_quantity DECIMAL(15,3) NOT NULL,
    accepted_quantity DECIMAL(15,3) DEFAULT 0,
    rejected_quantity DECIMAL(15,3) DEFAULT 0,
    uom VARCHAR(20) DEFAULT 'NOS',
    unit_price DECIMAL(15,4),
    line_amount DECIMAL(15,2),
    qc_required BOOLEAN DEFAULT TRUE,
    qc_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'in_progress', 'passed', 'failed', 'partial'
    inspection_type VARCHAR(20),             -- '100_percent', 'sampling'
    sample_size INTEGER,
    inspected_quantity INTEGER DEFAULT 0,
    batch_number VARCHAR(100),
    lot_number VARCHAR(100),
    manufacturing_date DATE,
    expiry_date DATE,
    storage_location_id INTEGER REFERENCES qc_locations(id),
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_grni_grn ON qc_grn_items(grn_id);
CREATE INDEX idx_grni_component ON qc_grn_items(component_id);
CREATE INDEX idx_grni_qc_status ON qc_grn_items(qc_status);


-- ================================================================================
-- MODULE 7: QC INSPECTION
-- ================================================================================

-- 7.1 Inspection Queue
CREATE TABLE IF NOT EXISTS qc_inspection_queue (
    id SERIAL PRIMARY KEY,
    queue_number VARCHAR(50) UNIQUE NOT NULL,
    grn_id INTEGER NOT NULL REFERENCES qc_grn(id),
    grn_item_id INTEGER NOT NULL REFERENCES qc_grn_items(id),
    component_id INTEGER NOT NULL REFERENCES qc_component_master(id),
    qc_plan_id INTEGER REFERENCES qc_plans(id),
    lot_size INTEGER NOT NULL,
    sample_size INTEGER NOT NULL,
    inspection_type VARCHAR(20) NOT NULL,    -- '100_percent', 'sampling'
    sampling_plan_id INTEGER REFERENCES qc_sampling_plans(id),
    priority INTEGER DEFAULT 5,             -- 1=highest, 10=lowest
    assigned_to VARCHAR(100),               -- maker (QC inspector)
    assigned_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'pending',   -- 'pending', 'in_progress', 'visual_done', 'functional_done', 'completed', 'on_hold'
    current_stage_id INTEGER REFERENCES qc_plan_stages(id),
    visual_result VARCHAR(20),              -- 'pass', 'fail', 'pending'
    functional_result VARCHAR(20),          -- 'pass', 'fail', 'pending', 'na'
    overall_result VARCHAR(20),             -- 'accept', 'reject', 'pending'
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    due_date DATE,
    days_in_quarantine INTEGER DEFAULT 0,
    is_overdue BOOLEAN DEFAULT FALSE,
    is_skip_lot BOOLEAN DEFAULT FALSE,
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_iq_grn ON qc_inspection_queue(grn_id);
CREATE INDEX idx_iq_component ON qc_inspection_queue(component_id);
CREATE INDEX idx_iq_status ON qc_inspection_queue(status);
CREATE INDEX idx_iq_priority ON qc_inspection_queue(priority, created_at);
CREATE INDEX idx_iq_assigned ON qc_inspection_queue(assigned_to);

-- 7.2 Inspection Results (per stage)
CREATE TABLE IF NOT EXISTS qc_inspection_results (
    id SERIAL PRIMARY KEY,
    result_number VARCHAR(50) UNIQUE NOT NULL,
    inspection_queue_id INTEGER NOT NULL REFERENCES qc_inspection_queue(id),
    qc_plan_stage_id INTEGER REFERENCES qc_plan_stages(id),
    stage_name VARCHAR(100),
    stage_type VARCHAR(20),                 -- 'visual', 'functional'
    sample_number INTEGER DEFAULT 1,
    sample_size INTEGER,
    total_checked INTEGER DEFAULT 0,
    total_passed INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    result VARCHAR(20),                     -- 'pass', 'fail', 'conditional'
    result_date TIMESTAMP WITH TIME ZONE,
    inspector_id VARCHAR(100),              -- maker
    inspector_name VARCHAR(200),
    verified_by VARCHAR(100),               -- checker
    verified_date TIMESTAMP WITH TIME ZONE,
    verification_remarks TEXT,
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ir_queue ON qc_inspection_results(inspection_queue_id);
CREATE INDEX idx_ir_result ON qc_inspection_results(result);
CREATE INDEX idx_ir_stage_type ON qc_inspection_results(stage_type);

-- 7.3 Inspection Result Details (per parameter)
CREATE TABLE IF NOT EXISTS qc_inspection_result_details (
    id SERIAL PRIMARY KEY,
    inspection_result_id INTEGER NOT NULL REFERENCES qc_inspection_results(id) ON DELETE CASCADE,
    checking_param_id INTEGER REFERENCES qc_component_checking_params(id),
    qc_plan_param_id INTEGER REFERENCES qc_plan_parameters(id),
    parameter_name VARCHAR(200) NOT NULL,
    checking_type VARCHAR(20),              -- 'visual', 'functional'
    specification VARCHAR(500),
    unit_code VARCHAR(20),
    tolerance_min DECIMAL(15,4),
    tolerance_max DECIMAL(15,4),
    measured_value DECIMAL(15,4),
    measured_value_2 DECIMAL(15,4),         -- for dual measurements
    measured_value_text VARCHAR(500),
    yes_no_result BOOLEAN,
    instrument_id INTEGER REFERENCES qc_instruments(id),
    instrument_code VARCHAR(50),
    is_within_tolerance BOOLEAN,
    result VARCHAR(20),                     -- 'pass', 'fail'
    defect_type_id INTEGER REFERENCES qc_defect_types(id),
    defect_remarks TEXT,
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ird_result ON qc_inspection_result_details(inspection_result_id);

-- 7.4 Inspection Defects
CREATE TABLE IF NOT EXISTS qc_inspection_defects (
    id SERIAL PRIMARY KEY,
    inspection_result_id INTEGER NOT NULL REFERENCES qc_inspection_results(id) ON DELETE CASCADE,
    defect_type_id INTEGER REFERENCES qc_defect_types(id),
    defect_code VARCHAR(50),
    defect_description TEXT,
    defect_quantity INTEGER DEFAULT 1,
    severity VARCHAR(20),                   -- 'critical', 'major', 'minor'
    image_url VARCHAR(500),
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_id_result ON qc_inspection_defects(inspection_result_id);


-- ================================================================================
-- MODULE 8: INSPECTION REPORTS (IR) â€” NEW DEDICATED TABLE
-- ================================================================================

-- 8.1 Inspection Report Master
CREATE TABLE IF NOT EXISTS qc_inspection_reports (
    id SERIAL PRIMARY KEY,
    ir_number VARCHAR(50) UNIQUE NOT NULL,
    ir_date DATE NOT NULL DEFAULT CURRENT_DATE,
    inspection_queue_id INTEGER NOT NULL REFERENCES qc_inspection_queue(id),
    grn_id INTEGER NOT NULL REFERENCES qc_grn(id),
    grn_number VARCHAR(50),
    grn_date DATE,
    po_number VARCHAR(100),
    po_date DATE,
    vendor_id INTEGER NOT NULL REFERENCES qc_vendors(id),
    vendor_name VARCHAR(200),
    supplier_bill_no VARCHAR(100),
    supplier_bill_date DATE,
    component_id INTEGER NOT NULL REFERENCES qc_component_master(id),
    part_code VARCHAR(100),
    part_name VARCHAR(300),
    lot_number VARCHAR(100),
    lot_size INTEGER,
    sample_size INTEGER,
    sample_plan_code VARCHAR(50),
    quality_plan_code VARCHAR(50),
    test_certificate_available BOOLEAN DEFAULT FALSE,
    fqir_available BOOLEAN DEFAULT FALSE,
    quantity_check_result VARCHAR(20),       -- 'pass', 'fail'
    visual_test_result VARCHAR(20),         -- 'pass', 'fail', 'na'
    functional_test_result VARCHAR(20),     -- 'pass', 'fail', 'na'
    overall_disposition VARCHAR(20) NOT NULL, -- 'accept', 'reject', 'conditional_accept'
    rejection_category VARCHAR(100),
    failure_summary TEXT,
    priority VARCHAR(20) DEFAULT 'normal',
    maker_id VARCHAR(100),                  -- QC Inspector who created
    maker_name VARCHAR(200),
    maker_date TIMESTAMP WITH TIME ZONE,
    maker_signature TEXT,
    checker_id VARCHAR(100),                -- QC Manager who verified
    checker_name VARCHAR(200),
    checker_date TIMESTAMP WITH TIME ZONE,
    checker_remarks TEXT,
    approver_id VARCHAR(100),
    approver_name VARCHAR(200),
    approver_date TIMESTAMP WITH TIME ZONE,
    approver_remarks TEXT,
    status VARCHAR(20) DEFAULT 'draft',     -- 'draft', 'submitted', 'verified', 'approved', 'rejected'
    pdf_path VARCHAR(500),
    pdf_generated_at TIMESTAMP WITH TIME ZONE,
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);
CREATE INDEX idx_irpt_queue ON qc_inspection_reports(inspection_queue_id);
CREATE INDEX idx_irpt_grn ON qc_inspection_reports(grn_id);
CREATE INDEX idx_irpt_vendor ON qc_inspection_reports(vendor_id);
CREATE INDEX idx_irpt_disposition ON qc_inspection_reports(overall_disposition);
CREATE INDEX idx_irpt_status ON qc_inspection_reports(status);


-- ================================================================================
-- MODULE 9: STORE TRANSFER (Acceptance Flow) â€” NEW
-- ================================================================================

-- 9.1 Store Transfers
CREATE TABLE IF NOT EXISTS qc_store_transfers (
    id SERIAL PRIMARY KEY,
    transfer_number VARCHAR(50) UNIQUE NOT NULL,
    transfer_date DATE NOT NULL DEFAULT CURRENT_DATE,
    inspection_report_id INTEGER NOT NULL REFERENCES qc_inspection_reports(id),
    grn_id INTEGER NOT NULL REFERENCES qc_grn(id),
    grn_item_id INTEGER NOT NULL REFERENCES qc_grn_items(id),
    component_id INTEGER NOT NULL REFERENCES qc_component_master(id),
    part_code VARCHAR(100),
    part_name VARCHAR(300),
    transfer_quantity DECIMAL(15,3) NOT NULL,
    uom VARCHAR(20) DEFAULT 'NOS',
    source_location_id INTEGER REFERENCES qc_locations(id),       -- Quarantine
    destination_location_id INTEGER REFERENCES qc_locations(id),  -- Store
    status VARCHAR(20) DEFAULT 'initiated',  -- 'initiated', 'in_transit', 'received', 'acknowledged'
    initiated_by VARCHAR(100),               -- QC Inspector
    initiated_date TIMESTAMP WITH TIME ZONE,
    received_by VARCHAR(100),                -- Store Keeper
    received_date TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(100),
    acknowledged_date TIMESTAMP WITH TIME ZONE,
    odoo_transfer_id INTEGER,
    odoo_sync_status VARCHAR(20),
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_st_grn ON qc_store_transfers(grn_id);
CREATE INDEX idx_st_ir ON qc_store_transfers(inspection_report_id);
CREATE INDEX idx_st_status ON qc_store_transfers(status);


-- ================================================================================
-- MODULE 10: VENDOR RETURNS
-- ================================================================================

-- 10.1 Vendor Return Request
CREATE TABLE IF NOT EXISTS qc_vendor_returns (
    id SERIAL PRIMARY KEY,
    return_number VARCHAR(50) UNIQUE NOT NULL,
    return_date DATE NOT NULL DEFAULT CURRENT_DATE,
    grn_id INTEGER NOT NULL REFERENCES qc_grn(id),
    inspection_report_id INTEGER REFERENCES qc_inspection_reports(id),
    vendor_id INTEGER NOT NULL REFERENCES qc_vendors(id),
    po_number VARCHAR(100),
    return_type VARCHAR(50) NOT NULL,        -- 'complete', 'partial'
    total_return_qty DECIMAL(15,3),
    total_return_amount DECIMAL(15,2),
    status VARCHAR(20) DEFAULT 'draft',      -- 'draft','submitted','checker_review','checker_approved','checker_rejected','approver_review','approved','rejected','dc_generated','shipped','closed'
    -- Maker (QC Inspector)
    maker_id VARCHAR(100),
    maker_name VARCHAR(200),
    maker_date TIMESTAMP WITH TIME ZONE,
    maker_remarks TEXT,
    -- Checker (QC Manager)
    checker_id VARCHAR(100),
    checker_name VARCHAR(200),
    checker_date TIMESTAMP WITH TIME ZONE,
    checker_remarks TEXT,
    checker_action VARCHAR(20),              -- 'approve', 'reject', 'return_to_maker'
    -- Approver (Finance/Management)
    approver_id VARCHAR(100),
    approver_name VARCHAR(200),
    approver_date TIMESTAMP WITH TIME ZONE,
    approver_remarks TEXT,
    approver_action VARCHAR(20),
    -- Shipping
    shipped_date DATE,
    courier_name VARCHAR(200),
    tracking_number VARCHAR(100),
    -- Odoo
    odoo_return_picking_id INTEGER,
    odoo_sync_status VARCHAR(20),
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);
CREATE INDEX idx_vr_grn ON qc_vendor_returns(grn_id);
CREATE INDEX idx_vr_vendor ON qc_vendor_returns(vendor_id);
CREATE INDEX idx_vr_status ON qc_vendor_returns(status);
CREATE INDEX idx_vr_ir ON qc_vendor_returns(inspection_report_id);

-- 10.2 Vendor Return Items
CREATE TABLE IF NOT EXISTS qc_vendor_return_items (
    id SERIAL PRIMARY KEY,
    vendor_return_id INTEGER NOT NULL REFERENCES qc_vendor_returns(id) ON DELETE CASCADE,
    grn_item_id INTEGER NOT NULL REFERENCES qc_grn_items(id),
    component_id INTEGER NOT NULL REFERENCES qc_component_master(id),
    part_code VARCHAR(100),
    part_name VARCHAR(300),
    return_quantity DECIMAL(15,3) NOT NULL,
    uom VARCHAR(20) DEFAULT 'NOS',
    rejection_reason_id INTEGER REFERENCES qc_rejection_reasons(id),
    rejection_reason_text TEXT,
    deviation_description TEXT,
    inspection_result_id INTEGER REFERENCES qc_inspection_results(id),
    unit_price DECIMAL(15,4),
    line_amount DECIMAL(15,2),
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_vri_return ON qc_vendor_return_items(vendor_return_id);


-- ================================================================================
-- MODULE 11: DELIVERY CHALLAN & DEBIT NOTES â€” NEW
-- ================================================================================

-- 11.1 Delivery Challans
CREATE TABLE IF NOT EXISTS qc_delivery_challans (
    id SERIAL PRIMARY KEY,
    dc_number VARCHAR(50) UNIQUE NOT NULL,
    dc_date DATE NOT NULL DEFAULT CURRENT_DATE,
    vendor_return_id INTEGER NOT NULL REFERENCES qc_vendor_returns(id),
    vendor_id INTEGER NOT NULL REFERENCES qc_vendors(id),
    vendor_name VARCHAR(200),
    vendor_address TEXT,
    source_location_id INTEGER REFERENCES qc_locations(id),    -- Quarantine
    transport_mode VARCHAR(50),
    vehicle_number VARCHAR(50),
    courier_name VARCHAR(200),
    tracking_number VARCHAR(100),
    total_packages INTEGER,
    total_weight DECIMAL(15,3),
    total_amount DECIMAL(15,2),
    status VARCHAR(20) DEFAULT 'draft',      -- 'draft', 'generated', 'dispatched', 'delivered'
    dispatched_date TIMESTAMP WITH TIME ZONE,
    dispatched_by VARCHAR(100),
    delivered_date TIMESTAMP WITH TIME ZONE,
    odoo_picking_id INTEGER,
    pdf_path VARCHAR(500),
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100)
);
CREATE INDEX idx_dc_return ON qc_delivery_challans(vendor_return_id);
CREATE INDEX idx_dc_vendor ON qc_delivery_challans(vendor_id);

-- 11.2 Delivery Challan Items
CREATE TABLE IF NOT EXISTS qc_delivery_challan_items (
    id SERIAL PRIMARY KEY,
    delivery_challan_id INTEGER NOT NULL REFERENCES qc_delivery_challans(id) ON DELETE CASCADE,
    vendor_return_item_id INTEGER REFERENCES qc_vendor_return_items(id),
    component_id INTEGER REFERENCES qc_component_master(id),
    part_code VARCHAR(100),
    part_name VARCHAR(300),
    quantity DECIMAL(15,3) NOT NULL,
    uom VARCHAR(20) DEFAULT 'NOS',
    unit_price DECIMAL(15,4),
    line_amount DECIMAL(15,2),
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 11.3 Debit Notes
CREATE TABLE IF NOT EXISTS qc_debit_notes (
    id SERIAL PRIMARY KEY,
    debit_note_number VARCHAR(50) UNIQUE NOT NULL,
    debit_note_date DATE NOT NULL DEFAULT CURRENT_DATE,
    vendor_return_id INTEGER NOT NULL REFERENCES qc_vendor_returns(id),
    delivery_challan_id INTEGER REFERENCES qc_delivery_challans(id),
    vendor_id INTEGER NOT NULL REFERENCES qc_vendors(id),
    original_invoice_number VARCHAR(100),
    original_invoice_date DATE,
    original_invoice_amount DECIMAL(15,2),
    debit_amount DECIMAL(15,2) NOT NULL,
    tax_amount DECIMAL(15,2) DEFAULT 0,
    total_amount DECIMAL(15,2) NOT NULL,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'draft',      -- 'draft', 'generated', 'sent', 'acknowledged'
    approved_by VARCHAR(100),
    approved_date TIMESTAMP WITH TIME ZONE,
    odoo_move_id INTEGER,
    odoo_sync_status VARCHAR(20),
    pdf_path VARCHAR(500),
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100)
);
CREATE INDEX idx_dn_return ON qc_debit_notes(vendor_return_id);
CREATE INDEX idx_dn_vendor ON qc_debit_notes(vendor_id);


-- ================================================================================
-- MODULE 12: WORKFLOW & AUDIT
-- ================================================================================

-- 12.1 Workflow Definitions
CREATE TABLE IF NOT EXISTS qc_workflow_definitions (
    id SERIAL PRIMARY KEY,
    workflow_code VARCHAR(50) UNIQUE NOT NULL,
    workflow_name VARCHAR(200) NOT NULL,
    module VARCHAR(50) NOT NULL,            -- 'grn', 'inspection', 'vendor_return', 'debit_note'
    requires_maker BOOLEAN DEFAULT TRUE,
    requires_checker BOOLEAN DEFAULT TRUE,
    requires_approver BOOLEAN DEFAULT TRUE,
    auto_approve_amount DECIMAL(15,2),
    escalation_hours INTEGER DEFAULT 48,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 12.2 Approval History (Unified across all modules)
CREATE TABLE IF NOT EXISTS qc_approval_history (
    id SERIAL PRIMARY KEY,
    module VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL,            -- 'submit', 'approve', 'reject', 'return_to_maker', 'escalate'
    from_status VARCHAR(50),
    to_status VARCHAR(50),
    action_by VARCHAR(100) NOT NULL,
    action_by_name VARCHAR(200),
    action_role VARCHAR(50),                -- 'maker', 'checker', 'approver'
    action_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    remarks TEXT,
    action_data JSONB
);
CREATE INDEX idx_ah_module_record ON qc_approval_history(module, record_id);
CREATE INDEX idx_ah_action_by ON qc_approval_history(action_by);

-- 12.3 Component History (Change tracking)
CREATE TABLE IF NOT EXISTS qc_component_history (
    id SERIAL PRIMARY KEY,
    component_id INTEGER NOT NULL REFERENCES qc_component_master(id) ON DELETE CASCADE,
    action VARCHAR(20) NOT NULL,
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    change_reason TEXT,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(100)
);
CREATE INDEX idx_ch_component ON qc_component_history(component_id);

-- 12.4 System Audit Log
CREATE TABLE IF NOT EXISTS qc_audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL,            -- 'INSERT', 'UPDATE', 'DELETE'
    old_data JSONB,
    new_data JSONB,
    changed_fields TEXT[],
    user_id VARCHAR(100),
    user_name VARCHAR(200),
    user_role VARCHAR(50),
    user_ip VARCHAR(50),
    action_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_al_table_record ON qc_audit_log(table_name, record_id);
CREATE INDEX idx_al_user ON qc_audit_log(user_id);

-- 12.5 Odoo Sync Log
CREATE TABLE IF NOT EXISTS qc_odoo_sync_log (
    id SERIAL PRIMARY KEY,
    sync_type VARCHAR(50) NOT NULL,         -- 'po_fetch', 'grn_create', 'stock_move', 'return_create', 'debit_note'
    module VARCHAR(50),
    record_id INTEGER,
    odoo_model VARCHAR(100),
    odoo_record_id INTEGER,
    direction VARCHAR(10) NOT NULL,         -- 'inbound', 'outbound'
    request_data JSONB,
    response_data JSONB,
    status VARCHAR(20) NOT NULL,            -- 'success', 'failed', 'pending', 'retry'
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    synced_by VARCHAR(100)
);
CREATE INDEX idx_osl_type ON qc_odoo_sync_log(sync_type);
CREATE INDEX idx_osl_status ON qc_odoo_sync_log(status);


-- ================================================================================
-- MODULE 13: DASHBOARD & REPORTS
-- ================================================================================

-- 13.1 Daily Summary (pre-aggregated for dashboard performance)
CREATE TABLE IF NOT EXISTS qc_daily_summary (
    id SERIAL PRIMARY KEY,
    summary_date DATE NOT NULL UNIQUE,
    gate_entries_count INTEGER DEFAULT 0,
    grn_count INTEGER DEFAULT 0,
    grn_pending INTEGER DEFAULT 0,
    inspections_started INTEGER DEFAULT 0,
    inspections_completed INTEGER DEFAULT 0,
    inspections_pending INTEGER DEFAULT 0,
    pass_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    pass_rate DECIMAL(5,2),
    items_in_quarantine INTEGER DEFAULT 0,
    avg_quarantine_days DECIMAL(5,1),
    returns_initiated INTEGER DEFAULT 0,
    returns_approved INTEGER DEFAULT 0,
    returns_amount DECIMAL(15,2) DEFAULT 0,
    store_transfers INTEGER DEFAULT 0,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 13.2 Vendor Performance (monthly rollup)
CREATE TABLE IF NOT EXISTS qc_vendor_performance (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL REFERENCES qc_vendors(id),
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    total_deliveries INTEGER DEFAULT 0,
    on_time_deliveries INTEGER DEFAULT 0,
    total_lots_inspected INTEGER DEFAULT 0,
    lots_accepted INTEGER DEFAULT 0,
    lots_rejected INTEGER DEFAULT 0,
    total_quantity DECIMAL(15,3) DEFAULT 0,
    accepted_quantity DECIMAL(15,3) DEFAULT 0,
    rejected_quantity DECIMAL(15,3) DEFAULT 0,
    acceptance_rate DECIMAL(5,2),
    on_time_rate DECIMAL(5,2),
    return_count INTEGER DEFAULT 0,
    return_amount DECIMAL(15,2) DEFAULT 0,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(vendor_id, period_year, period_month)
);
CREATE INDEX idx_vp_vendor ON qc_vendor_performance(vendor_id);


-- ================================================================================
-- MODULE 14: NOTIFICATIONS
-- ================================================================================

-- 14.1 Notifications
CREATE TABLE IF NOT EXISTS qc_notifications (
    id SERIAL PRIMARY KEY,
    notification_type VARCHAR(50) NOT NULL,  -- 'approval_pending', 'inspection_due', 'overdue', 'return_status', 'system'
    module VARCHAR(50),
    record_id INTEGER,
    title VARCHAR(300) NOT NULL,
    message TEXT,
    priority VARCHAR(20) DEFAULT 'normal',   -- 'low', 'normal', 'high', 'urgent'
    recipient_user_id INTEGER REFERENCES qc_users(id),
    recipient_role VARCHAR(50),
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    is_email_sent BOOLEAN DEFAULT FALSE,
    email_sent_at TIMESTAMP WITH TIME ZONE,
    action_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_notif_recipient ON qc_notifications(recipient_user_id);
CREATE INDEX idx_notif_unread ON qc_notifications(recipient_user_id, is_read) WHERE is_read = FALSE;


-- ================================================================================
-- TRIGGERS & FUNCTIONS
-- ================================================================================

-- Auto-generate Gate Entry Number
CREATE OR REPLACE FUNCTION fn_generate_gate_entry_number()
RETURNS TRIGGER AS $$
DECLARE yr VARCHAR(4); num INTEGER;
BEGIN
    yr := TO_CHAR(CURRENT_DATE, 'YYYY');
    SELECT COALESCE(MAX(CAST(SUBSTRING(gate_entry_number FROM 9) AS INTEGER)), 0) + 1 INTO num
    FROM qc_gate_entries WHERE gate_entry_number LIKE 'GE-' || yr || '-%';
    NEW.gate_entry_number := 'GE-' || yr || '-' || LPAD(num::TEXT, 5, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_gate_entry_number BEFORE INSERT ON qc_gate_entries
    FOR EACH ROW WHEN (NEW.gate_entry_number IS NULL) EXECUTE FUNCTION fn_generate_gate_entry_number();

-- Auto-generate Component Code
CREATE OR REPLACE FUNCTION fn_generate_component_code()
RETURNS TRIGGER AS $$
BEGIN
    SELECT 'COMP-' || LPAD((COALESCE(MAX(CAST(SUBSTRING(component_code FROM 6) AS INTEGER)), 0) + 1)::TEXT, 3, '0')
    INTO NEW.component_code FROM qc_component_master;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_component_code BEFORE INSERT ON qc_component_master
    FOR EACH ROW WHEN (NEW.component_code IS NULL) EXECUTE FUNCTION fn_generate_component_code();

-- Auto-generate GRN Number
CREATE OR REPLACE FUNCTION fn_generate_grn_number()
RETURNS TRIGGER AS $$
DECLARE yr VARCHAR(4); num INTEGER;
BEGIN
    yr := TO_CHAR(CURRENT_DATE, 'YYYY');
    SELECT COALESCE(MAX(CAST(SUBSTRING(grn_number FROM 10) AS INTEGER)), 0) + 1 INTO num
    FROM qc_grn WHERE grn_number LIKE 'GRN-' || yr || '-%';
    NEW.grn_number := 'GRN-' || yr || '-' || LPAD(num::TEXT, 5, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_grn_number BEFORE INSERT ON qc_grn
    FOR EACH ROW WHEN (NEW.grn_number IS NULL) EXECUTE FUNCTION fn_generate_grn_number();

-- Auto-generate Queue Number
CREATE OR REPLACE FUNCTION fn_generate_queue_number()
RETURNS TRIGGER AS $$
DECLARE yr VARCHAR(4); num INTEGER;
BEGIN
    yr := TO_CHAR(CURRENT_DATE, 'YYYY');
    SELECT COALESCE(MAX(CAST(SUBSTRING(queue_number FROM 9) AS INTEGER)), 0) + 1 INTO num
    FROM qc_inspection_queue WHERE queue_number LIKE 'QC-' || yr || '-%';
    NEW.queue_number := 'QC-' || yr || '-' || LPAD(num::TEXT, 5, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_queue_number BEFORE INSERT ON qc_inspection_queue
    FOR EACH ROW WHEN (NEW.queue_number IS NULL) EXECUTE FUNCTION fn_generate_queue_number();

-- Auto-generate IR Result Number
CREATE OR REPLACE FUNCTION fn_generate_result_number()
RETURNS TRIGGER AS $$
DECLARE yr VARCHAR(4); num INTEGER;
BEGIN
    yr := TO_CHAR(CURRENT_DATE, 'YYYY');
    SELECT COALESCE(MAX(CAST(SUBSTRING(result_number FROM 9) AS INTEGER)), 0) + 1 INTO num
    FROM qc_inspection_results WHERE result_number LIKE 'IR-' || yr || '-%';
    NEW.result_number := 'IR-' || yr || '-' || LPAD(num::TEXT, 5, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_result_number BEFORE INSERT ON qc_inspection_results
    FOR EACH ROW WHEN (NEW.result_number IS NULL) EXECUTE FUNCTION fn_generate_result_number();

-- Auto-generate Vendor Return Number
CREATE OR REPLACE FUNCTION fn_generate_return_number()
RETURNS TRIGGER AS $$
DECLARE yr VARCHAR(4); num INTEGER;
BEGIN
    yr := TO_CHAR(CURRENT_DATE, 'YYYY');
    SELECT COALESCE(MAX(CAST(SUBSTRING(return_number FROM 9) AS INTEGER)), 0) + 1 INTO num
    FROM qc_vendor_returns WHERE return_number LIKE 'VR-' || yr || '-%';
    NEW.return_number := 'VR-' || yr || '-' || LPAD(num::TEXT, 5, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_return_number BEFORE INSERT ON qc_vendor_returns
    FOR EACH ROW WHEN (NEW.return_number IS NULL) EXECUTE FUNCTION fn_generate_return_number();

-- Auto-generate Store Transfer Number
CREATE OR REPLACE FUNCTION fn_generate_transfer_number()
RETURNS TRIGGER AS $$
DECLARE yr VARCHAR(4); num INTEGER;
BEGIN
    yr := TO_CHAR(CURRENT_DATE, 'YYYY');
    SELECT COALESCE(MAX(CAST(SUBSTRING(transfer_number FROM 9) AS INTEGER)), 0) + 1 INTO num
    FROM qc_store_transfers WHERE transfer_number LIKE 'ST-' || yr || '-%';
    NEW.transfer_number := 'ST-' || yr || '-' || LPAD(num::TEXT, 5, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_transfer_number BEFORE INSERT ON qc_store_transfers
    FOR EACH ROW WHEN (NEW.transfer_number IS NULL) EXECUTE FUNCTION fn_generate_transfer_number();

-- Auto-generate IR Report Number
CREATE OR REPLACE FUNCTION fn_generate_ir_number()
RETURNS TRIGGER AS $$
DECLARE yr VARCHAR(4); num INTEGER;
BEGIN
    yr := TO_CHAR(CURRENT_DATE, 'YYYY');
    SELECT COALESCE(MAX(CAST(SUBSTRING(ir_number FROM 10) AS INTEGER)), 0) + 1 INTO num
    FROM qc_inspection_reports WHERE ir_number LIKE 'IRP-' || yr || '-%';
    NEW.ir_number := 'IRP-' || yr || '-' || LPAD(num::TEXT, 5, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ir_number BEFORE INSERT ON qc_inspection_reports
    FOR EACH ROW WHEN (NEW.ir_number IS NULL) EXECUTE FUNCTION fn_generate_ir_number();

-- Auto-update Timestamps
CREATE OR REPLACE FUNCTION fn_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_cm_ts BEFORE UPDATE ON qc_component_master FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();
CREATE TRIGGER trg_grn_ts BEFORE UPDATE ON qc_grn FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();
CREATE TRIGGER trg_iq_ts BEFORE UPDATE ON qc_inspection_queue FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();
CREATE TRIGGER trg_vr_ts BEFORE UPDATE ON qc_vendor_returns FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();
CREATE TRIGGER trg_vnd_ts BEFORE UPDATE ON qc_vendors FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();
CREATE TRIGGER trg_ge_ts BEFORE UPDATE ON qc_gate_entries FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();
CREATE TRIGGER trg_st_ts BEFORE UPDATE ON qc_store_transfers FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();
CREATE TRIGGER trg_dc_ts BEFORE UPDATE ON qc_delivery_challans FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();
CREATE TRIGGER trg_dept_ts BEFORE UPDATE ON qc_departments FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();


-- ================================================================================
-- VIEWS
-- ================================================================================

-- V1: Component List View
CREATE OR REPLACE VIEW vw_component_list AS
SELECT c.id, c.component_code, c.part_code, c.part_name, c.status, c.qc_required,
    c.default_inspection_type, c.pr_process_code,
    cat.category_code AS product_category, cat.category_name,
    pg.group_name AS product_group,
    qp.plan_code AS qc_plan_no, qp.plan_name AS qc_plan_name,
    v.vendor_name AS primary_vendor,
    d.department_name,
    (SELECT COUNT(*) FROM qc_component_checking_params WHERE component_id = c.id AND is_active) AS checkpoints
FROM qc_component_master c
LEFT JOIN qc_product_categories cat ON c.category_id = cat.id
LEFT JOIN qc_product_groups pg ON c.product_group_id = pg.id
LEFT JOIN qc_plans qp ON c.qc_plan_id = qp.id
LEFT JOIN qc_vendors v ON c.primary_vendor_id = v.id
LEFT JOIN qc_departments d ON c.department_id = d.id
WHERE c.is_deleted = FALSE;

-- V2: Inspection Queue View (FIFO ordered)
CREATE OR REPLACE VIEW vw_inspection_queue AS
SELECT iq.id, iq.queue_number, iq.status, iq.priority, iq.lot_size, iq.sample_size,
    iq.inspection_type, iq.assigned_to, iq.due_date, iq.days_in_quarantine,
    iq.visual_result, iq.functional_result, iq.overall_result,
    g.grn_number, g.grn_date,
    c.part_code, c.part_name,
    v.vendor_name,
    iq.created_at AS queued_at
FROM qc_inspection_queue iq
JOIN qc_grn g ON iq.grn_id = g.id
JOIN qc_component_master c ON iq.component_id = c.id
LEFT JOIN qc_vendors v ON g.vendor_id = v.id
ORDER BY iq.priority ASC, iq.created_at ASC;

-- V3: GRN List View
CREATE OR REPLACE VIEW vw_grn_list AS
SELECT g.id, g.grn_number, g.grn_date, g.status, g.qc_status, g.po_number,
    g.invoice_number, g.bill_number,
    v.vendor_name, v.vendor_code,
    ge.gate_entry_number, ge.gatepass_number,
    COUNT(gi.id) AS line_count,
    SUM(gi.received_quantity) AS total_qty,
    SUM(gi.accepted_quantity) AS total_accepted,
    SUM(gi.rejected_quantity) AS total_rejected
FROM qc_grn g
JOIN qc_vendors v ON g.vendor_id = v.id
LEFT JOIN qc_gate_entries ge ON g.gate_entry_id = ge.id
LEFT JOIN qc_grn_items gi ON g.id = gi.grn_id
GROUP BY g.id, v.vendor_name, v.vendor_code, ge.gate_entry_number, ge.gatepass_number;

-- V4: Gate Entry View
CREATE OR REPLACE VIEW vw_gate_entries AS
SELECT ge.id, ge.gate_entry_number, ge.inward_register_number, ge.entry_date,
    ge.gatepass_number, ge.status, ge.quantity_match_status,
    v.vendor_name, v.vendor_code,
    ge.po_number, ge.invoice_number,
    COUNT(gei.id) AS item_count,
    SUM(gei.received_quantity) AS total_received_qty
FROM qc_gate_entries ge
JOIN qc_vendors v ON ge.vendor_id = v.id
LEFT JOIN qc_gate_entry_items gei ON ge.id = gei.gate_entry_id
GROUP BY ge.id, v.vendor_name, v.vendor_code;

-- V5: Pending Approvals (for Checker/Approver dashboard)
CREATE OR REPLACE VIEW vw_pending_approvals AS
SELECT 'vendor_return' AS module, vr.id AS record_id, vr.return_number AS doc_number,
    vr.status, vr.return_date AS doc_date, v.vendor_name,
    vr.total_return_amount AS amount, vr.maker_name
FROM qc_vendor_returns vr
JOIN qc_vendors v ON vr.vendor_id = v.id
WHERE vr.status IN ('submitted', 'checker_review', 'approver_review')
UNION ALL
SELECT 'inspection_report', ir.id, ir.ir_number, ir.status, ir.ir_date, v.vendor_name,
    NULL, ir.maker_name
FROM qc_inspection_reports ir
JOIN qc_vendors v ON ir.vendor_id = v.id
WHERE ir.status IN ('submitted');

-- V6: Vendor Return Summary
CREATE OR REPLACE VIEW vw_vendor_returns AS
SELECT vr.id, vr.return_number, vr.return_date, vr.return_type, vr.status,
    vr.total_return_qty, vr.total_return_amount,
    v.vendor_name, g.grn_number, vr.po_number,
    vr.maker_name, vr.checker_name, vr.approver_name,
    dc.dc_number, dn.debit_note_number
FROM qc_vendor_returns vr
JOIN qc_vendors v ON vr.vendor_id = v.id
JOIN qc_grn g ON vr.grn_id = g.id
LEFT JOIN qc_delivery_challans dc ON dc.vendor_return_id = vr.id
LEFT JOIN qc_debit_notes dn ON dn.vendor_return_id = vr.id;

-- V7: Dashboard Metrics
CREATE OR REPLACE VIEW vw_dashboard_metrics AS
SELECT
    (SELECT COUNT(*) FROM qc_inspection_queue WHERE status = 'pending') AS pending_inspections,
    (SELECT COUNT(*) FROM qc_inspection_queue WHERE status = 'in_progress') AS active_inspections,
    (SELECT COUNT(*) FROM qc_inspection_queue WHERE is_overdue = TRUE) AS overdue_inspections,
    (SELECT COUNT(*) FROM qc_vendor_returns WHERE status IN ('submitted','checker_review','approver_review')) AS pending_approvals,
    (SELECT COUNT(*) FROM qc_grn WHERE qc_status = 'pending') AS grn_pending_qc,
    (SELECT COUNT(*) FROM qc_gate_entries WHERE status = 'pending') AS pending_gate_entries;


-- ================================================================================
-- SEED / INSERT DATA
-- ================================================================================

-- ============ MODULE 1: DEPARTMENTS, USERS, ROLES ============

INSERT INTO qc_departments (department_code, department_name, pass_source_location, pass_destination_location, fail_source_location, fail_destination_location, description) VALUES
('DEPT-QC',     'Quality Control',       'QC Quarantine',    'Main Store',       'QC Quarantine',    'Vendor Return Bay',    'Primary QC department for B-SCAN'),
('DEPT-STORE',  'Stores & Inventory',    'Receiving Bay',    'Main Store',       'Receiving Bay',    'QC Quarantine',        'Inventory and material management'),
('DEPT-PROD',   'Production',            'Main Store',       'Production Floor', 'Main Store',       'QC Quarantine',        'B-SCAN production department'),
('DEPT-FIN',    'Finance',               NULL,               NULL,               NULL,               NULL,                   'Finance and accounts'),
('DEPT-GATE',   'Security & Gate',       NULL,               NULL,               NULL,               NULL,                   'Gate entry and security');

INSERT INTO qc_roles (role_code, role_name, description, is_system_role) VALUES
('admin',    'Administrator',    'Full system access, configuration, user management',              TRUE),
('maker',    'Maker / QC Inspector', 'Create inspections, gate entries, initiate returns',          TRUE),
('checker',  'Checker / QC Manager', 'Review and validate inspections, approve/reject returns',     TRUE),
('approver', 'Approver / Finance',   'Final approval for debit notes and high-value returns',       TRUE),
('viewer',   'Viewer / Regulatory',  'Read-only access to QC records and compliance reports',       TRUE),
('gate_entry','Gate Entry Operator',  'Gate entry and quantity verification access only',            TRUE),
('store_keeper','Store Keeper',       'View approved items, acknowledge store transfers',            TRUE);

INSERT INTO qc_users (user_code, user_name, email, phone, department_id, designation, employee_id) VALUES
('USR-001', 'Rajesh Kumar',         'rajesh.kumar@appasamy.com',     '9876543210', 1, 'QC Manager',           'EMP-101'),
('USR-002', 'Priya Sharma',         'priya.sharma@appasamy.com',     '9876543211', 1, 'Senior QC Inspector',  'EMP-102'),
('USR-003', 'Anand Krishnan',       'anand.krishnan@appasamy.com',   '9876543212', 1, 'QC Inspector',         'EMP-103'),
('USR-004', 'Meera Venkatesh',      'meera.venkatesh@appasamy.com',  '9876543213', 4, 'Finance Manager',      'EMP-201'),
('USR-005', 'Suresh Babu',          'suresh.babu@appasamy.com',      '9876543214', 2, 'Store Keeper',         'EMP-301'),
('USR-006', 'Karthik Rajan',        'karthik.rajan@appasamy.com',    '9876543215', 5, 'Security Guard',       'EMP-401'),
('USR-007', 'Lakshmi Narayanan',    'lakshmi.n@appasamy.com',        '9876543216', 1, 'QA Manager',           'EMP-104'),
('USR-008', 'System Admin',         'admin@appasamy.com',            '9876543200', 1, 'System Administrator', 'EMP-001');

-- User-Role Mappings
INSERT INTO qc_user_roles (user_id, role_id, department_id, assigned_by) VALUES
(8, 1, 1, 'SYSTEM'),     -- Admin â†’ admin role
(1, 3, 1, 'SYSTEM'),     -- Rajesh â†’ checker (QC Manager)
(2, 2, 1, 'SYSTEM'),     -- Priya â†’ maker (Sr QC Inspector)
(3, 2, 1, 'SYSTEM'),     -- Anand â†’ maker (QC Inspector)
(4, 4, 4, 'SYSTEM'),     -- Meera â†’ approver (Finance)
(5, 7, 2, 'SYSTEM'),     -- Suresh â†’ store_keeper
(6, 6, 5, 'SYSTEM'),     -- Karthik â†’ gate_entry
(7, 3, 1, 'SYSTEM'),     -- Lakshmi â†’ checker (QA Manager)
(7, 5, 1, 'SYSTEM');     -- Lakshmi also â†’ viewer (regulatory oversight)

-- Permissions
INSERT INTO qc_permissions (permission_code, permission_name, module) VALUES
('config.manage',       'Manage QC Configuration',      'config'),
('gate_entry.manage',   'Gate Entry Operations',         'gate_entry'),
('grn.manage',          'GRN Processing',                'grn'),
('inspection.execute',  'Execute Inspections',           'inspection'),
('inspection.verify',   'Verify Inspection Results',     'inspection'),
('ir.generate',         'Generate Inspection Reports',   'inspection_report'),
('ir.approve',          'Approve Inspection Reports',    'inspection_report'),
('return.initiate',     'Initiate Vendor Returns',       'vendor_return'),
('return.approve',      'Approve Vendor Returns',        'vendor_return'),
('return.final_approve','Final Approve (Debit Notes)',   'vendor_return'),
('transfer.initiate',   'Initiate Store Transfers',      'store_transfer'),
('transfer.acknowledge','Acknowledge Store Transfers',   'store_transfer'),
('dashboard.view',      'View QC Dashboard',             'dashboard'),
('reports.generate',    'Generate QC Reports',           'reports'),
('reports.export',      'Export Reports (PDF/Excel)',     'reports');

-- Role-Permission Mappings (Admin gets everything)
INSERT INTO qc_role_permissions (role_id, permission_id, can_create, can_read, can_update, can_delete, can_approve) VALUES
-- Admin (all permissions, full CRUD)
(1, 1,  TRUE, TRUE, TRUE, TRUE, TRUE),
(1, 2,  TRUE, TRUE, TRUE, TRUE, TRUE),
(1, 3,  TRUE, TRUE, TRUE, TRUE, TRUE),
(1, 4,  TRUE, TRUE, TRUE, TRUE, TRUE),
(1, 5,  TRUE, TRUE, TRUE, TRUE, TRUE),
(1, 6,  TRUE, TRUE, TRUE, TRUE, TRUE),
(1, 7,  TRUE, TRUE, TRUE, TRUE, TRUE),
(1, 8,  TRUE, TRUE, TRUE, TRUE, TRUE),
(1, 9,  TRUE, TRUE, TRUE, TRUE, TRUE),
(1, 10, TRUE, TRUE, TRUE, TRUE, TRUE),
(1, 11, TRUE, TRUE, TRUE, TRUE, TRUE),
(1, 12, TRUE, TRUE, TRUE, TRUE, TRUE),
(1, 13, TRUE, TRUE, TRUE, TRUE, TRUE),
(1, 14, TRUE, TRUE, TRUE, TRUE, TRUE),
(1, 15, TRUE, TRUE, TRUE, TRUE, TRUE),
-- Maker (QC Inspector)
(2, 4,  TRUE, TRUE, TRUE, FALSE, FALSE),   -- Execute inspections
(2, 6,  TRUE, TRUE, FALSE, FALSE, FALSE),  -- Generate IR
(2, 8,  TRUE, TRUE, TRUE, FALSE, FALSE),   -- Initiate returns
(2, 11, TRUE, TRUE, FALSE, FALSE, FALSE),  -- Initiate transfers
(2, 13, FALSE, TRUE, FALSE, FALSE, FALSE), -- View dashboard
-- Checker (QC Manager)
(3, 1,  TRUE, TRUE, TRUE, FALSE, FALSE),   -- Manage config
(3, 4,  FALSE, TRUE, FALSE, FALSE, FALSE), -- View inspections
(3, 5,  FALSE, TRUE, FALSE, FALSE, TRUE),  -- Verify inspections
(3, 7,  FALSE, TRUE, FALSE, FALSE, TRUE),  -- Approve IR
(3, 9,  FALSE, TRUE, FALSE, FALSE, TRUE),  -- Approve returns
(3, 13, FALSE, TRUE, FALSE, FALSE, FALSE), -- Dashboard
(3, 14, FALSE, TRUE, FALSE, FALSE, FALSE), -- Reports
(3, 15, FALSE, TRUE, FALSE, FALSE, FALSE), -- Export
-- Approver (Finance)
(4, 10, FALSE, TRUE, FALSE, FALSE, TRUE),  -- Final approve debit notes
(4, 13, FALSE, TRUE, FALSE, FALSE, FALSE), -- Dashboard
(4, 14, FALSE, TRUE, FALSE, FALSE, FALSE), -- Reports
-- Gate Entry Operator
(6, 2,  TRUE, TRUE, TRUE, FALSE, FALSE),   -- Gate entry operations
-- Store Keeper
(7, 12, FALSE, TRUE, FALSE, FALSE, TRUE);  -- Acknowledge transfers

-- System Config
INSERT INTO qc_system_config (config_key, config_value, config_type, module, description) VALUES
('app.name',                    'Appasamy QC Application',  'string',  'system',     'Application name'),
('app.version',                 '1.0.0',                    'string',  'system',     'Current version'),
('odoo.base_url',               'https://odoo.appasamy.com','string',  'integration','Odoo server URL'),
('odoo.api_mode',               'mock',                     'string',  'integration','API mode: mock or real'),
('grn.auto_quarantine',         'true',                     'boolean', 'grn',        'Auto-move QC items to quarantine'),
('grn.fifo_enabled',            'true',                     'boolean', 'grn',        'FIFO ordering for GRN processing'),
('inspection.overdue_days',     '7',                        'number',  'inspection', 'Days before inspection marked overdue'),
('inspection.skip_lot_enabled', 'true',                     'boolean', 'inspection', 'Enable skip lot logic globally'),
('return.auto_approve_limit',   '5000',                     'number',  'return',     'Auto-approve returns below this amount (INR)'),
('notification.email_enabled',  'true',                     'boolean', 'notification','Enable email notifications'),
('auth.sso_enabled',            'false',                    'boolean', 'auth',       'Office 365 SSO enabled'),
('auth.session_timeout_mins',   '480',                      'number',  'auth',       'Session timeout in minutes');


-- ============ MODULE 2: MASTER DATA ============

INSERT INTO qc_product_categories (category_code, category_name, icon, sort_order) VALUES
('CAT-ELEC',  'Electronic Components',  'âš¡', 1),
('CAT-MECH',  'Mechanical Parts',       'âš™ï¸', 2),
('CAT-OPT',   'Optical Components',     'ðŸ”¬', 3),
('CAT-PKG',   'Packaging Materials',    'ðŸ“¦', 4),
('CAT-CHEM',  'Chemical & Consumables', 'ðŸ§ª', 5),
('CAT-RAW',   'Raw Materials',          'ðŸ—ï¸', 6);

INSERT INTO qc_product_groups (category_id, group_code, group_name, sort_order) VALUES
(1, 'GRP-PCB',    'PCB Assemblies',         1),
(1, 'GRP-SENSOR', 'Sensors & Transducers',  2),
(1, 'GRP-CONN',   'Connectors & Cables',    3),
(2, 'GRP-ENCL',   'Enclosures & Housings',  1),
(2, 'GRP-FAST',   'Fasteners & Hardware',    2),
(3, 'GRP-LENS',   'Lenses & Optics',        1),
(3, 'GRP-DISP',   'Displays & Screens',     2),
(4, 'GRP-BOX',    'Packaging Boxes',         1),
(5, 'GRP-GEL',    'Ultrasound Gel',          1);

INSERT INTO qc_units (unit_code, unit_name, unit_symbol, unit_type) VALUES
('MM',      'Millimeter',       'mm',   'length'),
('CM',      'Centimeter',       'cm',   'length'),
('M',       'Meter',            'm',    'length'),
('INCH',    'Inch',             'in',   'length'),
('G',       'Gram',             'g',    'weight'),
('KG',      'Kilogram',         'kg',   'weight'),
('NOS',     'Numbers',          'nos',  'count'),
('SET',     'Set',              'set',  'count'),
('V',       'Volt',             'V',    'electrical'),
('A',       'Ampere',           'A',    'electrical'),
('OHM',     'Ohm',              'Î©',    'electrical'),
('DEG',     'Degree',           'Â°',    'angle'),
('MHZ',     'Megahertz',        'MHz',  'frequency'),
('ML',      'Milliliter',       'ml',   'volume'),
('PCT',     'Percentage',       '%',    'ratio');

INSERT INTO qc_instruments (instrument_code, instrument_name, instrument_type, make, model, serial_number, calibration_due_date, department_id) VALUES
('INS-VMC-001', 'Vernier Caliper 150mm',       'Caliper',      'Mitutoyo',     'CD-15APX',     'MT-2024-001', '2026-06-15', 1),
('INS-MIC-001', 'Outside Micrometer 25mm',     'Micrometer',   'Mitutoyo',     'MDC-25MX',     'MT-2024-002', '2026-06-15', 1),
('INS-DGI-001', 'Digital Indicator',            'Indicator',    'Mitutoyo',     'ID-C125XB',    'MT-2024-003', '2026-07-20', 1),
('INS-MSC-001', 'Digital Multimeter',           'Multimeter',   'Fluke',        '87V',          'FK-2024-001', '2026-08-10', 1),
('INS-UST-001', 'Ultrasound Tester B-SCAN',    'US Tester',    'Appasamy',     'BST-2000',     'AP-2024-001', '2026-09-01', 1),
('INS-WGH-001', 'Precision Weighing Scale',    'Scale',        'AND',          'GX-2000',      'AND-2024-01', '2026-07-01', 1),
('INS-HRD-001', 'Hardness Tester',             'Hardness',     'Rockwell',     'HR-150A',      'RW-2024-001', '2026-08-15', 1);

INSERT INTO qc_vendors (vendor_code, vendor_name, vendor_type, contact_person, email, phone, city, state, gst_number, is_approved, odoo_partner_id) VALUES
('VND-001', 'Sri Lakshmi Electronics Pvt Ltd',  'supplier', 'Ravi Kumar',       'ravi@srilakshmi.com',      '044-28561234', 'Chennai',      'Tamil Nadu',   '33AABCS1234F1Z5',  TRUE,  1001),
('VND-002', 'Precision Optics India',           'supplier', 'Sudhir Menon',     'sudhir@precisionoptics.in','044-28567890', 'Chennai',      'Tamil Nadu',   '33AABCP5678G1Z8',  TRUE,  1002),
('VND-003', 'MechParts Manufacturing',          'supplier', 'Ganesh Iyer',      'ganesh@mechparts.co.in',   '080-41234567', 'Bangalore',    'Karnataka',    '29AABCM9012H1Z2',  TRUE,  1003),
('VND-004', 'TechBoard Solutions',              'supplier', 'Amit Shah',        'amit@techboard.in',        '022-67891234', 'Mumbai',       'Maharashtra',  '27AABCT3456I1Z6',  TRUE,  1004),
('VND-005', 'GreenPack India',                  'supplier', 'Sonia Gupta',      'sonia@greenpack.in',       '011-45678901', 'New Delhi',    'Delhi',        '07AABCG7890J1Z9',  TRUE,  1005);

INSERT INTO qc_sampling_plans (plan_code, plan_name, plan_type, aql_level, inspection_level) VALUES
('SP-001', 'Standard Sampling SP0',  'sp0', '1.0',  'normal'),
('SP-002', 'Standard Sampling SP1',  'sp1', '1.5',  'normal'),
('SP-003', 'Tightened Sampling SP2', 'sp2', '0.65', 'tightened'),
('SP-004', 'Reduced Sampling SP3',   'sp3', '2.5',  'reduced');

INSERT INTO qc_sampling_plan_details (sampling_plan_id, lot_size_min, lot_size_max, sample_size, accept_number, reject_number) VALUES
(1, 2, 8, 2, 0, 1),    (1, 9, 15, 3, 0, 1),     (1, 16, 25, 5, 0, 1),
(1, 26, 50, 8, 0, 1),   (1, 51, 90, 13, 1, 2),   (1, 91, 150, 20, 1, 2),
(1, 151, 280, 32, 2, 3),(1, 281, 500, 50, 3, 4),  (1, 501, 1200, 80, 5, 6),
(2, 2, 8, 3, 0, 1),    (2, 9, 15, 5, 0, 1),     (2, 16, 25, 8, 1, 2),
(2, 26, 50, 13, 1, 2),  (2, 51, 90, 20, 2, 3),   (2, 91, 150, 32, 3, 4),
(3, 2, 8, 3, 0, 1),    (3, 9, 15, 5, 0, 1),     (3, 16, 25, 8, 0, 1),
(3, 26, 50, 13, 1, 2),  (3, 51, 90, 20, 1, 2),   (3, 91, 150, 32, 2, 3);

INSERT INTO qc_defect_types (defect_code, defect_name, defect_category, severity_level) VALUES
('DEF-SCR',  'Surface Scratch',           'visual',     1),
('DEF-DENT', 'Dent / Deformation',        'visual',     2),
('DEF-DIM',  'Dimension Out of Spec',     'dimensional',3),
('DEF-FUNC', 'Functional Failure',        'functional', 3),
('DEF-CORR', 'Corrosion / Rust',          'visual',     2),
('DEF-MIS',  'Missing Component',         'assembly',   3),
('DEF-COLOR','Color Mismatch',            'visual',     1),
('DEF-ELEC', 'Electrical Failure',        'functional', 3),
('DEF-SEAL', 'Seal / Gasket Issue',       'assembly',   2),
('DEF-CAL',  'Calibration Drift',         'measurement',2);

INSERT INTO qc_rejection_reasons (reason_code, reason_name, reason_category) VALUES
('REJ-DIM',    'Dimensional Non-Conformance',   'quality'),
('REJ-VISUAL', 'Visual Defect',                  'quality'),
('REJ-FUNC',   'Functional Failure',             'quality'),
('REJ-MAT',    'Wrong Material',                 'material'),
('REJ-QTY',    'Quantity Shortage',              'logistics'),
('REJ-DOC',    'Missing Documentation',          'documentation'),
('REJ-PKG',    'Packaging Damage',               'logistics'),
('REJ-EXP',    'Expired / Near Expiry',          'shelf_life'),
('REJ-CONT',   'Contamination',                  'quality'),
('REJ-SPEC',   'Specification Mismatch',         'quality');

INSERT INTO qc_locations (location_code, location_name, location_type, warehouse_name, is_quarantine, is_restricted, odoo_location_id) VALUES
('LOC-GATE',    'Gate Entry Area',          'gate',         'Main Warehouse',   FALSE, FALSE, 2001),
('LOC-RCV',     'Receiving Bay',            'receiving',    'Main Warehouse',   FALSE, FALSE, 2002),
('LOC-QRT',     'QC Quarantine Zone',       'quarantine',   'Main Warehouse',   TRUE,  TRUE,  2003),
('LOC-STORE-A', 'Main Store - Section A',   'store',        'Main Warehouse',   FALSE, FALSE, 2004),
('LOC-STORE-B', 'Main Store - Section B',   'store',        'Main Warehouse',   FALSE, FALSE, 2005),
('LOC-RET',     'Vendor Return Bay',        'vendor',       'Main Warehouse',   FALSE, FALSE, 2006),
('LOC-PROD',    'Production Floor',         'production',   'Production',       FALSE, FALSE, 2007);


-- ============ MODULE 3: QC PLANS ============

INSERT INTO qc_plans (plan_code, plan_name, revision, revision_date, effective_date, inspection_stages, requires_visual, requires_functional, status, is_active) VALUES
('RD.7.3-07',  'B-SCAN Transducer QC Plan',        'Rev-03', '2025-12-01', '2026-01-01', 2, TRUE, TRUE,  'active', TRUE),
('A12',        'PCB Assembly QC Plan',              'Rev-02', '2025-11-15', '2026-01-01', 2, TRUE, TRUE,  'active', TRUE),
('RD.7.3-08',  'Optical Lens QC Plan',              'Rev-01', '2025-10-01', '2025-11-01', 1, TRUE, FALSE, 'active', TRUE),
('RD.7.3-09',  'Enclosure QC Plan',                 'Rev-01', '2025-12-15', '2026-01-15', 2, TRUE, TRUE,  'active', TRUE),
('PKG-QP-01',  'Packaging Material QC Plan',        'Rev-01', '2025-09-01', '2025-10-01', 1, TRUE, FALSE, 'active', TRUE);

INSERT INTO qc_plan_stages (qc_plan_id, stage_code, stage_name, stage_type, stage_sequence, inspection_type, sampling_plan_id, is_mandatory, requires_instrument) VALUES
-- B-SCAN Transducer (2 stages: Visual + Functional)
(1, 'STG-VIS', 'Visual Inspection',    'visual',      1, 'sampling', 1, TRUE,  FALSE),
(1, 'STG-FUN', 'Functional Test',      'functional',  2, 'sampling', 1, TRUE,  TRUE),
-- PCB Assembly (2 stages)
(2, 'STG-VIS', 'Visual Inspection',    'visual',      1, '100_percent', NULL, TRUE,  FALSE),
(2, 'STG-FUN', 'Electrical Test',      'functional',  2, '100_percent', NULL, TRUE,  TRUE),
-- Optical Lens (1 stage: Visual only)
(3, 'STG-VIS', 'Visual & Dimensional', 'visual',      1, 'sampling', 2, TRUE,  TRUE),
-- Enclosure (2 stages)
(4, 'STG-VIS', 'Surface & Dimension',  'visual',      1, 'sampling', 1, TRUE,  TRUE),
(4, 'STG-FUN', 'Fit & Assembly Test',  'functional',  2, 'sampling', 1, TRUE,  FALSE),
-- Packaging (1 stage)
(5, 'STG-VIS', 'Visual Check',         'visual',      1, '100_percent', NULL, TRUE,  FALSE);

INSERT INTO qc_plan_parameters (qc_plan_stage_id, parameter_code, parameter_name, checking_type, specification, unit_id, nominal_value, tolerance_min, tolerance_max, instrument_id, input_type, parameter_sequence) VALUES
-- B-SCAN Visual Stage parameters
(1, 'P-VIS-01', 'Surface Finish',          'visual',     'No scratches, dents or discoloration', NULL,  NULL, NULL, NULL, NULL,  'pass_fail', 1),
(1, 'P-VIS-02', 'Label Correctness',       'visual',     'Label matches part code and revision',  NULL,  NULL, NULL, NULL, NULL,  'pass_fail', 2),
(1, 'P-VIS-03', 'Cable Length',            'visual',     '1500 Â± 50 mm',                         1,     1500, 1450, 1550, 1,     'measurement', 3),
(1, 'P-VIS-04', 'Housing Diameter',        'visual',     '38.0 Â± 0.5 mm',                        1,     38.0, 37.5, 38.5, 1,     'measurement', 4),
-- B-SCAN Functional Stage parameters
(2, 'P-FUN-01', 'Frequency Response',      'functional', '3.5 Â± 0.3 MHz',                        13,    3.5,  3.2,  3.8,  5,     'measurement', 1),
(2, 'P-FUN-02', 'Sensitivity (dB)',        'functional', '-6 dB bandwidth > 60%',                 NULL,  60,   60,   100,  5,     'measurement', 2),
(2, 'P-FUN-03', 'Impedance',              'functional', '50 Â± 10 Ohm',                           11,    50,   40,   60,   4,     'measurement', 3),
(2, 'P-FUN-04', 'Beam Profile',           'functional', 'Uniform, no side lobes > -20dB',        NULL,  NULL, NULL, NULL, 5,     'pass_fail', 4),
-- PCB Visual
(3, 'P-PCB-V1', 'Solder Quality',         'visual',     'No cold joints, bridges or voids',      NULL,  NULL, NULL, NULL, NULL,  'pass_fail', 1),
(3, 'P-PCB-V2', 'Component Placement',    'visual',     'All components correctly placed',        NULL,  NULL, NULL, NULL, NULL,  'pass_fail', 2),
-- PCB Functional
(4, 'P-PCB-F1', 'Power Consumption',      'functional', '< 2.5W at 12V',                         9,     2.0,  0,    2.5,  4,     'measurement', 1),
(4, 'P-PCB-F2', 'Signal Output',          'functional', '3.3V Â± 0.1V',                           9,     3.3,  3.2,  3.4,  4,     'measurement', 2),
-- Optical Lens
(5, 'P-OPT-01', 'Lens Diameter',          'visual',     '25.0 Â± 0.1 mm',                         1,     25.0, 24.9, 25.1, 1,     'measurement', 1),
(5, 'P-OPT-02', 'Surface Clarity',        'visual',     'No inclusions, scratches, or haze',     NULL,  NULL, NULL, NULL, NULL,  'pass_fail', 2),
(5, 'P-OPT-03', 'Focal Length',           'visual',     '75 Â± 2 mm',                              1,     75,   73,   77,   3,     'measurement', 3);


-- ============ MODULE 4: COMPONENTS ============

INSERT INTO qc_component_master (component_code, part_code, part_name, category_id, product_group_id, qc_required, qc_plan_id, default_inspection_type, default_sampling_plan_id, test_cert_required, fqir_required, pr_process_code, pr_process_name, primary_vendor_id, department_id, status, created_by) VALUES
('COMP-001', 'BSC-TRD-001', 'B-SCAN Ultrasound Transducer 3.5MHz', 1, 2, TRUE,  1, 'sampling',      1, TRUE,  TRUE,  'direct_purchase', 'Direct Purchase',     1, 1, 'active', 'USR-008'),
('COMP-002', 'BSC-PCB-001', 'Main Control PCB Assembly',           1, 1, TRUE,  2, '100_percent',   NULL, TRUE,  FALSE, 'direct_purchase', 'Direct Purchase',     4, 1, 'active', 'USR-008'),
('COMP-003', 'BSC-LNS-001', 'Acoustic Lens 25mm',                  3, 6, TRUE,  3, 'sampling',      2, FALSE, FALSE, 'direct_purchase', 'Direct Purchase',     2, 1, 'active', 'USR-008'),
('COMP-004', 'BSC-ENC-001', 'Scanner Housing Assembly',             2, 4, TRUE,  4, 'sampling',      1, FALSE, FALSE, 'external_job',    'External Job Work',   3, 1, 'active', 'USR-008'),
('COMP-005', 'BSC-CBL-001', 'Transducer Cable Assembly 1.5m',       1, 3, TRUE,  1, 'sampling',      1, FALSE, FALSE, 'direct_purchase', 'Direct Purchase',     1, 1, 'active', 'USR-008'),
('COMP-006', 'BSC-PKG-001', 'Product Packaging Box (B-SCAN)',       4, 8, TRUE,  5, '100_percent',   NULL, FALSE, FALSE, 'direct_purchase', 'Direct Purchase',     5, 1, 'active', 'USR-008'),
('COMP-007', 'BSC-GEL-001', 'Ultrasound Gel 250ml',                 5, 9, FALSE, NULL,'sampling',    1, FALSE, FALSE, 'direct_purchase', 'Direct Purchase',     5, 1, 'active', 'USR-008');

-- Component Checking Parameters
INSERT INTO qc_component_checking_params (component_id, qc_plan_stage_id, checking_type, checking_point, specification, unit_id, nominal_value, tolerance_min, tolerance_max, instrument_id, instrument_name, input_type, sort_order) VALUES
-- Transducer Visual
(1, 1, 'visual',     'Surface Finish',          'No scratches or dents',               NULL,  NULL, NULL, NULL, NULL,            NULL,                    'pass_fail',    1),
(1, 1, 'visual',     'Cable Length',            '1500 Â± 50 mm',                         1,     1500, 1450, 1550, 1,              'Vernier Caliper 150mm', 'measurement',  2),
(1, 1, 'visual',     'Housing Diameter',        '38.0 Â± 0.5 mm',                        1,     38.0, 37.5, 38.5, 1,              'Vernier Caliper 150mm', 'measurement',  3),
(1, 1, 'visual',     'Connector Type',          'BNC Male, gold plated',                NULL,  NULL, NULL, NULL, NULL,            NULL,                    'pass_fail',    4),
-- Transducer Functional
(1, 2, 'functional', 'Frequency Response',      '3.5 Â± 0.3 MHz',                        13,    3.5,  3.2,  3.8,  5,              'Ultrasound Tester',     'measurement',  1),
(1, 2, 'functional', 'Sensitivity',             '-6 dB bandwidth > 60%',                 15,    60,   60,   100,  5,              'Ultrasound Tester',     'measurement',  2),
(1, 2, 'functional', 'Impedance',              '50 Â± 10 Ohm',                           11,    50,   40,   60,   4,              'Digital Multimeter',    'measurement',  3),
(1, 2, 'functional', 'Beam Profile',           'Uniform pattern, no side lobes',         NULL,  NULL, NULL, NULL, 5,              'Ultrasound Tester',     'pass_fail',    4),
-- PCB Visual
(2, 3, 'visual',     'Solder Quality',         'No cold joints or bridges',              NULL,  NULL, NULL, NULL, NULL,            NULL,                    'pass_fail',    1),
(2, 3, 'visual',     'Component Placement',    'All ICs, resistors correctly placed',    NULL,  NULL, NULL, NULL, NULL,            NULL,                    'pass_fail',    2),
-- PCB Functional
(2, 4, 'functional', 'Power Consumption',      '< 2.5W at 12V',                         9,     2.0,  0,    2.5,  4,              'Digital Multimeter',    'measurement',  1),
(2, 4, 'functional', 'Signal Output Voltage',  '3.3V Â± 0.1V',                           9,     3.3,  3.2,  3.4,  4,              'Digital Multimeter',    'measurement',  2);


-- ============ MODULE 5-6: GATE ENTRY & GRN (Sample Transaction Data) ============

INSERT INTO qc_gate_entries (gate_entry_number, inward_register_number, entry_date, vendor_id, po_number, po_date, odoo_po_id, invoice_number, invoice_date, invoice_amount, vehicle_number, no_of_packages, gatepass_number, gatepass_generated, quantity_verified, quantity_match_status, status, entry_by, verified_by, created_by) VALUES
('GE-2026-00001', 'IR/2026/001', '2026-01-15', 1, 'PO-2026-0101', '2026-01-05', 5001, 'INV-SLE-2026-045', '2026-01-14', 125000.00, 'TN-01-AB-1234', 3, 'GP-2026-001', TRUE, TRUE, 'match',     'completed',  'USR-006', 'USR-006', 'USR-006'),
('GE-2026-00002', 'IR/2026/002', '2026-01-20', 4, 'PO-2026-0102', '2026-01-08', 5002, 'INV-TBS-2026-012', '2026-01-19', 85000.00,  'MH-04-CD-5678', 2, 'GP-2026-002', TRUE, TRUE, 'match',     'completed',  'USR-006', 'USR-006', 'USR-006'),
('GE-2026-00003', 'IR/2026/003', '2026-01-25', 3, 'PO-2026-0103', '2026-01-10', 5003, 'INV-MPM-2026-088', '2026-01-24', 45000.00,  'KA-05-EF-9012', 1, 'GP-2026-003', TRUE, TRUE, 'shortage',  'completed',  'USR-006', 'USR-006', 'USR-006'),
('GE-2026-00004', 'IR/2026/004', '2026-02-01', 2, 'PO-2026-0104', '2026-01-15', 5004, 'INV-POI-2026-023', '2026-01-31', 60000.00,  'TN-02-GH-3456', 2, 'GP-2026-004', TRUE, TRUE, 'match',     'completed',  'USR-006', 'USR-006', 'USR-006');

INSERT INTO qc_gate_entry_items (gate_entry_id, component_id, part_code, part_name, po_quantity, invoice_quantity, received_quantity, uom, quantity_match, mismatch_type) VALUES
(1, 1, 'BSC-TRD-001', 'B-SCAN Ultrasound Transducer 3.5MHz', 50, 50, 50, 'NOS', TRUE, NULL),
(1, 5, 'BSC-CBL-001', 'Transducer Cable Assembly 1.5m',       50, 50, 50, 'NOS', TRUE, NULL),
(2, 2, 'BSC-PCB-001', 'Main Control PCB Assembly',            25, 25, 25, 'NOS', TRUE, NULL),
(3, 4, 'BSC-ENC-001', 'Scanner Housing Assembly',             100, 100, 95, 'NOS', FALSE, 'quantity_shortage'),
(4, 3, 'BSC-LNS-001', 'Acoustic Lens 25mm',                   200, 200, 200, 'NOS', TRUE, NULL);

INSERT INTO qc_grn (grn_number, grn_date, gate_entry_id, vendor_id, po_number, po_date, odoo_po_id, invoice_number, invoice_date, invoice_amount, bill_number, bill_date, quarantine_location_id, status, qc_status, maker_id, maker_date, created_by) VALUES
('GRN-2026-00001', '2026-01-15', 1, 1, 'PO-2026-0101', '2026-01-05', 5001, 'INV-SLE-2026-045', '2026-01-14', 125000.00, 'BILL-001', '2026-01-15', 3, 'qc_complete', 'passed',  'USR-005', '2026-01-15 10:00:00+05:30', 'USR-005'),
('GRN-2026-00002', '2026-01-20', 2, 4, 'PO-2026-0102', '2026-01-08', 5002, 'INV-TBS-2026-012', '2026-01-19', 85000.00,  'BILL-002', '2026-01-20', 3, 'qc_complete', 'failed',  'USR-005', '2026-01-20 11:00:00+05:30', 'USR-005'),
('GRN-2026-00003', '2026-01-25', 3, 3, 'PO-2026-0103', '2026-01-10', 5003, 'INV-MPM-2026-088', '2026-01-24', 45000.00,  'BILL-003', '2026-01-25', 3, 'qc_pending',  'pending', 'USR-005', '2026-01-25 09:30:00+05:30', 'USR-005'),
('GRN-2026-00004', '2026-02-01', 4, 2, 'PO-2026-0104', '2026-01-15', 5004, 'INV-POI-2026-023', '2026-01-31', 60000.00,  'BILL-004', '2026-02-01', 3, 'qc_pending',  'pending', 'USR-005', '2026-02-01 10:00:00+05:30', 'USR-005');

INSERT INTO qc_grn_items (grn_id, po_line_number, component_id, part_code, part_name, po_quantity, received_quantity, accepted_quantity, rejected_quantity, uom, unit_price, line_amount, qc_required, qc_status, inspection_type, sample_size, batch_number) VALUES
(1, 1, 1, 'BSC-TRD-001', 'B-SCAN Ultrasound Transducer 3.5MHz', 50,  50,  48, 2,  'NOS', 2000.00, 100000.00, TRUE,  'passed',  'sampling',     8,  'LOT-TRD-2026-01'),
(1, 2, 5, 'BSC-CBL-001', 'Transducer Cable Assembly 1.5m',       50,  50,  50, 0,  'NOS', 500.00,  25000.00,  TRUE,  'passed',  'sampling',     8,  'LOT-CBL-2026-01'),
(2, 1, 2, 'BSC-PCB-001', 'Main Control PCB Assembly',            25,  25,  0,  25, 'NOS', 3400.00, 85000.00,  TRUE,  'failed',  '100_percent',  25, 'LOT-PCB-2026-01'),
(3, 1, 4, 'BSC-ENC-001', 'Scanner Housing Assembly',             100, 95,  0,  0,  'NOS', 450.00,  42750.00,  TRUE,  'pending', 'sampling',     13, 'LOT-ENC-2026-01'),
(4, 1, 3, 'BSC-LNS-001', 'Acoustic Lens 25mm',                   200, 200, 0,  0,  'NOS', 300.00,  60000.00,  TRUE,  'pending', 'sampling',     20, 'LOT-LNS-2026-01');


-- ============ MODULE 7-8: INSPECTION & IR ============

INSERT INTO qc_inspection_queue (queue_number, grn_id, grn_item_id, component_id, qc_plan_id, lot_size, sample_size, inspection_type, sampling_plan_id, priority, assigned_to, status, visual_result, functional_result, overall_result, started_at, completed_at) VALUES
('QC-2026-00001', 1, 1, 1, 1, 50, 8, 'sampling',     1, 3, 'USR-002', 'completed',  'pass', 'pass', 'accept',  '2026-01-16 09:00:00+05:30', '2026-01-16 15:00:00+05:30'),
('QC-2026-00002', 1, 2, 5, 1, 50, 8, 'sampling',     1, 5, 'USR-003', 'completed',  'pass', 'pass', 'accept',  '2026-01-16 10:00:00+05:30', '2026-01-16 14:00:00+05:30'),
('QC-2026-00003', 2, 3, 2, 2, 25, 25,'100_percent',  NULL, 2, 'USR-002', 'completed',  'pass', 'fail', 'reject',  '2026-01-21 09:00:00+05:30', '2026-01-21 16:00:00+05:30'),
('QC-2026-00004', 3, 4, 4, 4, 95, 13,'sampling',     1, 5, 'USR-003', 'pending',    NULL,   NULL,   'pending', NULL, NULL),
('QC-2026-00005', 4, 5, 3, 3, 200,20,'sampling',     2, 5, 'USR-002', 'pending',    NULL,   NULL,   'pending', NULL, NULL);

INSERT INTO qc_inspection_results (result_number, inspection_queue_id, qc_plan_stage_id, stage_name, stage_type, sample_size, total_checked, total_passed, total_failed, result, result_date, inspector_id, inspector_name, verified_by, verified_date) VALUES
-- Transducer Visual (passed)
('IR-2026-00001', 1, 1, 'Visual Inspection', 'visual',     8, 8, 8, 0, 'pass', '2026-01-16 12:00:00+05:30', 'USR-002', 'Priya Sharma', 'USR-001', '2026-01-16 13:00:00+05:30'),
-- Transducer Functional (passed)
('IR-2026-00002', 1, 2, 'Functional Test',   'functional', 8, 8, 8, 0, 'pass', '2026-01-16 15:00:00+05:30', 'USR-002', 'Priya Sharma', 'USR-001', '2026-01-16 16:00:00+05:30'),
-- Cable Visual (passed)
('IR-2026-00003', 2, 1, 'Visual Inspection', 'visual',     8, 8, 8, 0, 'pass', '2026-01-16 14:00:00+05:30', 'USR-003', 'Anand Krishnan', 'USR-001', '2026-01-16 15:00:00+05:30'),
-- PCB Visual (passed)
('IR-2026-00004', 3, 3, 'Visual Inspection', 'visual',     25, 25, 23, 2, 'pass', '2026-01-21 12:00:00+05:30', 'USR-002', 'Priya Sharma', 'USR-001', '2026-01-21 13:00:00+05:30'),
-- PCB Functional (failed)
('IR-2026-00005', 3, 4, 'Electrical Test',   'functional', 25, 25, 15, 10, 'fail', '2026-01-21 16:00:00+05:30', 'USR-002', 'Priya Sharma', 'USR-001', '2026-01-21 17:00:00+05:30');

-- Inspection Reports
INSERT INTO qc_inspection_reports (ir_number, ir_date, inspection_queue_id, grn_id, grn_number, po_number, vendor_id, vendor_name, supplier_bill_no, component_id, part_code, part_name, lot_number, lot_size, sample_size, quality_plan_code, overall_disposition, maker_id, maker_name, maker_date, checker_id, checker_name, checker_date, status) VALUES
('IRP-2026-00001', '2026-01-16', 1, 1, 'GRN-2026-00001', 'PO-2026-0101', 1, 'Sri Lakshmi Electronics Pvt Ltd', 'INV-SLE-2026-045', 1, 'BSC-TRD-001', 'B-SCAN Ultrasound Transducer 3.5MHz', 'LOT-TRD-2026-01', 50, 8, 'RD.7.3-07', 'accept', 'USR-002', 'Priya Sharma', '2026-01-16 15:30:00+05:30', 'USR-001', 'Rajesh Kumar', '2026-01-16 16:00:00+05:30', 'approved'),
('IRP-2026-00002', '2026-01-16', 2, 1, 'GRN-2026-00001', 'PO-2026-0101', 1, 'Sri Lakshmi Electronics Pvt Ltd', 'INV-SLE-2026-045', 5, 'BSC-CBL-001', 'Transducer Cable Assembly 1.5m', 'LOT-CBL-2026-01', 50, 8, 'RD.7.3-07', 'accept', 'USR-003', 'Anand Krishnan', '2026-01-16 14:30:00+05:30', 'USR-001', 'Rajesh Kumar', '2026-01-16 15:30:00+05:30', 'approved'),
('IRP-2026-00003', '2026-01-21', 3, 2, 'GRN-2026-00002', 'PO-2026-0102', 4, 'TechBoard Solutions', 'INV-TBS-2026-012', 2, 'BSC-PCB-001', 'Main Control PCB Assembly', 'LOT-PCB-2026-01', 25, 25, 'A12', 'reject', 'USR-002', 'Priya Sharma', '2026-01-21 16:30:00+05:30', 'USR-001', 'Rajesh Kumar', '2026-01-21 17:30:00+05:30', 'approved');


-- ============ MODULE 9: STORE TRANSFER ============

INSERT INTO qc_store_transfers (transfer_number, transfer_date, inspection_report_id, grn_id, grn_item_id, component_id, part_code, part_name, transfer_quantity, uom, source_location_id, destination_location_id, status, initiated_by, initiated_date, received_by, received_date, acknowledged_by, acknowledged_date) VALUES
('ST-2026-00001', '2026-01-17', 1, 1, 1, 1, 'BSC-TRD-001', 'B-SCAN Ultrasound Transducer 3.5MHz', 48, 'NOS', 3, 4, 'acknowledged', 'USR-002', '2026-01-17 09:00:00+05:30', 'USR-005', '2026-01-17 10:00:00+05:30', 'USR-005', '2026-01-17 10:30:00+05:30'),
('ST-2026-00002', '2026-01-17', 2, 1, 2, 5, 'BSC-CBL-001', 'Transducer Cable Assembly 1.5m',       50, 'NOS', 3, 4, 'acknowledged', 'USR-003', '2026-01-17 09:30:00+05:30', 'USR-005', '2026-01-17 10:00:00+05:30', 'USR-005', '2026-01-17 10:30:00+05:30');


-- ============ MODULE 10-11: VENDOR RETURNS, DC & DEBIT NOTE ============

INSERT INTO qc_vendor_returns (return_number, return_date, grn_id, inspection_report_id, vendor_id, po_number, return_type, total_return_qty, total_return_amount, status, maker_id, maker_name, maker_date, maker_remarks, checker_id, checker_name, checker_date, checker_remarks, checker_action, approver_id, approver_name, approver_date, approver_remarks, approver_action, created_by) VALUES
('VR-2026-00001', '2026-01-22', 2, 3, 4, 'PO-2026-0102', 'complete', 25, 85000.00, 'approved', 'USR-002', 'Priya Sharma', '2026-01-22 10:00:00+05:30', 'PCB batch failed functional test - 10/25 units non-conforming', 'USR-001', 'Rajesh Kumar', '2026-01-22 14:00:00+05:30', 'Verified. Failure rate 40% - full batch return recommended', 'approve', 'USR-004', 'Meera Venkatesh', '2026-01-22 16:00:00+05:30', 'Approved for debit note generation', 'approve', 'USR-002');

INSERT INTO qc_vendor_return_items (vendor_return_id, grn_item_id, component_id, part_code, part_name, return_quantity, uom, rejection_reason_id, rejection_reason_text, deviation_description, unit_price, line_amount) VALUES
(1, 3, 2, 'BSC-PCB-001', 'Main Control PCB Assembly', 25, 'NOS', 3, 'Functional Failure', '10 out of 25 PCBs failed electrical test - signal output voltage outside tolerance (measured 3.8V vs spec 3.3V Â± 0.1V). Batch rejected per quality policy.', 3400.00, 85000.00);

INSERT INTO qc_delivery_challans (dc_number, dc_date, vendor_return_id, vendor_id, vendor_name, vendor_address, source_location_id, vehicle_number, total_packages, total_amount, status, dispatched_by, dispatched_date, created_by) VALUES
('DC-2026-00001', '2026-01-23', 1, 4, 'TechBoard Solutions', 'Plot 45, MIDC Industrial Area, Mumbai 400093', 3, 'MH-04-CD-5678', 2, 85000.00, 'dispatched', 'USR-005', '2026-01-23 11:00:00+05:30', 'USR-005');

INSERT INTO qc_delivery_challan_items (delivery_challan_id, vendor_return_item_id, component_id, part_code, part_name, quantity, uom, unit_price, line_amount) VALUES
(1, 1, 2, 'BSC-PCB-001', 'Main Control PCB Assembly', 25, 'NOS', 3400.00, 85000.00);

INSERT INTO qc_debit_notes (debit_note_number, debit_note_date, vendor_return_id, delivery_challan_id, vendor_id, original_invoice_number, original_invoice_date, original_invoice_amount, debit_amount, tax_amount, total_amount, reason, status, approved_by, approved_date, created_by) VALUES
('DN-2026-00001', '2026-01-23', 1, 1, 4, 'INV-TBS-2026-012', '2026-01-19', 85000.00, 72033.90, 12966.10, 85000.00, 'Full batch return - PCB functional failure (40% non-conforming)', 'generated', 'USR-004', '2026-01-22 16:30:00+05:30', 'USR-004');


-- ============ MODULE 12: WORKFLOW & AUDIT ============

INSERT INTO qc_workflow_definitions (workflow_code, workflow_name, module, requires_maker, requires_checker, requires_approver, auto_approve_amount, escalation_hours) VALUES
('WF-GRN',        'GRN Processing Workflow',        'grn',            TRUE, FALSE, FALSE, NULL,   24),
('WF-INSPECTION',  'Inspection Workflow',             'inspection',     TRUE, TRUE,  FALSE, NULL,   48),
('WF-VR',          'Vendor Return Workflow',          'vendor_return',  TRUE, TRUE,  TRUE,  5000,   48),
('WF-DEBIT',       'Debit Note Workflow',             'debit_note',     TRUE, TRUE,  TRUE,  NULL,   72),
('WF-STORE-XFER',  'Store Transfer Workflow',         'store_transfer', TRUE, FALSE, FALSE, NULL,   24);

INSERT INTO qc_approval_history (module, record_id, action, from_status, to_status, action_by, action_by_name, action_role, action_date, remarks) VALUES
-- Vendor Return VR-2026-00001 approval flow
('vendor_return', 1, 'submit',  'draft',           'submitted',       'USR-002', 'Priya Sharma',     'maker',    '2026-01-22 10:30:00+05:30', 'Submitted for checker review'),
('vendor_return', 1, 'approve', 'submitted',       'checker_approved','USR-001', 'Rajesh Kumar',     'checker',  '2026-01-22 14:00:00+05:30', 'Verified failure. Approved for final review.'),
('vendor_return', 1, 'approve', 'checker_approved','approved',        'USR-004', 'Meera Venkatesh',  'approver', '2026-01-22 16:00:00+05:30', 'Approved. Generate debit note.'),
-- IR Approval flow
('inspection_report', 1, 'submit',  'draft', 'submitted', 'USR-002', 'Priya Sharma', 'maker',   '2026-01-16 15:30:00+05:30', 'Inspection complete - all passed'),
('inspection_report', 1, 'approve', 'submitted', 'approved', 'USR-001', 'Rajesh Kumar', 'checker', '2026-01-16 16:00:00+05:30', 'Verified and approved');


-- ============ MODULE 13: DASHBOARD DATA ============

INSERT INTO qc_daily_summary (summary_date, gate_entries_count, grn_count, inspections_completed, inspections_pending, pass_count, fail_count, pass_rate, items_in_quarantine, returns_initiated) VALUES
('2026-01-15', 1, 1, 0, 2, 0, 0, 0,    2, 0),
('2026-01-16', 0, 0, 2, 0, 2, 0, 100,  0, 0),
('2026-01-20', 1, 1, 0, 1, 0, 0, 0,    1, 0),
('2026-01-21', 0, 0, 1, 0, 0, 1, 0,    0, 0),
('2026-01-22', 0, 0, 0, 0, 0, 0, 0,    0, 1),
('2026-01-25', 1, 1, 0, 1, 0, 0, 0,    1, 0),
('2026-02-01', 1, 1, 0, 1, 0, 0, 0,    2, 0);

INSERT INTO qc_vendor_performance (vendor_id, period_year, period_month, total_deliveries, total_lots_inspected, lots_accepted, lots_rejected, total_quantity, accepted_quantity, rejected_quantity, acceptance_rate) VALUES
(1, 2026, 1, 1, 2, 2, 0, 100, 98,  2,  98.00),
(4, 2026, 1, 1, 1, 0, 1, 25,  0,   25, 0.00),
(3, 2026, 1, 1, 0, 0, 0, 95,  0,   0,  NULL),
(2, 2026, 2, 1, 0, 0, 0, 200, 0,   0,  NULL);


-- ============ MODULE 14: NOTIFICATIONS ============

INSERT INTO qc_notifications (notification_type, module, record_id, title, message, priority, recipient_user_id, action_url) VALUES
('inspection_due',   'inspection', 4, 'New Inspection Pending',        'Scanner Housing Assembly (QC-2026-00004) is pending inspection from GRN-2026-00003', 'normal', 3, '/inspection/QC-2026-00004'),
('inspection_due',   'inspection', 5, 'New Inspection Pending',        'Acoustic Lens 25mm (QC-2026-00005) is pending inspection from GRN-2026-00004',      'normal', 2, '/inspection/QC-2026-00005'),
('approval_pending', 'vendor_return', 1, 'Return Approved',            'Vendor return VR-2026-00001 has been approved. DC and Debit Note generated.',       'high',   2, '/returns/VR-2026-00001'),
('system',           'dashboard', NULL, 'Daily QC Summary',            'Feb 1: 1 GRN received, 2 inspections pending',                                       'low',    1, '/dashboard');


COMMIT;

-- ================================================================================
-- SCHEMA STATISTICS
-- ================================================================================
-- Total Tables:     42
-- Total Views:       7
-- Total Triggers:   17 (8 auto-generate + 9 timestamp)
-- Total Functions:   9
-- Total Indexes:    55+
-- Modules:          14
-- Screens Covered:  All 16 (Screens 1-16)
-- ================================================================================
