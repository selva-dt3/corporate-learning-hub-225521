import os
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
    Performs validation and logs actionable guidance without aborting startup.
    """
    load_dotenv()  # Load from lms_backend/.env if present

    app.config["SUPABASE_URL"] = (os.getenv("SUPABASE_URL") or "").strip()
    app.config["SUPABASE_ANON_KEY"] = (os.getenv("SUPABASE_ANON_KEY") or "").strip()
    app.config["SUPABASE_SERVICE_ROLE_KEY"] = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    app.config["SUPABASE_JWT_SECRET"] = (os.getenv("SUPABASE_JWT_SECRET") or "").strip()

    # Frontend and CORS origins
    app.config["FRONTEND_URL"] = os.getenv("FRONTEND_URL", "").strip()
    extra_allowed = os.getenv("EXTRA_ALLOWED_ORIGINS", "")
    cors_origins_env = os.getenv("CORS_ORIGINS", "")

    # Build allowed origins list from env:
    origins: List[str] = []
    for raw in [app.config["FRONTEND_URL"], cors_origins_env, extra_allowed]:
        if raw:
            origins.extend([o.strip() for o in raw.split(",") if o.strip()])

    # If nothing configured, default to deny-all except same-origin swagger usage.
    app.config["CORS_ORIGINS"] = sorted({o for o in origins if o and o != "*"})

    # OpenAPI/Swagger configuration
    app.config["API_TITLE"] = "Corporate Learning Hub - LMS API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/docs"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    # Docs embedding/frame-ancestors configuration via env
    app.config["DOCS_FRAME_ANCESTORS"] = os.getenv("DOCS_FRAME_ANCESTORS", "").strip()

    # Robust validation with guidance
    url = app.config.get("SUPABASE_URL", "")
    anon = app.config.get("SUPABASE_ANON_KEY", "")
    svc = app.config.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not url:
        app.logger.warning(
            "SUPABASE_URL is not set. Supabase-backed endpoints will be unavailable. "
            "Set SUPABASE_URL in lms_backend/.env."
        )

    # Detect placeholders or obviously invalid keys (short length or known dummy prefixes)
    def _is_invalid_key(k: str) -> bool:
        if not k:
            return True
        # Supabase keys are JWT-like base64 segments with at least two dots typically
        if k.count(".") < 2:
            return True
        # Common placeholders
        if any(p in k.lower() for p in ["your-", "placeholder", "changeme", "example", "xxxx", "placeholder"]):
            return True
        return False

    if _is_invalid_key(anon):
        app.logger.warning(
            "SUPABASE_ANON_KEY appears missing or invalid. Public client operations will be disabled. "
            "Ensure SUPABASE_ANON_KEY is set to your project's anon public key."
        )
    if svc and _is_invalid_key(svc):
        app.logger.warning(
            "SUPABASE_SERVICE_ROLE_KEY appears invalid. Server-side privileged operations will be disabled. "
            "Unset or correct SUPABASE_SERVICE_ROLE_KEY."
        )


def _init_supabase(app: Flask) -> Optional[Client]:
    """
    Initialize and attach Supabase client to app.

    Logic:
    - Prefer using the anon key for general runtime operations to respect RLS.
    - Only use service role for guarded server tasks (auto-create profile), and only if the key is valid.
    - If URL or anon key invalid, do not create client; return None so routes can return 503 gracefully.
    """
    url = (app.config.get("SUPABASE_URL") or "").strip()
    anon_key = (app.config.get("SUPABASE_ANON_KEY") or "").strip()
    svc_key = (app.config.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()

    def _looks_valid(k: str) -> bool:
        return bool(k) and k.count(".") >= 2

    if not url or not _looks_valid(anon_key):
        app.logger.warning(
            "Supabase client not initialized: missing or invalid SUPABASE_URL/SUPABASE_ANON_KEY. "
            "App will continue to serve health/docs; endpoints requiring Supabase will respond with 503."
        )
        return None

    try:
        # Use anon key for primary client
        client = create_client(url, anon_key)
        # Store a flag so request handlers know if service role is available
        app.config["HAS_SERVICE_ROLE"] = _looks_valid(svc_key)
        if not app.config["HAS_SERVICE_ROLE"] and svc_key:
            app.logger.warning(
                "SUPABASE_SERVICE_ROLE_KEY provided but appears invalid; privileged ops (like auto-profile) disabled."
            )
        return client
    except Exception as e:
        app.logger.error(f"Failed to initialize Supabase client: {e}")
        return None


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

    # Apply to all paths (flask-cors will echo the request Origin if it matches allowed list/regex)
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
    - Auto-create a default profile on first login when service role key is valid
    - Attach g.user and g.role
    - Apply security headers and CORS preflight handling
    """
    @app.before_request
    def authenticate():
        # Handle OPTIONS preflight early and return 200 with headers applied by flask-cors
        if request.method == "OPTIONS":
            app.logger.debug("CORS preflight OPTIONS for path=%s", request.path)
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
            app.logger.info("Auth missing Bearer token for path=%s", path)
            return jsonify({"error": {"code": "AUTH_ERROR", "message": "Missing Bearer token"}}), 401

        token = auth_header.replace("Bearer ", "").strip()
        claims = _jwt_decode(token, app)
        if not claims:
            app.logger.info("Auth invalid token for path=%s", path)
            return jsonify({"error": {"code": "AUTH_ERROR", "message": "Invalid token"}}), 401

        # user id expected in 'sub' claim
        user_id = claims.get("sub")
        if not user_id:
            app.logger.info("Auth token missing sub claim for path=%s", path)
            return jsonify({"error": {"code": "AUTH_ERROR", "message": "Invalid token: sub missing"}}), 401

        g.user_id = user_id
        g.user = {"id": user_id}
        g.role = None

        # If Supabase is not configured, fail gracefully for routes that need it
        if not supabase:
            app.logger.warning("Supabase client unavailable; returning 503 for path=%s", path)
            return jsonify({
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY. "
                               "For server-side operations, optionally set SUPABASE_SERVICE_ROLE_KEY."
                }
            }), 503

        # Fetch role and profile; if not present attempt creation (service role required)
        try:
            resp = supabase.table("profiles").select("*").eq("user_id", user_id).limit(1).execute()  # type: ignore
            if resp.data and len(resp.data) > 0:
                profile = resp.data[0]
                g.user["profile"] = profile
                g.role = profile.get("role")
                app.logger.debug("Loaded profile for user_id=%s role=%s", user_id, g.role)
            else:
                # Attempt auto-create a minimal profile only when a valid service role key is configured.
                if app.config.get("HAS_SERVICE_ROLE"):
                    payload = {
                        "user_id": user_id,
                        "role": "employee",
                        "onboarding_complete": False,
                    }
                    try:
                        ins = supabase.table("profiles").insert(payload).execute()  # type: ignore
                        created = ins.data[0] if ins.data else payload
                        g.user["profile"] = created
                        g.role = created.get("role")
                        app.logger.info("Auto-created profile for user_id=%s with role=%s", user_id, g.role)
                    except Exception as ie:
                        app.logger.error("Auto-create profile failed for user_id=%s error=%s", user_id, ie)
                        # Keep role None; downstream role_required will enforce access
                else:
                    # Service role not configured; cannot auto-create due to RLS/policies
                    app.logger.warning(
                        "SUPABASE_SERVICE_ROLE_KEY not available or invalid; cannot auto-create profile for user_id=%s",
                        user_id,
                    )
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
            frame_ancestors = app.config.get("DOCS_FRAME_ANCESTORS", "")
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

    # Attach Supabase client to app for reuse (lazy/guarded init)
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
