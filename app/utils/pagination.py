from flask import request, current_app


def get_pagination_params():
    """Extract and validate pagination params from query string."""
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    page = max(1, page)

    try:
        per_page = int(request.args.get('per_page', current_app.config.get('DEFAULT_PER_PAGE', 20)))
    except (ValueError, TypeError):
        per_page = 20
    per_page = max(1, min(per_page, current_app.config.get('MAX_PER_PAGE', 100)))

    return page, per_page


def paginate_query(query, page, per_page):
    """Apply pagination to a SQLAlchemy query and return results + meta."""
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    meta = {
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'total_pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
    }
    return pagination.items, meta


def get_sort_params(allowed_columns, default_sort='created_at', default_order='desc'):
    """Extract and validate sort params."""
    sort_by = request.args.get('sort_by', default_sort)
    sort_order = request.args.get('sort_order', default_order).lower()

    if sort_by not in allowed_columns:
        sort_by = default_sort
    if sort_order not in ('asc', 'desc'):
        sort_order = default_order

    return sort_by, sort_order
