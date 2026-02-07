import re
import bleach


def sanitize_string(value):
    """Strip HTML tags and trim whitespace from string inputs."""
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    cleaned = bleach.clean(str(value), tags=[], strip=True)
    return cleaned.strip()


def sanitize_dict(data):
    """Recursively sanitize all string values in a dict."""
    if not isinstance(data, dict):
        return data
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item) if isinstance(item, dict)
                else sanitize_string(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


# Indian GST Format: 22AAAAA0000A1Z5
GST_REGEX = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
# Valid Indian state codes for GST
VALID_STATE_CODES = {
    '01', '02', '03', '04', '05', '06', '07', '08', '09', '10',
    '11', '12', '13', '14', '15', '16', '17', '18', '19', '20',
    '21', '22', '23', '24', '25', '26', '27', '28', '29', '30',
    '31', '32', '33', '34', '35', '36', '37',
}

# Indian PAN: AAAAA0000A
PAN_REGEX = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')

# Indian PIN code: 6 digits, first non-zero
PINCODE_REGEX = re.compile(r'^[1-9][0-9]{5}$')

# Alphanumeric + hyphens
ALPHANUM_HYPHEN_REGEX = re.compile(r'^[A-Za-z0-9\-]+$')

# Part code: uppercase alphanumeric + hyphens
PART_CODE_REGEX = re.compile(r'^[A-Z0-9\-]+$')


def validate_gst(value):
    """Validate Indian GST number format."""
    if not value:
        return None
    value = value.upper().strip()
    if not GST_REGEX.match(value):
        return 'Invalid GST format. Expected: 22AAAAA0000A1Z5'
    if value[:2] not in VALID_STATE_CODES:
        return f'Invalid state code "{value[:2]}" in GST number'
    return None


def validate_pan(value):
    """Validate Indian PAN number format."""
    if not value:
        return None
    value = value.upper().strip()
    if not PAN_REGEX.match(value):
        return 'Invalid PAN format. Expected: AAAAA0000A'
    return None


def validate_pincode(value):
    """Validate Indian PIN code."""
    if not value:
        return None
    value = str(value).strip()
    if not PINCODE_REGEX.match(value):
        return 'Invalid PIN code. Must be 6 digits, first digit non-zero'
    return None


def validate_email(value):
    """Basic email format validation."""
    if not value:
        return None
    email_regex = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    if not email_regex.match(value.strip()):
        return 'Invalid email format'
    return None


def validate_phone(value):
    """Basic phone validation."""
    if not value:
        return None
    phone_regex = re.compile(r'^[\+\-\(\)\s0-9]{7,20}$')
    if not phone_regex.match(value.strip()):
        return 'Invalid phone number format'
    return None
