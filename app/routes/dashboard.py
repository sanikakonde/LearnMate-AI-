"""
LearnMate AI – Dashboard Routes
"""
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import (
    LearningRoadmap, RoadmapMilestone, QuizSession,
    StudySession, ProgressLog, ChatSession
)

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint("dashboard", __name__)

# In-process next-step cache: {user_id: (timestamp, result)}
_NEXT_STEP_CACHE: dict = {}
_NEXT_STEP_TTL = 300  # seconds – regenerate at most once every 5 minutes


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    uid = current_user.id

    # --- Stats (single DB queries per entity) ---
    active_roadmap = LearningRoadmap.query.filter_by(
        user_id=uid, is_active=True
    ).order_by(LearningRoadmap.created_at.desc()).first()

    # Fetch quiz sessions once, derive all quiz stats from that list
    quiz_sessions = current_user.quiz_sessions.order_by(QuizSession.created_at.desc()).limit(10).all()
    recent_quiz_sessions = quiz_sessions[:5]
    total_quizzes = len(quiz_sessions)
    avg_score = (sum(q.score for q in quiz_sessions) // total_quizzes) if total_quizzes else 0

    # Study stats – one aggregate DB query for total; separate limit query for recent list
    all_study = current_user.study_sessions.order_by(StudySession.created_at.desc()).limit(7).all()
    total_study_result = db.session.query(
        db.func.coalesce(db.func.sum(StudySession.duration_minutes), 0)
    ).filter(StudySession.user_id == uid).scalar()
    total_study_mins = int(total_study_result or 0)

    completed_topics = ProgressLog.query.filter_by(
        user_id=uid, status="completed"
    ).count()

    progress_logs = current_user.progress_logs.order_by(
        ProgressLog.updated_at.desc()
    ).limit(5).all()

    # Roadmap progress
    roadmap_progress = 0
    total_milestones = 0
    completed_milestones = 0
    current_phase_name = "Getting Started"
    if active_roadmap:
        milestones = RoadmapMilestone.query.filter_by(roadmap_id=active_roadmap.id).all()
        total_milestones = len(milestones)
        completed_milestones = sum(1 for m in milestones if m.status == "completed")
        if total_milestones > 0:
            roadmap_progress = round((completed_milestones / total_milestones) * 100)
        in_progress = next((m for m in milestones if m.status == "in_progress"), None)
        if in_progress:
            current_phase_name = f"Phase {in_progress.phase}"

    # Study chart – one aggregated query instead of 7 separate queries
    study_chart = _get_study_chart_data(uid, 7)

    # Quiz chart from already-fetched list
    quiz_chart = _get_quiz_chart_data_from_list(quiz_sessions)

    # Next step recommendation with in-process cache (avoids AI call on every load)
    next_step = _get_cached_next_step(uid)

    return render_template(
        "dashboard/index.html",
        active_roadmap=active_roadmap,
        quiz_sessions=recent_quiz_sessions,
        total_quizzes=total_quizzes,
        avg_score=avg_score,
        study_sessions=all_study,
        total_study_mins=total_study_mins,
        completed_topics=completed_topics,
        progress_logs=progress_logs,
        roadmap_progress=roadmap_progress,
        total_milestones=total_milestones,
        completed_milestones=completed_milestones,
        current_phase_name=current_phase_name,
        study_chart=json.dumps(study_chart),
        quiz_chart=json.dumps(quiz_chart),
        next_step=next_step,
    )


def _get_study_chart_data(user_id: int, days: int = 7) -> dict:
    """
    Get study minutes per day for the last N days using a single
    aggregated DB query instead of one query per day.
    """
    today = datetime.utcnow().date()
    start = today - timedelta(days=days - 1)

    # Single query: fetch all sessions in the window
    sessions = StudySession.query.filter(
        StudySession.user_id == user_id,
        StudySession.created_at >= datetime.combine(start, datetime.min.time()),
    ).with_entities(StudySession.created_at, StudySession.duration_minutes).all()

    # Aggregate by date
    by_day: dict = {}
    for created_at, mins in sessions:
        day_key = created_at.date()
        by_day[day_key] = by_day.get(day_key, 0) + mins

    labels = []
    data = []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        labels.append(day.strftime("%b %d"))
        data.append(by_day.get(day, 0))

    return {"labels": labels, "data": data}


def _get_quiz_chart_data_from_list(sessions: list) -> dict:
    """Build quiz chart data from an already-fetched list (no extra DB query)."""
    last10 = list(reversed(sessions[:10]))
    labels = [f"{s.topic[:10]}..." if len(s.topic) > 10 else s.topic for s in last10]
    data = [s.score for s in last10]
    return {"labels": labels, "data": data}


def _get_cached_next_step(user_id: int) -> dict:
    """
    Return AI next-step recommendation, caching the result in memory for
    _NEXT_STEP_TTL seconds so the AI call is not made on every page load.
    """
    now = datetime.utcnow().timestamp()
    cached = _NEXT_STEP_CACHE.get(user_id)
    if cached and (now - cached[0]) < _NEXT_STEP_TTL:
        return cached[1]

    try:
        from app.services.ai_service import get_next_step_recommendation
        completed_topics = [
            log.topic for log in ProgressLog.query.filter_by(
                user_id=user_id, status="completed"
            ).with_entities(ProgressLog.topic).all()
        ]
        quiz_sessions = QuizSession.query.filter_by(user_id=user_id).order_by(
            QuizSession.created_at.desc()
        ).limit(3).all()
        quiz_perf = (
            f"Recent scores: {', '.join(str(q.score)+'%' for q in quiz_sessions)}"
            if quiz_sessions else "No quizzes yet"
        )

        result = get_next_step_recommendation({
            "career_goal": current_user.career_goal or "Software Engineer",
            "skill_level": current_user.current_skill_level or "beginner",
            "completed_topics": completed_topics,
            "quiz_performance": quiz_perf,
            "current_phase": "Foundation",
            "study_hours": current_user.available_study_hours or 2,
        })
        _NEXT_STEP_CACHE[user_id] = (now, result)
        return result
    except Exception as exc:
        logger.warning("Next step recommendation failed: %s", exc)
        fallback = {
            "next_topic": "Start your learning journey",
            "why": "Begin by exploring your personalized roadmap",
            "action": "Visit your roadmap and start the first topic",
            "resources": [],
            "estimated_time": "At your own pace",
            "encouragement": "Every expert was once a beginner. Let's go!",
        }
        # Cache the fallback too so a broken AI service doesn't hammer watsonx
        _NEXT_STEP_CACHE[user_id] = (now, fallback)
        return fallback


@dashboard_bp.route("/api/dashboard/stats")
@login_required
def api_stats():
    """API endpoint for dashboard stats refresh."""
    return jsonify({
        "total_study_mins": current_user.total_study_minutes(),
        "total_quizzes": current_user.quiz_sessions.count(),
        "completed_topics": current_user.completed_topics_count(),
        "avg_score": current_user.total_quiz_score(),
    })
