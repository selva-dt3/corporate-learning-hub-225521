from flask import g, jsonify, current_app as app
from flask_smorest import Blueprint
from flask.views import MethodView
from marshmallow import Schema, fields

from ..auth.decorators import role_required

blp = Blueprint(
    "Quizzes",
    "quizzes",
    url_prefix="/quizzes",
    description="Quiz management and submissions"
)

class QuizSchema(Schema):
    id = fields.UUID()
    title = fields.String(required=True)
    spec = fields.Dict(required=True)
    created_at = fields.DateTime(allow_none=True)

class QuizCreateSchema(Schema):
    title = fields.String(required=True)
    spec = fields.Dict(required=True)

class QuizUpdateSchema(Schema):
    title = fields.String()
    spec = fields.Dict()


# PUBLIC_INTERFACE
@blp.route("")
class QuizzesCollection(MethodView):
    """List and create quizzes."""

    @blp.response(200, QuizSchema(many=True))
    def get(self):
        """List quizzes visible to the user (RLS limits for employees)."""
        supabase = getattr(app, "supabase", None)
        if not supabase:
            return jsonify({"error": {"code": "SERVICE_UNAVAILABLE", "message": "Supabase is not configured."}}), 503
        resp = supabase.table("quizzes").select("*").order("created_at", desc=True).execute()  # type: ignore
        return resp.data or []

    @role_required("admin", "hr")
    @blp.arguments(QuizCreateSchema)
    @blp.response(201, QuizSchema)
    def post(self, json_data):
        """Create quiz (admin/hr)."""
        supabase = getattr(app, "supabase", None)
        if not supabase:
            return jsonify({"error": {"code": "SERVICE_UNAVAILABLE", "message": "Supabase is not configured."}}), 503
        resp = supabase.table("quizzes").insert(json_data).execute()  # type: ignore
        return (resp.data[0] if resp.data else {}) or {}, 201


# PUBLIC_INTERFACE
@blp.route("/<string:quiz_id>")
class QuizResource(MethodView):
    """Retrieve, update, delete a quiz."""

    @blp.response(200, QuizSchema)
    def get(self, quiz_id):
        """Get quiz by id."""
        supabase = getattr(app, "supabase", None)
        if not supabase:
            return jsonify({"error": {"code": "SERVICE_UNAVAILABLE", "message": "Supabase is not configured."}}), 503
        resp = supabase.table("quizzes").select("*").eq("id", quiz_id).limit(1).execute()  # type: ignore
        if not resp.data:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Quiz not found"}}), 404
        return resp.data[0]

    @role_required("admin", "hr")
    @blp.arguments(QuizUpdateSchema)
    @blp.response(200, QuizSchema)
    def patch(self, json_data, quiz_id):
        """Update quiz (admin/hr)."""
        supabase = getattr(app, "supabase", None)
        if not supabase:
            return jsonify({"error": {"code": "SERVICE_UNAVAILABLE", "message": "Supabase is not configured."}}), 503
        resp = supabase.table("quizzes").update(json_data).eq("id", quiz_id).execute()  # type: ignore
        return (resp.data[0] if resp.data else {}) or {}

    @role_required("admin", "hr")
    def delete(self, quiz_id):
        """Delete quiz (admin/hr)."""
        supabase = getattr(app, "supabase", None)
        if not supabase:
            return jsonify({"error": {"code": "SERVICE_UNAVAILABLE", "message": "Supabase is not configured."}}), 503
        supabase.table("quizzes").delete().eq("id", quiz_id).execute()  # type: ignore
        return {"deleted": True}


class SubmissionSchema(Schema):
    answers = fields.Dict(required=True, description="Map of question id to answer value")

class SubmissionResultSchema(Schema):
    submission_id = fields.UUID()
    score = fields.Float()
    max_score = fields.Float()
    submitted_at = fields.DateTime()


# PUBLIC_INTERFACE
@blp.route("/<string:quiz_id>/submit")
class QuizSubmit(MethodView):
    """Submit answers to a quiz."""

    @blp.arguments(SubmissionSchema)
    @blp.response(200, SubmissionResultSchema)
    def post(self, json_data, quiz_id):
        """Submit quiz answers. Employees submit their own; admins/hr may submit for testing."""
        supabase = getattr(app, "supabase", None)
        if not supabase:
            return jsonify({"error": {"code": "SERVICE_UNAVAILABLE", "message": "Supabase is not configured."}}), 503
        # fetch quiz spec
        quiz_resp = supabase.table("quizzes").select("*").eq("id", quiz_id).limit(1).execute()  # type: ignore
        if not quiz_resp.data:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Quiz not found"}}), 404
        quiz = quiz_resp.data[0]
        spec = quiz.get("spec") or {}

        # simple scoring: spec.questions[*].answer and optional spec.scoring per question
        answers = json_data["answers"]
        questions = spec.get("questions", [])
        scoring_map = spec.get("scoring", {})

        score = 0.0
        max_score = 0.0
        for q in questions:
            qid = q.get("id")
            correct = q.get("answer")
            weight = float(scoring_map.get(qid, 1))
            max_score += weight
            if qid in answers:
                if answers[qid] == correct:
                    score += weight

        # store submission
        payload = {
            "quiz_id": quiz_id,
            "user_id": str(getattr(g, "user_id", None)),
            "answers": answers,
            "score": score,
        }
        sub_resp = supabase.table("quiz_submissions").insert(payload).execute()  # type: ignore
        sub = sub_resp.data[0] if sub_resp.data else {}
        return {
            "submission_id": sub.get("id"),
            "score": score,
            "max_score": max_score,
            "submitted_at": sub.get("submitted_at"),
        }
