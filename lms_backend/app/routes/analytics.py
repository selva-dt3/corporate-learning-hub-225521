from flask import current_app as app, jsonify
from flask_smorest import Blueprint
from flask.views import MethodView
from marshmallow import Schema, fields

from ..auth.decorators import role_required

blp = Blueprint(
    "Analytics",
    "analytics",
    url_prefix="/analytics",
    description="Aggregated analytics"
)

class AnalyticsSummarySchema(Schema):
    """Schema describing the analytics summary response."""
    users = fields.Integer(required=True, description="Total number of users (profiles)")
    lessons = fields.Integer(required=True, description="Total number of lessons")
    quizzes = fields.Integer(required=True, description="Total number of quizzes")
    assignments = fields.Integer(required=True, description="Total number of assignments")
    quiz_submissions = fields.Integer(required=True, description="Total number of quiz submissions")

# PUBLIC_INTERFACE
@blp.route("/summary")
class AnalyticsSummary(MethodView):
    """Basic analytics aggregates endpoint."""

    @role_required("admin", "hr")
    @blp.response(200, AnalyticsSummarySchema, description="Aggregate counts for admin/hr dashboards")
    def get(self):
        """
        Get summary counts for dashboards (admin/hr).

        Returns a JSON object with the following keys:
        - users: number of profiles
        - lessons: number of lessons
        - quizzes: number of quizzes
        - assignments: number of assignments
        - quiz_submissions: number of quiz submissions
        """
        supabase = getattr(app, "supabase", None)
        if not supabase:
            return jsonify({
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Supabase is not configured."
                }
            }), 503

        # Counts
        profiles_count = supabase.table("profiles").select("user_id", count="exact").execute()  # type: ignore
        lessons_count = supabase.table("lessons").select("id", count="exact").execute()  # type: ignore
        quizzes_count = supabase.table("quizzes").select("id", count="exact").execute()  # type: ignore
        assignments_count = supabase.table("assignments").select("id", count="exact").execute()  # type: ignore
        submissions_count = supabase.table("quiz_submissions").select("id", count="exact").execute()  # type: ignore

        return {
            "users": profiles_count.count or 0,
            "lessons": lessons_count.count or 0,
            "quizzes": quizzes_count.count or 0,
            "assignments": assignments_count.count or 0,
            "quiz_submissions": submissions_count.count or 0,
        }
