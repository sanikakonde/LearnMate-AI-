"""
LearnMate AI – Quiz Routes
AI-powered MCQ generation, submission, scoring, and history.
"""
import json
import logging
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models import QuizSession

logger = logging.getLogger(__name__)
quiz_bp = Blueprint("quiz", __name__, url_prefix="/quiz")

DIFFICULTY_LEVELS = ["beginner", "intermediate", "advanced"]


@quiz_bp.route("/")
@login_required
def index():
    recent_sessions = current_user.quiz_sessions.order_by(
        QuizSession.created_at.desc()
    ).limit(5).all()
    return render_template("quiz/index.html", recent_sessions=recent_sessions)


@quiz_bp.route("/history")
@login_required
def history():
    page = request.args.get("page", 1, type=int)
    sessions = current_user.quiz_sessions.order_by(
        QuizSession.created_at.desc()
    ).paginate(page=page, per_page=10, error_out=False)
    return render_template("quiz/history.html", sessions=sessions)


@quiz_bp.route("/session/<int:session_id>")
@login_required
def session_detail(session_id):
    session = QuizSession.query.filter_by(
        id=session_id, user_id=current_user.id
    ).first_or_404()
    questions = []
    answers = {}
    try:
        questions = json.loads(session.questions_data or "[]")
        answers = json.loads(session.answers_data or "{}")
    except Exception:
        pass
    return render_template(
        "quiz/session_detail.html",
        session=session,
        questions=questions,
        answers=answers,
    )


@quiz_bp.route("/api/validate-topic", methods=["POST"])
@login_required
def api_validate_topic():
    """Validate and normalize the quiz topic."""
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"is_valid": False, "reason": "Topic is required."}), 400
    if len(topic) > 100:
        return jsonify({"is_valid": False, "reason": "Topic too long."}), 400

    try:
        from app.services.quiz_service import validate_and_normalize_topic
        result = validate_and_normalize_topic(topic)
        return jsonify(result)
    except Exception as exc:
        logger.error("Topic validation error: %s", exc)
        return jsonify({"is_valid": True, "normalized_topic": topic.title(), "reason": ""}), 200


@quiz_bp.route("/api/generate", methods=["POST"])
@login_required
def api_generate():
    """Generate a quiz using IBM Granite."""
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    difficulty = (data.get("difficulty") or "intermediate").strip().lower()

    if not topic:
        return jsonify({"error": "Topic is required."}), 400
    if difficulty not in DIFFICULTY_LEVELS:
        return jsonify({"error": f"Difficulty must be one of: {', '.join(DIFFICULTY_LEVELS)}."}), 400

    # Validate topic
    try:
        from app.services.quiz_service import validate_and_normalize_topic
        validation = validate_and_normalize_topic(topic)
        if not validation.get("is_valid", True):
            return jsonify({
                "error": (
                    f"'{topic}' doesn't appear to be a technology or programming topic. "
                    f"LearnMate quizzes cover programming languages, frameworks, AI/ML, cloud, "
                    f"databases, DevOps, cybersecurity, and other technical topics. "
                    f"{validation.get('reason', '')}"
                )
            }), 400
        normalized_topic = validation.get("normalized_topic", topic.title())
    except Exception as exc:
        logger.warning("Validation error, using raw topic: %s", exc)
        normalized_topic = topic.title()

    # Generate quiz
    try:
        from app.services.quiz_service import generate_quiz
        questions = generate_quiz(normalized_topic, difficulty)
        return jsonify({
            "questions": questions,
            "topic": normalized_topic,
            "difficulty": difficulty,
        })
    except RuntimeError as exc:
        logger.error("Quiz generation failed: %s", exc)
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:
        logger.error("Unexpected error generating quiz: %s", exc)
        return jsonify({"error": "Quiz generation failed. Please try again."}), 500


@quiz_bp.route("/api/submit", methods=["POST"])
@login_required
def api_submit():
    """Submit quiz answers and calculate score."""
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    difficulty = (data.get("difficulty") or "intermediate").strip()
    questions = data.get("questions", [])
    user_answers = data.get("answers", {})
    time_taken = int(data.get("time_taken_seconds", 0) or 0)

    if not questions or not topic:
        return jsonify({"error": "Invalid submission data."}), 400

    try:
        from app.services.quiz_service import calculate_score
        result = calculate_score(questions, user_answers)

        # Get AI feedback
        feedback = ""
        try:
            from app.services.ai_service import generate_quiz_feedback
            feedback = generate_quiz_feedback({
                "topic": topic,
                "difficulty": difficulty,
                "score": result["score"],
                "correct": result["correct_count"],
                "total": result["total"],
                "weak_areas": result.get("weak_areas", []),
            })
        except Exception as exc:
            logger.warning("Quiz feedback generation failed: %s", exc)
            feedback = "Review the explanations for incorrect answers to strengthen your understanding."

        # Save session
        session = QuizSession(
            user_id=current_user.id,
            topic=topic,
            difficulty=difficulty,
            score=result["score"],
            correct_count=result["correct_count"],
            total_questions=result["total"],
            time_taken_seconds=time_taken,
            questions_data=json.dumps(questions),
            answers_data=json.dumps(user_answers),
            feedback=feedback,
        )
        db.session.add(session)
        db.session.commit()

        return jsonify({
            "score": result["score"],
            "correct_count": result["correct_count"],
            "total": result["total"],
            "results": result["results"],
            "weak_areas": result.get("weak_areas", []),
            "feedback": feedback,
            "session_id": session.id,
            "grade": session.grade_label(),
        })

    except Exception as exc:
        db.session.rollback()
        logger.error("Quiz submission error: %s", exc)
        return jsonify({"error": "Submission failed. Please try again."}), 500
