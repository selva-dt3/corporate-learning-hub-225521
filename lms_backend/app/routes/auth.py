from flask import g, jsonify, current_app as app
from flask_smorest import Blueprint
from flask.views import MethodView
from marshmallow import Schema, fields, validate

blp = Blueprint(
    "Auth",
    "auth",
    url_prefix="/auth",
    description="Authentication and profile endpoints"
)

class ProfileSchema(Schema):
    user_id = fields.UUID(required=True, description="Auth user id")
    role = fields.String(required=True, validate=validate.OneOf(["admin", "hr", "employee"]))
    onboarding_complete = fields.Boolean(required=True)
    full_name = fields.String(allow_none=True)
    department = fields.String(allow_none=True)
    created_at = fields.DateTime(allow_none=True)


# PUBLIC_INTERFACE
@blp.route("/profile")
class ProfileResource(MethodView):
    """Get or update the current user's profile information."""

    @blp.response(200, ProfileSchema, description="Current user profile")
    def get(self):
        """Get current user's profile.
        Returns the authenticated user's profile row from Supabase.
        """
        if not getattr(g, "user_id", None):
            return jsonify({"error": {"code": "AUTH_ERROR", "message": "Unauthorized"}}), 401

        supabase = getattr(app, "supabase", None)
        resp = supabase.table("profiles").select("*").eq("user_id", str(g.user_id)).limit(1).execute()  # type: ignore
        if not resp.data:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Profile not found"}}), 404
        return resp.data[0]

    class ProfileUpdateSchema(Schema):
        onboarding_complete = fields.Boolean(description="Mark onboarding as complete")
        full_name = fields.String()
        department = fields.String()

    @blp.arguments(ProfileUpdateSchema)
    @blp.response(200, ProfileSchema, description="Updated profile")
    def put(self, json_data):
        """Update current user's profile fields (non-role)."""
        if not getattr(g, "user_id", None):
            return jsonify({"error": {"code": "AUTH_ERROR", "message": "Unauthorized"}}), 401

        updates = {k: v for k, v in json_data.items() if k in ["onboarding_complete", "full_name", "department"]}
        if not updates:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "No valid fields to update"}}), 400

        supabase = getattr(app, "supabase", None)
        resp = supabase.table("profiles").update(updates).eq("user_id", str(g.user_id)).execute()  # type: ignore
        # Supabase returns list of rows updated
        data = resp.data[0] if resp.data else None
        return data or {}


onboarding_blp = Blueprint(
    "Onboarding",
    "onboarding",
    url_prefix="/onboarding",
    description="Onboarding flow endpoints"
)

# PUBLIC_INTERFACE
@onboarding_blp.route("/complete")
class OnboardingComplete(MethodView):
    """Mark onboarding as complete for current user."""

    @blp.response(200, ProfileSchema)
    def post(self):
        """Complete onboarding for current user."""
        if not getattr(g, "user_id", None):
            return jsonify({"error": {"code": "AUTH_ERROR", "message": "Unauthorized"}}), 401

        supabase = getattr(app, "supabase", None)
        resp = supabase.table("profiles").update({"onboarding_complete": True}).eq("user_id", str(g.user_id)).execute()  # type: ignore
        data = resp.data[0] if resp.data else None
        return data or {}

# Register onboarding under Auth group in the same blueprint registration step
blp.register_blueprint(onboarding_blp)

# Compatibility route alias (frontend may call without /auth prefix)
# PUBLIC_INTERFACE
@blp.route("/onboarding/complete")
class OnboardingCompleteAlias(MethodView):
    """Alias to support clients posting to /auth/onboarding/complete or /onboarding/complete."""

    @blp.response(200, ProfileSchema)
    def post(self):
        """Complete onboarding for current user (alias)."""
        # Reuse same logic by delegating to the original handler
        if not getattr(g, "user_id", None):
            return jsonify({"error": {"code": "AUTH_ERROR", "message": "Unauthorized"}}), 401

        supabase = getattr(app, "supabase", None)
        resp = supabase.table("profiles").update({"onboarding_complete": True}).eq("user_id", str(g.user_id)).execute()  # type: ignore
        data = resp.data[0] if resp.data else None
        return data or {}
