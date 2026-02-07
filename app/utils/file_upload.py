import os
from uuid import uuid4
from werkzeug.utils import secure_filename
from flask import current_app, send_from_directory

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'xlsx', 'docx'}

def get_extension(filename):
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def is_allowed_file(filename):
    ext = get_extension(filename)
    return ext in ALLOWED_EXTENSIONS

def save_file(file, module, record_id):
    storage = current_app.config.get('UPLOAD_STORAGE', 'local')
    original_name = secure_filename(file.filename)
    ext = get_extension(original_name)
    unique_name = f"{uuid4().hex}.{ext}"
    if storage == 'local':
        upload_dir = current_app.config.get('UPLOAD_DIR', './uploads')
        path = os.path.join(upload_dir, module, str(record_id))
        os.makedirs(path, exist_ok=True)
        filepath = os.path.join(path, unique_name)
        file.save(filepath)
        return f"/api/v1/files/{module}/{record_id}/{unique_name}", filepath
    else:
        import boto3
        s3 = boto3.client('s3', region_name=current_app.config.get('AWS_REGION'))
        bucket = current_app.config.get('AWS_S3_BUCKET')
        s3_key = f"{module}/{record_id}/{unique_name}"
        file.seek(0)
        s3.upload_fileobj(file, bucket, s3_key)
        return f"https://{bucket}.s3.amazonaws.com/{s3_key}", s3_key

def serve_local_file(module, record_id, filename):
    upload_dir = current_app.config.get('UPLOAD_DIR', './uploads')
    directory = os.path.join(upload_dir, module, str(record_id))
    return send_from_directory(os.path.abspath(directory), filename, as_attachment=True)
