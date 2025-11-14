from flask import jsonify, current_app as app
from flask_smorest import Blueprint
from flask.views import MethodView
from marshmallow import Schema, fields, validate

from ..auth.decorators import role_required  # moved to dedicated module

blp = Blueprint(
    "Users",
    "users",
    url_prefix="/users",
    description="Admin managed users"
)

class UserCreateSchema(Schema):
    user_id = fields.UUID(required=True, description="Auth user id to link")
    role = fields.String(required=True, validate=validate.OneOf(["admin", "hr", "employee"]))
    full_name = fields.String()
    department = fields.String()

class UserPatchSchema(Schema):
    role = fields.String(validate=validate.OneOf(["admin", "hr", "employee"]))
    full_name = fields.String()
    department = fields.String()
    onboarding_complete = fields.Boolean()

class ProfileSchema(Schema):
    user_id = fields.UUID(required=True)
    role = fields.String(required=True)
    onboarding_complete = fields.Boolean(required=True)
    full_name = fields.String(allow_none=True)
    department = fields.String(allow_none=True)
    created_at = fields.DateTime(allow_none=True)


# PUBLIC_INTERFACE
@blp.route("")
class UsersCollection(MethodView):
    """Admin-only user management collection endpoints."""

    @role_required("admin")
    @blp.response(200, ProfileSchema(many=True))
    def get(self):
        """List all users (admin only)."""
        supabase = getattr(app, "supabase", None)
        resp = supabase.table("profiles").select("*").order("created_at").execute()  # type: ignore
        return resp.data or []

    @role_required("admin")
    @blp.arguments(UserCreateSchema)
    @blp.response(201, ProfileSchema)
    def post(self, json_data):
        """Create a profile row for an existing Supabase auth user (admin only)."""
        supabase = getattr(app, "supabase", None)
        data = {
            "user_id": str(json_data["user_id"]),
            "role": json_data["role"],
            "full_name": json_data.get("full_name"),
            "department": json_data.get("department"),
        }
        resp = supabase.table("profiles").insert(data).execute()  # type: ignore
        created = resp.data[0] if resp.data else None
        return created or {}, 201


# PUBLIC_INTERFACE
@blp.route("/<string:user_id>")
class UserResource(MethodView):
    """Admin-only user management resource endpoints."""

    @role_required("admin")
    @blp.arguments(UserPatchSchema)
    @blp.response(200, ProfileSchema)
    def patch(self, json_data, user_id):
        """Update a user's profile (admin only)."""
        supabase = getattr(app, "supabase", None)
        updates = {k: v for k, v in json_data.items() if k in ["role", "full_name", "department", "onboarding_complete"]}
        if not updates:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "No fields to update"}}), 400
        resp = supabase.table("profiles").update(updates).eq("user_id", user_id).execute()  # type: ignore
        return (resp.data[0] if resp.data else {}) or {}
