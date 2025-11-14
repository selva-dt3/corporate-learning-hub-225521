"""Authentication and authorization decorators for the LMS backend.

This module is intentionally isolated from app initialization to avoid circular imports.
It must not import the Flask 'app' object or any blueprints. It should only use
Flask globals and simple utilities that do not cause import-time side effects.
"""

from functools import wraps
from typing import Callable, Any

from flask import g, jsonify


# PUBLIC_INTERFACE
def role_required(*roles: str) -> Callable[..., Any]:
    """Decorator for role-based authorization.

    Usage:
        @role_required('admin', 'hr')
        def some_view(...):
            ...

    This decorator checks the 'g.role' populated by request authentication middleware.
    If the current user role is not present in the allowed roles, a 403 response is returned.
    """
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def _inner(*args, **kwargs):
            role = getattr(g, "role", None)
            if not role or role not in roles:
                return jsonify({"error": {"code": "AUTHZ_ERROR", "message": "Insufficient role"}}), 403
            return fn(*args, **kwargs)
        return _inner
    return decorator
