from flask import g, jsonify, current_app as app
from flask_smorest import Blueprint
from flask.views import MethodView
from marshmallow import Schema, fields, validate

from ..auth.decorators import role_required

blp = Blueprint(
    "Assignments",
    "assignments",
    url_prefix="/assignments",
    description="Assignments workflows"
)

class AssignmentSchema(Schema):
    id = fields.UUID()
    assignee_user = fields.UUID(required=True)
    lesson_id = fields.UUID(allow_none=True)
    quiz_id = fields.UUID(allow_none=True)
    due_at = fields.DateTime(allow_none=True)
    status = fields.String(validate=validate.OneOf(["assigned", "in_progress", "completed"]))
    created_at = fields.DateTime(allow_none=True)

class AssignmentCreateSchema(Schema):
    assignee_user = fields.UUID(required=True)
    lesson_id = fields.UUID(allow_none=True)
    quiz_id = fields.UUID(allow_none=True)
    due_at = fields.DateTime(allow_none=True)

class AssignmentUpdateSchema(Schema):
    due_at = fields.DateTime(allow_none=True)
    status = fields.String(validate=validate.OneOf(["assigned", "in_progress", "completed"]))


# PUBLIC_INTERFACE
@blp.route("")
class AssignmentsCollection(MethodView):
    """List and create assignments."""

    @blp.response(200, AssignmentSchema(many=True))
    def get(self):
        """List assignments visible to the user (admin/hr all, employee own via RLS)."""
        supabase = getattr(app, "supabase", None)
        if not supabase:
            return jsonify({"error": {"code": "SERVICE_UNAVAILABLE", "message": "Supabase is not configured."}}), 503
        resp = supabase.table("assignments").select("*").order("created_at", desc=True).execute()  # type: ignore
        return resp.data or []

    @role_required("admin", "hr")
    @blp.arguments(AssignmentCreateSchema)
    @blp.response(201, AssignmentSchema)
    def post(self, json_data):
        """Create assignment (admin/hr)."""
        supabase = getattr(app, "supabase", None)
        if not supabase:
            return jsonify({"error": {"code": "SERVICE_UNAVAILABLE", "message": "Supabase is not configured."}}), 503
        resp = supabase.table("assignments").insert(json_data).execute()  # type: ignore
        return (resp.data[0] if resp.data else {}) or {}, 201


# PUBLIC_INTERFACE
@blp.route("/<string:assignment_id>")
class AssignmentResource(MethodView):
    """Get, update, or delete an assignment."""

    @blp.response(200, AssignmentSchema)
    def get(self, assignment_id):
        """Get assignment by id (RLS enforced)."""
        supabase = getattr(app, "supabase", None)
        if not supabase:
            return jsonify({"error": {"code": "SERVICE_UNAVAILABLE", "message": "Supabase is not configured."}}), 503
        resp = supabase.table("assignments").select("*").eq("id", assignment_id).limit(1).execute()  # type: ignore
        if not resp.data:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Assignment not found"}}), 404
        return resp.data[0]

    @role_required("admin", "hr")
    @blp.arguments(AssignmentUpdateSchema)
    @blp.response(200, AssignmentSchema)
    def patch(self, json_data, assignment_id):
        """Update assignment (admin/hr)."""
        supabase = getattr(app, "supabase", None)
        if not supabase:
            return jsonify({"error": {"code": "SERVICE_UNAVAILABLE", "message": "Supabase is not configured."}}), 503
        resp = supabase.table("assignments").update(json_data).eq("id", assignment_id).execute()  # type: ignore
        return (resp.data[0] if resp.data else {}) or {}

    @role_required("admin", "hr")
    def delete(self, assignment_id):
        """Delete assignment (admin/hr)."""
        supabase = getattr(app, "supabase", None)
        if not supabase:
            return jsonify({"error": {"code": "SERVICE_UNAVAILABLE", "message": "Supabase is not configured."}}), 503
        supabase.table("assignments").delete().eq("id", assignment_id).execute()  # type: ignore
        return {"deleted": True}


# PUBLIC_INTERFACE
@blp.route("/by-user/<string:user_id>")
class AssignmentsByUser(MethodView):
    """List assignments by user id (admin/hr can view anyone; employees only self)."""

    @blp.response(200, AssignmentSchema(many=True))
    def get(self, user_id):
        """List assignments for a specific user."""
        role = getattr(g, "role", None)
        auth_user = str(getattr(g, "user_id", ""))
        if role not in ["admin", "hr"] and auth_user != user_id:
            return jsonify({"error": {"code": "AUTHZ_ERROR", "message": "Forbidden"}}), 403

        supabase = getattr(app, "supabase", None)
        if not supabase:
            return jsonify({"error": {"code": "SERVICE_UNAVAILABLE", "message": "Supabase is not configured."}}), 503
        resp = supabase.table("assignments").select("*").eq("assignee_user", user_id).order("created_at", desc=True).execute()  # type: ignore
        return resp.data or []
