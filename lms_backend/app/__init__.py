import os
from datetime import datetime
from typing import Any, Dict, Optional, List

from flask import Flask, g, request, jsonify, make_response
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

    # Frontend and CORS origins
    app.config["FRONTEND_URL"] = os.getenv("FRONTEND_URL", "").strip()
    extra_allowed = os.getenv("EXTRA_ALLOWED_ORIGINS", "")
    cors_origins_env = os.getenv("CORS_ORIGINS", "")

    # Build allowed origins list from env:
    # - FRONTEND_URL
    # - CORS_ORIGINS (legacy, comma-separated)
    # - EXTRA_ALLOWED_ORIGINS (comma-separated)
    # - Always include beta.kavia.ai (preview) if present via explicit string below
    origins: List[str] = []
    for raw in [app.config["FRONTEND_URL"], cors_origins_env, extra_allowed]:
        if raw:
            origins.extend([o.strip() for o in raw.split(",") if o.strip()])

    # Ensure uniqueness and include known preview host if provided in env
    # Do not hardcode ports; rely on env to provide exact origins.
    # Also permit beta.kavia.ai if explicitly added in env; if not set, user can add via EXTRA_ALLOWED_ORIGINS.

    # If nothing configured, default to deny-all except same-origin swagger usage.
    # However, flask-cors requires an origins list; keep empty to block cross-origin unless configured.
    app.config["CORS_ORIGINS"] = sorted({o for o in origins if o and o != "*"})

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
    Configure CORS to allow frontend origin(s), including preview origins.
    Applies to all routes including /docs.

    Behavior:
    - If CORS_ORIGINS env is provided, use that list (exact origins).
    - If not provided, allow any origin via regex (".*") so preflights succeed in preview.
      This returns the requesting Origin header (not "*"), which works with credentials.
    """
    origins = app.config.get("CORS_ORIGINS", [])

    # Build dynamic origin allowance:
    # - When explicitly configured: use configured list
    # - When empty: permissive regex fallback for preview environments
    allowed_origins = origins if origins else [r".*"]

    # Methods/Headers per requirements
    cors_options = {
        "origins": allowed_origins,
        "supports_credentials": True,
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type", "X-Requested-With"],
        "expose_headers": [],
    }

    # Apply to all paths
    CORS(
        app,
        resources={r"/*": cors_options},
        supports_credentials=cors_options["supports_credentials"],
        methods=cors_options["methods"],
        allow_headers=cors_options["allow_headers"],
        expose_headers=cors_options["expose_headers"],
    )


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
    - Apply security headers and CORS preflight handling
    """
    @app.before_request
    def authenticate():
        # Handle OPTIONS preflight early and return 200 with headers applied by flask-cors
        if request.method == "OPTIONS":
            return make_response(("", 200))

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
        # Security headers defaults
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Default deny framing
        xfo = "DENY"
        csp = None

        # Relax for docs
        path = request.path or ""
        if path.startswith("/docs"):
            # Allow same-origin for embedding Swagger UI in platform preview frame
            xfo = "SAMEORIGIN"
            # Optional override via env: DOCS_FRAME_ANCESTORS allows explicit framing
            frame_ancestors = os.getenv("DOCS_FRAME_ANCESTORS", "").strip()
            if frame_ancestors:
                # Use CSP frame-ancestors which supersedes X-Frame-Options in modern browsers
                csp = f"frame-ancestors {frame_ancestors};"

        response.headers["X-Frame-Options"] = xfo
        if csp:
            # Append/Set Content-Security-Policy
            response.headers["Content-Security-Policy"] = csp
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
