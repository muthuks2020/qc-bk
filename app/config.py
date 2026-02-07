import os


def _build_database_url():
    """Build DATABASE_URL from individual parts OR use full URL if provided."""
    full_url = os.environ.get('DATABASE_URL')
    if full_url:
        return full_url

    # Build from individual env vars
    host = os.environ.get('DB_HOST', 'localhost')
    port = os.environ.get('DB_PORT', '5432')
    name = os.environ.get('DB_NAME', 'appasamy_qc')
    user = os.environ.get('DB_USER', 'postgres')
    password = os.environ.get('DB_PASSWORD', 'postgres')
    return f'postgresql://{user}:{password}@{host}:{port}/{name}'


def _get_engine_options(pool_size=None, max_overflow=None):
    """Build SQLAlchemy engine options with schema search_path."""
    schema = os.environ.get('DB_SCHEMA', 'public')
    options = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {
            'connect_timeout': 10,
            'options': f'-csearch_path={schema},public'
        }
    }
    if pool_size:
        options['pool_size'] = pool_size
    if max_overflow:
        options['max_overflow'] = max_overflow
    return options


class BaseConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB default
    UPLOAD_DIR = os.environ.get('UPLOAD_DIR', './uploads')
    UPLOAD_STORAGE = os.environ.get('UPLOAD_STORAGE', 'local')
    ODOO_ENABLED = os.environ.get('ODOO_ENABLED', 'false').lower() == 'true'
    EMAIL_ENABLED = os.environ.get('EMAIL_ENABLED', 'false').lower() == 'true'
    SCHEDULER_ENABLED = os.environ.get('SCHEDULER_ENABLED', 'false').lower() == 'true'
    API_SECRET_TOKEN = os.environ.get('API_SECRET_TOKEN', 'local-dev-token-2026')
    AUTH_ENABLED = os.environ.get('AUTH_ENABLED', 'true').lower() in ('true', '1', 'yes')
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
    LOG_FILE = os.environ.get('LOG_FILE', './logs/app.log')

    # Database schema (public for local, qcapp for AWS)
    DB_SCHEMA = os.environ.get('DB_SCHEMA', 'public')

    # File upload settings
    ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'xlsx', 'docx'}
    BLOCKED_EXTENSIONS = {'exe', 'bat', 'sh', 'py', 'js', 'php'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB for file uploads

    # Pagination defaults
    DEFAULT_PAGE = 1
    DEFAULT_PER_PAGE = 20
    MAX_PER_PAGE = 100

    # Rate limiting
    RATELIMIT_DEFAULT = "100/minute"
    RATELIMIT_STORAGE_URI = "memory://"


class DevelopmentConfig(BaseConfig):
    """Local development — points to localhost PostgreSQL (public schema)."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _build_database_url()
    SQLALCHEMY_ENGINE_OPTIONS = _get_engine_options()


class StagingConfig(BaseConfig):
    """AWS staging — points to RDS (appasamy_rpt, qcapp schema)."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _build_database_url()
    SQLALCHEMY_ENGINE_OPTIONS = _get_engine_options(pool_size=5, max_overflow=10)


class ProductionConfig(BaseConfig):
    """AWS production — RDS with stricter settings."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _build_database_url()
    RATELIMIT_STORAGE_URI = os.environ.get('REDIS_URL', 'memory://')
    SQLALCHEMY_ENGINE_OPTIONS = _get_engine_options(pool_size=10, max_overflow=20)


class TestingConfig(BaseConfig):
    """Unit / integration tests — local test DB."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'TEST_DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/appasamy_qc_test'
    )
    SQLALCHEMY_ENGINE_OPTIONS = _get_engine_options()


config = {
    'development': DevelopmentConfig,
    'staging': StagingConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
