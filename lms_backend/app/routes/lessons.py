from flask import g, jsonify, current_app as app
from flask_smorest import Blueprint
from flask.views import MethodView
from marshmallow import Schema, fields

from .. import role_required

blp = Blueprint(
    "Lessons",
    "lessons",
    url_prefix="/lessons",
    description="Lesson management"
)

class LessonSchema(Schema):
    id = fields.UUID()
    title = fields.String(required=True)
    content_url = fields.String(allow_none=True)
    owner = fields.UUID(allow_none=True)
    created_at = fields.DateTime(allow_none=True)

class LessonCreateSchema(Schema):
    title = fields.String(required=True)
    content_url = fields.String(allow_none=True)

class LessonUpdateSchema(Schema):
    title = fields.String()
    content_url = fields.String(allow_none=True)


# PUBLIC_INTERFACE
@blp.route("")
class LessonsCollection(MethodView):
    """List and create lessons."""

    @blp.response(200, LessonSchema(many=True))
    def get(self):
        """List lessons visible to the user (admin/hr all; employees only assigned ones per RLS)."""
        supabase = getattr(app, "supabase", None)
        resp = supabase.table("lessons").select("*").order("created_at", desc=True).execute()  # type: ignore
        return resp.data or []

    @role_required("admin", "hr")
    @blp.arguments(LessonCreateSchema)
    @blp.response(201, LessonSchema)
    def post(self, json_data):
        """Create lesson (admin/hr)."""
        supabase = getattr(app, "supabase", None)
        data = {
            "title": json_data["title"],
            "content_url": json_data.get("content_url"),
            "owner": str(getattr(g, "user_id", None)),
        }
        resp = supabase.table("lessons").insert(data).execute()  # type: ignore
        return (resp.data[0] if resp.data else {}) or {}, 201


# PUBLIC_INTERFACE
@blp.route("/<string:lesson_id>")
class LessonResource(MethodView):
    """Retrieve, update, or delete a lesson."""

    @blp.response(200, LessonSchema)
    def get(self, lesson_id):
        """Get lesson by id (RLS controls visibility)."""
        supabase = getattr(app, "supabase", None)
        resp = supabase.table("lessons").select("*").eq("id", lesson_id).limit(1).execute()  # type: ignore
        if not resp.data:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Lesson not found"}}), 404
        return resp.data[0]

    @role_required("admin", "hr")
    @blp.arguments(LessonUpdateSchema)
    @blp.response(200, LessonSchema)
    def patch(self, json_data, lesson_id):
        """Update lesson (admin/hr)."""
        supabase = getattr(app, "supabase", None)
        resp = supabase.table("lessons").update(json_data).eq("id", lesson_id).execute()  # type: ignore
        return (resp.data[0] if resp.data else {}) or {}

    @role_required("admin", "hr")
    def delete(self, lesson_id):
        """Delete lesson (admin/hr)."""
        supabase = getattr(app, "supabase", None)
        supabase.table("lessons").delete().eq("id", lesson_id).execute()  # type: ignore
        return {"deleted": True}
