"""
WSGI entrypoint for the LMS Flask backend.

This module exposes the Flask application as 'application' for WSGI servers.
It uses the factory function to avoid import-time side effects and ensures
the app can be picked up by servers like gunicorn or uWSGI.

Environment:
- PORT: Optional. Runtime port for development (default 3011); WSGI servers typically manage binding.
- SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET, FRONTEND_URL, CORS_ORIGINS: Optional for startup; app fails lazily on auth-required routes when not provided.
"""

from app import create_app

# Expose as 'application' for WSGI servers
application = create_app()
