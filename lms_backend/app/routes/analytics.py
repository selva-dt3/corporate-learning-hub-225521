from flask import current_app as app
from flask_smorest import Blueprint
from flask.views import MethodView

from .. import role_required

blp = Blueprint(
    "Analytics",
    "analytics",
    url_prefix="/analytics",
    description="Aggregated analytics"
)

# PUBLIC_INTERFACE
@blp.route("/summary")
class AnalyticsSummary(MethodView):
    """Basic analytics aggregates."""

    @role_required("admin", "hr")
    def get(self):
        """Get summary counts for dashboards (admin/hr)."""
        supabase = getattr(app, "supabase", None)
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
