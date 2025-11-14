import os
from datetime import datetime
from typing import Any, Dict, Optional

from flask import Flask, g, request, jsonify
from flask_cors import CORS
from flask_smorest import Api
from dotenv import load_dotenv
from jose import jwt, JWTError
from supabase import create_client, Client

# Blueprints
from .routes.health import blp as health_blp
from .routes.auth import blp as auth_blp
from .routes.users import blp as users_blp
from .routes.lessons import blp as lessons_blp
from .routes.quizzes import blp as quizzes_blp
from .routes.assignments import blp as assignments_blp
from .routes.analytics import blp as analytics_blp


def _load_config(app: Flask) -> None:
    """
    Load configuration from environment variables.
    """
    load_dotenv()  # Load from lms_backend/.env if present

    app.config["SUPABASE_URL"] = os.getenv("SUPABASE_URL")
    app.config["SUPABASE_ANON_KEY"] = os.getenv("SUPABASE_ANON_KEY")
    app.config["SUPABASE_SERVICE_ROLE_KEY"] = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    app.config["SUPABASE_JWT_SECRET"] = os.getenv("SUPABASE_JWT_SECRET")
    app.config["FRONTEND_URL"] = os.getenv("FRONTEND_URL", "*")
    cors_origins = os.getenv("CORS_ORIGINS", app.config["FRONTEND_URL"])
    app.config["CORS_ORIGINS"] = [o.strip() for o in cors_origins.split(",") if o.strip()]

    # OpenAPI/Swagger configuration
    app.config["API_TITLE"] = "Corporate Learning Hub - LMS API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/docs"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    # Simple validation: ensure required keys are present at runtime
    for key in ["SUPABASE_URL", "SUPABASE_ANON_KEY"]:
        if not app.config.get(key):
            # Let app still start for health/docs; auth-required endpoints will fail with 500
            app.logger.warning(f"Environment variable {key} is not set. Authenticated calls may fail.")


def _init_supabase(app: Flask) -> Client:
    """
    Initialize and attach Supabase client to app.
    """
    url = app.config.get("SUPABASE_URL")
    key = app.config.get("SUPABASE_SERVICE_ROLE_KEY") or app.config.get("SUPABASE_ANON_KEY")
    if not url or not key:
        app.logger.warning("Supabase not fully configured, some endpoints will not function.")
        return None  # type: ignore

    client = create_client(url, key)
    return client


def _install_cors(app: Flask) -> None:
    """
    Configure CORS to allow frontend origin(s).
    """
    origins = app.config.get("CORS_ORIGINS", ["*"])
    CORS(app, resources={r"/*": {"origins": origins}}, supports_credentials=True)


def _jwt_decode(token: str, app: Flask) -> Optional[Dict[str, Any]]:
    """
    Decode and validate JWT using SUPABASE_JWT_SECRET when available.
    If secret is missing, attempt no verification decode to extract sub for local dev.
    """
    secret = app.config.get("SUPABASE_JWT_SECRET")
    algorithms = ["HS256"]
    try:
        if secret:
            return jwt.decode(token, secret, algorithms=algorithms, options={"verify_aud": False})
        else:
            # Fallback: decode without validation for local dev; DO NOT use in production.
            app.logger.warning("SUPABASE_JWT_SECRET missing; decoding JWT without verification (dev only).")
            return jwt.get_unverified_claims(token)  # type: ignore
    except JWTError as e:
        app.logger.info(f"JWT decode error: {e}")
        return None


def _attach_request_context(app: Flask, supabase: Optional[Client]) -> None:
    """
    Install before_request/after_request handlers:
    - Authenticate Bearer JWT and load profile from Supabase
    - Attach g.user and g.role
    """
    @app.before_request
    def authenticate():
        # Public routes: health, docs/openapi
        path = request.path or ""
        if path == "/" or path.startswith("/docs") or path == "/openapi.json":
            return

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            # Allow only if route opts-out via attribute
            if getattr(app.view_functions.get(request.endpoint, None), "auth_optional", False):
                return
            return jsonify({"error": {"code": "AUTH_ERROR", "message": "Missing Bearer token"}}), 401

        token = auth_header.replace("Bearer ", "").strip()
        claims = _jwt_decode(token, app)
        if not claims:
            return jsonify({"error": {"code": "AUTH_ERROR", "message": "Invalid token"}}), 401

        # user id expected in 'sub' claim
        user_id = claims.get("sub")
        if not user_id:
            return jsonify({"error": {"code": "AUTH_ERROR", "message": "Invalid token: sub missing"}}), 401

        g.user_id = user_id
        g.user = {"id": user_id}
        g.role = None

        # Fetch role and profile from profiles
        if supabase:
            try:
                resp = supabase.table("profiles").select("*").eq("user_id", user_id).limit(1).execute()
                if resp.data and len(resp.data) > 0:
                    profile = resp.data[0]
                    g.user["profile"] = profile
                    g.role = profile.get("role")
                else:
                    # No profile row; treat as unauthorized for protected routes
                    g.role = None
            except Exception as e:
                app.logger.error(f"Supabase profile fetch failed: {e}")

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response





def create_app() -> Flask:
    """
    Factory to create Flask app with all config, auth, routes and docs.
    """
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    _load_config(app)
    _install_cors(app)

    # OpenAPI
    api = Api(app, spec_kwargs={
        "info": {
            "title": app.config["API_TITLE"],
            "version": app.config["API_VERSION"],
            "description": "REST API for Corporate Learning Hub (LMS) with Supabase auth and role-based access.",
        },
        "tags": [
            {"name": "Health", "description": "Health check and service info"},
            {"name": "Auth", "description": "Authentication and profile endpoints"},
            {"name": "Users", "description": "Admin-managed users"},
            {"name": "Lessons", "description": "Lesson management"},
            {"name": "Quizzes", "description": "Quiz management and submissions"},
            {"name": "Assignments", "description": "Assignments workflows"},
            {"name": "Analytics", "description": "Aggregated analytics"},
        ],
    })

    # Attach Supabase client to app for reuse
    app.supabase = _init_supabase(app)  # type: ignore[attr-defined]

    # Request context auth handlers
    _attach_request_context(app, getattr(app, "supabase", None))

    # Centralized error handling
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Bad request"}}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": {"code": "AUTH_ERROR", "message": "Unauthorized"}}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": {"code": "AUTHZ_ERROR", "message": "Forbidden"}}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Not found"}}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}), 500

    # Register blueprints
    api.register_blueprint(health_blp)
    api.register_blueprint(auth_blp)
    api.register_blueprint(users_blp)
    api.register_blueprint(lessons_blp)
    api.register_blueprint(quizzes_blp)
    api.register_blueprint(assignments_blp)
    api.register_blueprint(analytics_blp)

    # Expose for generate_openapi.py
    app.api = api  # type: ignore[attr-defined]

    return app


# Initialize app for run.py and openapi generation
app = create_app()
api = app.api  # type: ignore[attr-defined]
